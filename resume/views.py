# resume/views.py
from __future__ import annotations

import json, logging, os, re
from typing import Optional, Tuple

from bs4 import BeautifulSoup           # pip install beautifulsoup4
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views import View
from django.views.decorators.http import require_http_methods
from openai import OpenAI               # openai-python ≥ 1.3
from weasyprint import HTML

from .forms import ResumeUploadForm
from .models import Resume
from .templates_config import TEMPLATES_LIST
from .utils import clean_extracted_text, extract_text_from_file, validate_file

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ────────────────────────────  SPA  ────────────────────────────
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "resume/spa.html")


# ──────────────────────  RESUME UPLOAD  ───────────────────────
@require_http_methods(["POST"])
def upload_resume_ajax(request: HttpRequest) -> JsonResponse:
    try:
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file provided"}, status=400)

        file_obj = request.FILES["file"]
        errs = validate_file(file_obj)
        if errs:
            return JsonResponse({"error": "; ".join(errs)}, status=400)

        form = ResumeUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({"error": "Invalid file"}, status=400)

        resume = form.save(commit=False)
        if request.user.is_authenticated:
            resume.user = request.user
        resume.save()

        text = extract_text_from_file(resume.file.path)
        resume.extracted_text = clean_extracted_text(text)
        resume.save()

        return JsonResponse(
            {
                "success": True,
                "resume_id": resume.id,
                "file_size": resume.file_size,
                "text_length": len(resume.extracted_text),
            }
        )
    except Exception as exc:
        logger.exception("Upload failed: %s", exc)
        return JsonResponse({"error": f"Upload failed: {exc}"}, status=500)


# ────────────  GENERATE TAILORED RESUME (AJAX)  ───────────────
@require_http_methods(["POST"])
def generate_tailored_resume_ajax(request: HttpRequest,
                                  resume_id: int,
                                  template_id: int) -> JsonResponse:
    try:
        resume   = get_object_or_404(Resume, id=resume_id)
        payload  = json.loads(request.body or "{}")
        job_desc = payload.get("job_description", "")
        num_pg   = payload.get("num_pages")

        if len(job_desc.strip()) < 50:
            return JsonResponse({"error": "Job description must be at least 50 characters"}, status=400)

        tpl_meta = next((t for t in TEMPLATES_LIST if t["id"] == template_id), None)
        if not tpl_meta:
            return JsonResponse({"error": "Template not found"}, status=400)
        tpl_path = os.path.join(settings.BASE_DIR, "resume", "templates", "resume",
                                "templates_repo", tpl_meta["filename"])
        if not os.path.exists(tpl_path):
            return JsonResponse({"error": "Template file missing"}, status=400)

        template_html = open(tpl_path, encoding="utf-8").read()

        html_resume, ats, job = tailor_resume_with_llm(
            resume.extracted_text, job_desc, template_html, num_pg
        )

        request.session.update({
            "tailored_resume": html_resume,
            "ats_score":       ats,
            "job_score":       job,
            "resume_id":       resume_id,
            "template_id":     template_id,
        })
        return JsonResponse({"success": True,
                             "final_resume": html_resume,
                             "ats_score":    ats,
                             "job_score":    job})
    except Exception as exc:
        logger.exception("Generation failed: %s", exc)
        return JsonResponse({"error": f"Generation failed: {exc}"}, status=500)


# ─────────────────────────  PDF DOWNLOAD  ─────────────────────
def download_pdf_ajax(request: HttpRequest, resume_id: int):
    try:
        html_resume = request.session.get("tailored_resume")
        if not html_resume:
            return JsonResponse({"error": "Generate resume first"}, status=400)

        # Generate PDF with proper WeasyPrint syntax
        pdf_html = render_to_string("resume/pdf_template.html", 
                                   {"final_resume": html_resume})
        pdf_file = HTML(string=pdf_html).write_pdf()

        # Create response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="optimized_resume.pdf"'
        return response

    except Exception as exc:
        logger.exception("PDF generation failed")
        return JsonResponse({"error": f"PDF error: {exc}"}, status=500)


# ─────────────────────────  TEMPLATE LIST  ────────────────────
def get_templates_ajax(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"templates": TEMPLATES_LIST})


# ─────────────────────────  REST ENDPOINTS  ───────────────────
class ResumeAPIView(View):
    def get(self, request, resume_id=None):
        try:
            if resume_id:
                r = get_object_or_404(Resume, id=resume_id)
                return JsonResponse({
                    "id":          r.id,
                    "filename":    r.file.name,
                    "created_at":  r.created_at.isoformat(),
                    "file_size":   r.file_size,
                    "extracted_text": (r.extracted_text[:500] + "…")
                                      if r.extracted_text and len(r.extracted_text) > 500
                                      else r.extracted_text})
            qs = Resume.objects.filter(user=request.user) if request.user.is_authenticated else Resume.objects.all()[:10]
            return JsonResponse({"resumes":[{"id":r.id,"filename":r.file.name,
                                             "created_at":r.created_at.isoformat(),
                                             "file_size":r.file_size} for r in qs]})
        except Exception as exc:
            logger.exception("API GET error: %s", exc)
            return JsonResponse({"error": str(exc)}, status=500)

@require_http_methods(["POST"])
def analyze_resume_ajax(request: HttpRequest):
    """Initial analysis before generation"""
    try:
        data = json.loads(request.body)
        resume_text = data.get('resume', '')
        job_desc = data.get('job_description', '')
        
        from .utils import extract_keywords
        keywords = extract_keywords(job_desc)
        
        return JsonResponse({
            "missing_keywords": keywords,
            "action_items": [
                "Add technical skills section",
                "Include measurable achievements",
                "Match job title terminology"
            ]
        })
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return JsonResponse({"error": "Initial analysis failed"}, status=500)

# ─────────────────  LLM ROUTINE (WITH LOOP)  ──────────────────
WORDS_PER_PAGE   = 500
MAX_ITER         = settings.LLM_CONFIG.get("MAX_ITERATIONS", 6)
MIN_SCORE        = max(92, settings.LLM_CONFIG.get("MIN_ATS_SCORE", 92))

# ─────────────────  LLM ROUTINE (ITERATIVE IMPROVEMENT)  ──────────────────
def tailor_resume_with_llm(resume_text: str,
                           job_desc: str,
                           template_html: str,
                           num_pages: Optional[int]=None) -> Tuple[str,int,int]:
    """Iterate until BOTH scores ≥ 92% using keyword-focused improvements"""
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI key missing - using fallback")
        return _create_fallback_resume(resume_text, template_html), 70, 0

    MAX_ITER = 8  # Prevent infinite loops
    MIN_SCORE = 92
    collected_keywords = []

    base_prompt = {
        "role": "system",
        "content": """You are an ATS optimization expert. Return JSON with:
        - html_resume: Resume HTML with keywords integrated
        - ats_score: 0-100 ATS compatibility score
        - job_score: 0-100 job match score
        - missing_keywords: List of missing JD keywords"""
    }

    messages = [
        base_prompt,
        {"role": "user", "content": f"""
        JOB DESCRIPTION:
        {job_desc}
        
        RESUME CONTENT:
        {resume_text}
        
        TEMPLATE:
        {template_html}
        
        TARGET PAGES: {num_pages or 1}
        """}
    ]

    best_resume = ""
    best_ats = 0
    best_job = 0

    for iteration in range(MAX_ITER):
        try:
            # Get LLM response
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            
            # Extract scores and keywords
            ats = int(data.get('ats_score', 0))
            job = int(data.get('job_score', 0))
            new_keywords = [kw.lower() for kw in data.get('missing_keywords', []) 
                           if kw.lower() not in collected_keywords]
            
            collected_keywords.extend(new_keywords)
            
            # Track best version
            if ats > best_ats and job > best_job:
                best_resume = data.get('html_resume', '')
                best_ats = ats
                best_job = job

            # Exit if targets met
            if ats >= MIN_SCORE and job >= MIN_SCORE:
                return best_resume, ats, job

            # Prepare next iteration
            improvement_instructions = f"""
            Improve by integrating these keywords: {', '.join(collected_keywords)}.
            Make these changes:
            1. Add missing keywords to Skills/Summary
            2. Align bullet points with job requirements
            3. Maintain {num_pages or 1} page limit
            4. Ensure ATS-friendly formatting
            5. Preserve original valid content"""

            messages.extend([
                {"role": "assistant", "content": json.dumps(data)},
                {"role": "user", "content": improvement_instructions}
            ])

        except Exception as e:
            logger.error(f"Iteration {iteration} failed: {str(e)}")
            continue

    return best_resume or _create_fallback_resume(resume_text, template_html), best_ats, best_job

# ───────────────────  FALLBACK RESUME  ────────────────────────
def _create_fallback_resume(resume_text: str, template_html: str) -> str:
    first_line = next((ln.strip() for ln in resume_text.splitlines() if ln.strip()), "Candidate")
    email = re.search(r"\b\S+@\S+\.\S+\b", resume_text)
    phone = re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", resume_text)
    repl = {
        "{{NAME}}": first_line,
        "{{EMAIL}}": email.group() if email else "email@example.com",
        "{{PHONE}}": phone.group() if phone else "(555) 123-4567",
        "{{SUMMARY}}":"Motivated professional seeking new challenges.",
        "{{PROJECTS}}":"<ul><li>Project A</li><li>Project B</li></ul>",
    }
    for k,v in repl.items():
        template_html = template_html.replace(k,v)
    return re.sub(r"\{\{[^}]+\}\}","",template_html)
def extract_keywords(text: str) -> list:
    """Extract technical keywords from text"""
    if not text:
        return []
    
    # NLP-based keyword extraction
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import nltk
        nltk.download('stopwords')
        from nltk.corpus import stopwords

        stop_words = set(stopwords.words('english'))
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words=stop_words)
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        
        return feature_names[:25]  # Top 25 keywords
        
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        return []