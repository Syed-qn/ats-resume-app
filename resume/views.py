# resume/views.py - Updated with Task 10: Email notifications on first resume upload

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import timedelta
from typing import Optional, Tuple
from django.core.cache import cache
import threading
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from .models import Resume, DownloadLog, Profile, ManualResume
from .forms import CustomSignupForm
import json
import os
from django.urls import reverse_lazy
from bs4 import BeautifulSoup           # pip install beautifulsoup4
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.views import View
from django.views.decorators.http import require_http_methods
from django.db import transaction
from openai import OpenAI               # openai-python ≥ 1.3
from weasyprint import HTML

# Task 10: Import email functionality
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.contrib.auth.views import LoginView

from .forms import ResumeUploadForm, CustomSignupForm, ManualResumeForm
from .models import Resume, DownloadLog
from .templates_config import TEMPLATES_LIST
from .utils import clean_extracted_text, extract_text_from_file, validate_file

# Task 10: Enhanced email functionality
from django.core.mail import EmailMessage, send_mail
from django.template.loader import get_template
from django.contrib.auth.views import LoginView

# Task 11: Password reset functionality
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView, 
    PasswordResetConfirmView, PasswordResetCompleteView
)


logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Target scores - must achieve both
TARGET_ATS_SCORE = 92
TARGET_JOB_SCORE = 92

# ────────────────────  Landing & Signup  ────────────────────

def landing(request: HttpRequest) -> HttpResponse:
    """Public landing page explaining ATS importance."""
    return render(request, "landing.html")


def ats_details(request: HttpRequest) -> HttpResponse:
    """Detailed page explaining ATS systems - Task 13"""
    return render(request, "ats_details.html")


def our_services(request: HttpRequest) -> HttpResponse:
    """Detailed page explaining our services - Task 13"""
    return render(request, "our_services.html")


def signup(request: HttpRequest) -> HttpResponse:
    """
    Custom user signup with success message and redirect to login.
    Task 3: Show success prompt and redirect to login page.
    Task 10: Enhanced to store signup data for email notifications.
    """
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Task 10: Store signup form data in session for first resume email
            signup_data = {
                'username': form.cleaned_data.get('username'),
                'email': form.cleaned_data.get('email'),
                'phone_number': form.cleaned_data.get('phone_number'),
                'country_code': form.cleaned_data.get('country_code'),
                'city': form.cleaned_data.get('city'),
                'country': form.cleaned_data.get('country'),
                'signup_time': timezone.now().isoformat(),
            }
            
            # Store in cache with user ID as key for later retrieval
            cache.set(f"signup_data_{user.id}", signup_data, timeout=86400)  # 24 hours
            
            # Task 3: Add success message and redirect to login
            messages.success(
                request, 
                f'🎉 Success! Your account has been created successfully. '
                f'Welcome to ATS Resume Optimizer, {user.username}! '
                f'Please log in to access your dashboard.'
            )
            return redirect("login")
        else:
            # Add error message for form validation failures
            messages.error(
                request,
                'Please correct the errors below and try again.'
            )
    else:
        form = CustomSignupForm()
    return render(request, "registration/signup.html", {"form": form})


# ────────────────────────  SPA Dashboard  ───────────────────────

@login_required(login_url="login")
def dashboard(request: HttpRequest) -> HttpResponse:
    """Single-page application entry point; requires login - Task 14."""
    
    # Check if user is admin and redirect to admin panel
    if request.user.is_superuser or request.user.is_staff:
        messages.info(request, f'Welcome Admin {request.user.username}! Redirecting to Admin Panel...')
        return redirect('admin_dashboard')
    
    return render(request, "resume/spa.html")


# Task 10: Enhanced email notification function for first resume upload
def send_first_resume_notification(user, resume_file, signup_data=None):
    """Send comprehensive email notification when user uploads their first resume"""
    try:
        # Get user profile information
        profile = getattr(user, 'profile', None)
        
        # Get signup data from cache if not provided
        if not signup_data:
            signup_data = cache.get(f"signup_data_{user.id}", {})
        
        # Prepare comprehensive context for email template
        context = {
            'user': user,
            'profile': profile,
            'resume_filename': resume_file.name if resume_file else 'No file',
            'resume_file_size': resume_file.size if resume_file else 0,
            'upload_time': timezone.now(),
            'admin_email': getattr(settings, 'ADMIN_EMAIL', 'admin@example.com'),
            
            # Signup form details
            'signup_data': {
                'username': signup_data.get('username', user.username),
                'email': signup_data.get('email', user.email),
                'phone_number': signup_data.get('phone_number', 'Not provided'),
                'country_code': signup_data.get('country_code', 'Not provided'),
                'city': signup_data.get('city', 'Not provided'),
                'country': signup_data.get('country', 'Not provided'),
                'signup_time': signup_data.get('signup_time', 'Unknown'),
                'full_phone': f"{signup_data.get('country_code', '')}{signup_data.get('phone_number', '')}" if signup_data.get('phone_number') else 'Not provided'
            },
            
            # Additional user info
            'user_info': {
                'date_joined': user.date_joined,
                'last_login': user.last_login,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
            }
        }
        
        # Load email template
        email_template = get_template('emails/first_resume_notification.html')
        email_content = email_template.render(context)
        
        # Create email message
        admin_email = getattr(settings, 'ADMIN_CONFIG', {}).get('EMAIL', 'admin@example.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@atsresume.com')
        
        email = EmailMessage(
            subject=f'🎯 New User First Resume Upload - {user.username}',
            body=email_content,
            from_email=from_email,
            to=[admin_email],
            reply_to=[user.email],
        )
        
        # Set email as HTML
        email.content_subtype = 'html'
        
        # Attach the resume file if it exists
        if resume_file and hasattr(resume_file, 'path') and os.path.exists(resume_file.path):
            try:
                email.attach_file(resume_file.path)
                logger.info(f"Resume file attached: {resume_file.path}")
            except Exception as e:
                logger.warning(f"Failed to attach resume file: {e}")
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"First resume notification sent for user: {user.username}")
        
        # Clear signup data from cache after successful email
        cache.delete(f"signup_data_{user.id}")
        
    except Exception as e:
        logger.error(f"Failed to send first resume notification for user {user.username}: {e}")



# ────────────────────────  Resume Upload  ───────────────────────

@require_http_methods(["POST"])
@login_required(login_url="login")
def upload_resume_ajax(request: HttpRequest) -> JsonResponse:
    """Upload resume with login protection - Task 14"""
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

        # Task 10: Check if this is the user's first resume
        is_first_resume = not Resume.objects.filter(user=request.user).exists()

        resume = form.save(commit=False)
        resume.user = request.user
        resume.file_size_bytes = file_obj.size
        resume.save()

        text = extract_text_from_file(resume.file.path)
        resume.extracted_text = clean_extracted_text(text)
        resume.save()

        # Task 10: Send email notification for first resume upload
        if is_first_resume:
            try:
                # Get signup data from cache
                signup_data = cache.get(f"signup_data_{request.user.id}", {})
                
                # Send notification in background thread to avoid blocking the response
                threading.Thread(
                    target=send_first_resume_notification,
                    args=(request.user, resume.file, signup_data),
                    daemon=True
                ).start()
                logger.info(f"First resume upload notification queued for user: {request.user.username}")
            except Exception as e:
                logger.error(f"Failed to queue first resume notification: {e}")

        return JsonResponse({
            "success": True,
            "resume_id": resume.id,
            "file_size": resume.file_size,
            "text_length": len(resume.extracted_text),
            "is_first_resume": is_first_resume,
        })
    except Exception as exc:
        logger.exception("Upload failed: %s", exc)
        return JsonResponse({"error": f"Upload failed: {exc}"}, status=500)


# Task 11: Custom Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with enhanced template and messaging"""
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    
    def form_valid(self, form):
        """Add success message and send email"""
        response = super().form_valid(form)
        
        email = form.cleaned_data['email']
        messages.success(
            self.request, 
            f'Password reset instructions have been sent to {email}. '
            f'Please check your email and follow the instructions to reset your password.'
        )
        
        return response


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Custom password reset done view"""
    template_name = 'registration/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view"""
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        """Add success message after password reset"""
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            '🎉 Your password has been successfully reset! You can now log in with your new password.'
        )
        
        return response


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Custom password reset complete view"""
    template_name = 'registration/password_reset_complete.html'


# Task 11: Custom Login View with Admin Redirect
class CustomLoginView(LoginView):
    """Custom login view that redirects based on user type"""
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        """Determine redirect URL based on user type"""
        user = self.request.user
        
        # Check if user is admin/staff
        if user.is_superuser or user.is_staff:
            return '/admin-panel/'
        else:
            return '/app/'
    
    def form_valid(self, form):
        """Add success message based on user type"""
        response = super().form_valid(form)
        user = form.get_user()
        
        if user.is_superuser or user.is_staff:
            messages.success(self.request, f'Welcome to Admin Panel, {user.username}!')
        else:
            messages.success(self.request, f'Welcome back, {user.username}!')
            
        return response


# ───────────────────  Generate Tailored Resume with Pure LLM Intelligence  ──────────────────

@require_http_methods(["POST"])
@login_required(login_url="login")
def generate_tailored_resume_ajax(
    request: HttpRequest,
    resume_id: int,
    template_id: int
) -> JsonResponse:
    """Start resume generation with login protection - Task 14"""
    try:
        resume = get_object_or_404(Resume, id=resume_id, user=request.user)
        payload = json.loads(request.body or "{}")
        job_desc = payload.get("job_description", "")
        num_pg = payload.get("num_pages", 1)

        if len(job_desc.strip()) < 50:
            return JsonResponse({
                "error": "Job description must be at least 50 characters"
            }, status=400)

        tpl_meta = next((t for t in TEMPLATES_LIST if t["id"] == template_id), None)
        if not tpl_meta:
            return JsonResponse({"error": "Template not found"}, status=400)

        tpl_path = os.path.join(
            settings.BASE_DIR, "resume", "templates", "resume",
            "templates_repo", tpl_meta["filename"]
        )
        if not os.path.exists(tpl_path):
            return JsonResponse({"error": "Template file missing"}, status=400)

        template_html = open(tpl_path, encoding="utf-8").read()
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize progress tracking
        progress_key = f"resume_progress_{task_id}"
        cache.set(progress_key, {
            "progress": 0,
            "status": "starting",
            "message": "Initializing intelligent LLM-driven optimization...",
            "completed": False,
            "error": None,
            "result": None,
            "iteration": 0,
            "current_scores": {"ats": 0, "job": 0},
            "analysis_phase": "starting"
        }, timeout=1800)
        
        # Start background task with pure LLM intelligence
        threading.Thread(
            target=process_intelligent_resume_generation,
            args=(task_id, resume.extracted_text, job_desc, template_html, num_pg, request.user.id, resume_id, template_id),
            daemon=True
        ).start()

        return JsonResponse({
            "success": True,
            "task_id": task_id,
            "message": "Intelligent LLM optimization started - analyzing job requirements first"
        })
        
    except Exception as exc:
        logger.exception("Generation failed: %s", exc)
        return JsonResponse({"error": f"Generation failed: {exc}"}, status=500)


@login_required(login_url="login")
def check_progress(request: HttpRequest, task_id: str) -> JsonResponse:
    """Check progress with login protection - Task 14"""
    progress_key = f"resume_progress_{task_id}"
    progress_data = cache.get(progress_key)
    
    if not progress_data:
        return JsonResponse({"error": "Task not found"}, status=404)
    
    return JsonResponse(progress_data)


def process_intelligent_resume_generation(task_id: str, resume_text: str, job_desc: str, template_html: str, num_pages: int, user_id: int, resume_id: int, template_id: int):
    """Background task with intelligent LLM-driven analysis and optimization"""
    progress_key = f"resume_progress_{task_id}"
    
    def update_progress(progress: int, status: str, message: str, iteration: int = 0, scores: dict = None, result: dict = None, error: str = None, analysis_phase: str = ""):
        cache.set(progress_key, {
            "progress": progress,
            "status": status,
            "message": message,
            "completed": progress >= 100,
            "error": error,
            "result": result,
            "iteration": iteration,
            "current_scores": scores or {"ats": 0, "job": 0},
            "analysis_phase": analysis_phase
        }, timeout=1800)
    
    try:
        # Phase 1: Intelligent job analysis by LLM
        update_progress(10, "analyzing", "🧠 LLM analyzing job description to extract all requirements...", 0, {"ats": 0, "job": 0}, analysis_phase="job_analysis")
        
        job_analysis = analyze_job_with_llm(job_desc)
        if not job_analysis:
            raise Exception("Failed to analyze job description")
        
        update_progress(20, "analyzing", f"✅ Job analysis complete: {len(job_analysis.get('keywords', []))} keywords, {len(job_analysis.get('skills', []))} skills identified", 0, {"ats": 0, "job": 0}, analysis_phase="resume_analysis")
        
        # Phase 2: Intelligent resume analysis
        update_progress(25, "analyzing", "🔍 LLM analyzing original resume structure and content...", 0, {"ats": 0, "job": 0}, analysis_phase="resume_analysis")
        
        resume_analysis = analyze_resume_with_llm(resume_text)
        if not resume_analysis:
            raise Exception("Failed to analyze resume")
        
        update_progress(35, "optimizing", f"📋 Resume analysis complete: Identified {len(resume_analysis.get('sections', []))} sections. Starting optimization...", 0, {"ats": 0, "job": 0}, analysis_phase="optimization")
        
        # Phase 3: Unlimited intelligent optimization
        html_resume, ats_score, job_score, final_iteration = intelligent_resume_optimization(
            resume_text, job_desc, template_html, num_pages, job_analysis, resume_analysis,
            lambda p, m, i, s, phase: update_progress(35 + int(p * 0.6), "optimizing", m, i, s, analysis_phase=phase)
        )
        
        # Phase 4: Final validation
        update_progress(95, "validating", f"🎯 Optimization complete! ATS: {ats_score}%, Job: {job_score}% (Iterations: {final_iteration})", final_iteration, {"ats": ats_score, "job": job_score}, analysis_phase="complete")
        
        # Store results
        session_key = f"tailored_resume_{user_id}_{resume_id}"
        cache.set(session_key, {
            "tailored_resume": html_resume,
            "ats_score": ats_score,
            "job_score": job_score,
            "resume_id": resume_id,
            "template_id": template_id,
            "iterations_used": final_iteration,
            "job_analysis": job_analysis,
            "resume_analysis": resume_analysis
        }, timeout=3600)
        
        # Phase 5: Complete
        update_progress(100, "completed", f"🎉 TARGET ACHIEVED! ATS: {ats_score}%, Job: {job_score}% (Iterations: {final_iteration})", final_iteration, {"ats": ats_score, "job": job_score}, {
            "final_resume": html_resume,
            "ats_score": ats_score,
            "job_score": job_score,
            "session_key": session_key,
            "iterations_used": final_iteration,
            "job_analysis": job_analysis
        }, analysis_phase="complete")
        
    except Exception as e:
        logger.exception(f"Intelligent resume generation failed for task {task_id}: {e}")
        update_progress(0, "error", f"Generation failed: {str(e)}", error=str(e), analysis_phase="error")


def analyze_job_with_llm(job_desc: str) -> dict:
    """Let LLM intelligently analyze job description and extract all requirements"""
    
    # Use string concatenation instead of f-string to avoid formatting issues
    analysis_prompt = """You are an expert job analysis AI. Your task is to comprehensively analyze the following job description and extract ALL important elements that a resume should match.

JOB DESCRIPTION TO ANALYZE:
""" + job_desc + """

ANALYSIS REQUIREMENTS:
1. Extract the exact job title and any alternative titles
2. Identify ALL technical skills mentioned (programming languages, tools, frameworks, platforms, etc.)
3. Identify ALL soft skills and interpersonal requirements
4. Extract required qualifications, education, and experience levels
5. Identify key industry keywords and domain-specific terminology
6. Extract action verbs and achievement-oriented language used
7. Identify company values, culture keywords, and working style preferences
8. Determine the seniority level and career stage this role targets
9. Extract any certifications, methodologies, or specialized knowledge required
10. Identify measurement criteria and KPI-related terms

EXTRACTION INSTRUCTIONS:
- Be comprehensive - extract every skill, keyword, and requirement mentioned
- Include variations and synonyms (e.g., if "AI" is mentioned, also note "Artificial Intelligence")
- Capture both explicit requirements and implied needs
- Note the frequency/importance of different terms based on repetition
- Identify the primary vs secondary skills based on emphasis in the job description

OUTPUT FORMAT:
Return a detailed JSON object with the following structure:
{
    "job_title": "Primary job title",
    "alternative_titles": ["list of alternative titles or related roles"],
    "technical_skills": ["comprehensive list of all technical skills"],
    "soft_skills": ["all soft skills and interpersonal requirements"], 
    "programming_languages": ["all programming languages mentioned"],
    "tools_platforms": ["all tools, platforms, software mentioned"],
    "frameworks_libraries": ["all frameworks, libraries, APIs mentioned"],
    "methodologies": ["agile, scrum, devops, etc."],
    "certifications": ["any certifications or credentials mentioned"],
    "education_requirements": ["degree requirements, field of study, etc."],
    "experience_level": "entry/mid/senior level description",
    "key_keywords": ["most important keywords for ATS"],
    "action_verbs": ["action verbs used in job description"],
    "industry_terms": ["domain-specific terminology"],
    "company_values": ["culture and value keywords"],
    "measurements_kpis": ["metrics, KPIs, measurement terms"],
    "priority_skills": ["top 10 most important skills based on emphasis"],
    "nice_to_have": ["preferred but not required skills"],
    "total_analysis": "Brief summary of the role and key requirements"
}

Be thorough and extract everything that could be relevant for resume optimization."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(response.choices[0].message.content)
        logger.info(f"Job analysis extracted {len(analysis.get('key_keywords', []))} keywords and {len(analysis.get('technical_skills', []))} technical skills")
        return analysis
        
    except Exception as e:
        logger.error(f"Job analysis failed: {e}")
        return None


def analyze_resume_with_llm(resume_text: str) -> dict:
    """Let LLM intelligently analyze the original resume structure and content"""
    
    # Use string concatenation to avoid f-string formatting issues
    analysis_prompt = """You are an expert resume analysis AI. Analyze the following resume and extract its complete structure, content, and optimization opportunities.

RESUME TO ANALYZE:
""" + resume_text + """

ANALYSIS REQUIREMENTS:
1. Identify all sections present in the resume (summary, experience, education, skills, projects, etc.)
2. Extract all work experiences with companies, titles, dates, and descriptions
3. Extract all educational qualifications with institutions, degrees, and dates
4. Extract all projects with descriptions and technologies
5. Identify current skills mentioned and categorize them
6. Extract contact information and personal details
7. Identify the current professional level and career focus
8. Analyze the writing style and language used
9. Identify strengths and areas for improvement
10. Determine which sections exist vs which are missing

EXTRACTION INSTRUCTIONS:
- Preserve all factual information exactly (names, companies, dates, institutions)
- Identify which sections have substantial content vs minimal content
- Note the current tone and style of writing
- Identify gaps where content could be enhanced
- Categorize existing skills and experiences

OUTPUT FORMAT:
Return a detailed JSON object:
{
    "personal_info": {
        "name": "exact name",
        "email": "email address", 
        "phone": "phone number",
        "location": "location/address"
    },
    "sections_present": ["list of all sections that exist"],
    "sections_with_content": ["sections that have substantial content"],
    "sections_minimal": ["sections with minimal content"],
    "work_experiences": [
        {
            "title": "exact job title",
            "company": "exact company name", 
            "dates": "employment dates",
            "description": "current description",
            "achievements": ["extracted achievements"]
        }
    ],
    "education": [
        {
            "degree": "exact degree name",
            "institution": "exact institution name",
            "dates": "education dates",
            "details": "additional details if any"
        }
    ],
    "projects": [
        {
            "title": "project title",
            "description": "project description",
            "technologies": ["technologies used"]
        }
    ],
    "current_skills": {
        "technical": ["current technical skills"],
        "soft": ["current soft skills"],
        "tools": ["tools and platforms"]
    },
    "professional_summary": "current summary/objective if present",
    "career_level": "assessment of seniority level",
    "writing_style": "description of current tone and style",
    "strengths": ["current resume strengths"],
    "improvement_areas": ["areas that need enhancement"],
    "total_analysis": "Overall assessment of the resume"
}

Preserve all factual information exactly while identifying optimization opportunities."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        
        analysis = json.loads(response.choices[0].message.content)
        logger.info(f"Resume analysis identified {len(analysis.get('sections_present', []))} sections and {len(analysis.get('work_experiences', []))} work experiences")
        return analysis
        
    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        return None


def intelligent_resume_optimization(
    resume_text: str,
    job_desc: str, 
    template_html: str,
    num_pages: Optional[int] = None,
    job_analysis: dict = None,
    resume_analysis: dict = None,
    progress_callback = None
) -> Tuple[str, int, int, int]:
    """Pure LLM-driven intelligent resume optimization with unlimited iterations"""
    
    if not settings.OPENAI_API_KEY:
        logger.error("OpenAI key missing – using fallback")
        if progress_callback:
            progress_callback(100, "Using fallback resume generation...", 1, {"ats": 70, "job": 50}, "fallback")
        return _create_fallback_resume(resume_text, template_html), 70, 50, 1

    if progress_callback:
        progress_callback(0, "Preparing intelligent optimization strategy...", 0, {"ats": 0, "job": 0}, "preparation")

    # Create the master optimization prompt - using string concatenation to avoid f-string issues
    system_prompt = """You are the world's most advanced ATS resume optimization AI. Your mission is to achieve MINIMUM """ + str(TARGET_ATS_SCORE) + """% ATS score and """ + str(TARGET_JOB_SCORE) + """% job match through intelligent, data-driven optimization with STRICT page count adherence.

CRITICAL SUCCESS CRITERIA:
- ATS Score: MUST be ≥ """ + str(TARGET_ATS_SCORE) + """%
- Job Match Score: MUST be ≥ """ + str(TARGET_JOB_SCORE) + """%
- Page Count: MUST be EXACTLY """ + str(num_pages or 1) + """ page(s) - NO MORE, NO LESS
- If scores below target, provide specific, actionable improvement suggestions

PAGE COUNT ENFORCEMENT RULES:
- TARGET PAGES: """ + str(num_pages or 1) + """ page(s) EXACTLY
- MUST fill entire page(s) with NO blank spaces at bottom
- If content doesn't fill completely, ADD "Why Should You Hire Me?" section at the end
- Content density should be optimized for the exact page count specified
- Use appropriate spacing, bullet points, and formatting to achieve target length

JOB ANALYSIS RESULTS:
""" + (json.dumps(job_analysis, indent=2) if job_analysis else "No job analysis available") + """

RESUME ANALYSIS RESULTS:
""" + (json.dumps(resume_analysis, indent=2) if resume_analysis else "No resume analysis available") + """

INTELLIGENT OPTIMIZATION STRATEGY:

1. PRESERVE FACTUAL ACCURACY:
   - Keep personal information EXACTLY as in original (name, phone, email, location)
   - Keep job titles, company names, and institution names EXACTLY as in original
   - Keep employment dates and education dates EXACTLY as in original
   - Preserve the factual foundation while transforming presentation

2. AGGRESSIVE CONTENT TRANSFORMATION:
   - COMPLETELY REWRITE professional summary using job analysis keywords and requirements
   - Transform job descriptions to highlight achievements that match job requirements
   - Rewrite project descriptions to emphasize relevance to target role
   - ADD missing skills identified in job analysis
   - Use job-specific action verbs and terminology throughout
   - Quantify achievements with metrics and impact statements

3. INTELLIGENT SKILLS OPTIMIZATION:
   - COMPLETELY REPLACE skills section with job-relevant skills from analysis
   - Prioritize technical skills, programming languages, and tools from job requirements
   - Include soft skills and methodologies mentioned in job description
   - Organize skills by relevance and importance to the role
   - Ensure comprehensive coverage of job requirements

4. STRICT PAGE COUNT MANAGEMENT:
   - Calculate content length to fill EXACTLY """ + str(num_pages or 1) + """ page(s)
   - Expand or condense content as needed to meet page target
   - If pages not completely filled, ADD "Why Should You Hire Me?" section:
     * Question: "Why Should You Hire Me?"
     * Answer: 3-5 compelling bullet points based on tailored resume content
     * Highlight unique value proposition for the specific role
     * Emphasize key achievements and skills that match job requirements
   - Use strategic spacing and formatting to optimize page utilization

5. DYNAMIC SECTION HANDLING:
   - Only include sections that exist in original resume (based on resume analysis)
   - Place sections in optimal order: Summary → Experience → Projects (if exists) → Education → Skills → Why Hire Me? (if needed)
   - Remove any template conditional syntax and return clean HTML
   - Ensure every included section is fully optimized for the target role

6. KEYWORD INTEGRATION MASTERY:
   - Naturally integrate ALL priority keywords from job analysis
   - Use industry terminology and domain-specific language
   - Include company values and culture keywords where appropriate
   - Ensure proper keyword density for ATS optimization
   - Match the tone and style of the job description

7. SCORING OPTIMIZATION:
   - If ATS score low: Focus on keyword integration, formatting, section structure
   - If Job score low: Focus on content relevance, role-specific achievements, terminology
   - Provide specific suggestions for reaching target scores
   - Identify exact gaps and how to address them

PAGE ESTIMATION GUIDELINES:
- 1 page ≈ 500-650 words (tight formatting)
- 2 pages ≈ 900-1200 words (balanced formatting)
- 3 pages ≈ 1300-1800 words (detailed formatting)
- Adjust content density, bullet points, and spacing to achieve exact page target

"WHY SHOULD YOU HIRE ME?" SECTION FORMAT:
If additional content needed to fill pages completely, add this section:

<h2>Why Should You Hire Me?</h2>
<div class="section-content">
<ul>
<li>[Compelling reason 1 based on job requirements and resume achievements]</li>
<li>[Compelling reason 2 highlighting unique skills and experience]</li>
<li>[Compelling reason 3 emphasizing quantified results and impact]</li>
<li>[Compelling reason 4 showing cultural fit and role-specific expertise]</li>
<li>[Compelling reason 5 demonstrating value proposition for the company]</li>
</ul>
</div>

OUTPUT REQUIREMENTS:
Return JSON with:
- html_resume: Complete optimized HTML (EXACTLY """ + str(num_pages or 1) + """ page(s))
- ats_score: ATS compatibility score (0-100)
- job_score: Job match percentage (0-100)
- page_count_achieved: Actual page count of final resume
- page_utilization: Percentage of page space utilized
- improvements_needed: Specific suggestions if scores below target
- optimization_applied: Description of optimizations made
- sections_included: List of sections included in final resume
- keywords_integrated: Number of job keywords successfully integrated
- why_hire_me_added: Boolean indicating if "Why Should You Hire Me?" section was added

CRITICAL INSTRUCTIONS:
- MUST achieve EXACTLY """ + str(num_pages or 1) + """ page(s) - no exceptions
- Fill entire page space with no blank areas at bottom
- Use job analysis and resume analysis to make intelligent decisions
- Be aggressive in optimization while maintaining factual accuracy
- Every section should be transformed to match job requirements
- Skills section must be completely rewritten based on job needs
- Professional summary must perfectly align with job requirements
- Remove ALL template syntax and return clean HTML
- If content insufficient for target pages, ADD "Why Should You Hire Me?" section"""

    user_prompt = """
ORIGINAL RESUME:
""" + resume_text + """

TARGET JOB DESCRIPTION:
""" + job_desc + """

HTML TEMPLATE:
""" + template_html + """

STRICT PAGE REQUIREMENT: """ + str(num_pages or 1) + """ page(s) EXACTLY

OPTIMIZATION MISSION:
Using the comprehensive job analysis and resume analysis provided, intelligently transform this resume to achieve """ + str(TARGET_ATS_SCORE) + """%+ ATS score and """ + str(TARGET_JOB_SCORE) + """%+ job match with STRICT adherence to """ + str(num_pages or 1) + """ page(s).

SPECIFIC REQUIREMENTS:
1. Use job analysis to completely rewrite professional summary
2. Transform work experience descriptions to highlight job-relevant achievements  
3. Rewrite skills section based on job requirements (technical skills, tools, etc.)
4. Integrate priority keywords naturally throughout all sections
5. Only include sections that exist in original resume
6. Return clean HTML without any template conditionals
7. Ensure every section is optimized for the target role
8. MUST fill EXACTLY """ + str(num_pages or 1) + """ page(s) with NO blank space at bottom
9. If content insufficient, ADD "Why Should You Hire Me?" section to fill remaining space

PAGE COUNT ENFORCEMENT:
- Target: """ + str(num_pages or 1) + """ page(s) EXACTLY
- Expand content with more detailed bullet points if too short
- Add "Why Should You Hire Me?" section if needed to fill remaining space
- Use appropriate formatting and spacing to achieve target length
- NO blank spaces allowed at bottom of final page

Transform aggressively while preserving factual accuracy and achieving exact page count.
"""

    # Initialize tracking
    iteration = 0
    best_resume, best_ats, best_job = "", 0, 0
    conversation_history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Unlimited intelligent optimization loop
    while True:
        iteration += 1
        
        try:
            if progress_callback:
                progress_callback(
                    min(95, 10 + (iteration * 3)), 
                    f"Iteration {iteration}: Intelligent optimization in progress...",
                    iteration,
                    {"ats": best_ats, "job": best_job},
                    "optimization"
                )
            
            # Call LLM for intelligent optimization
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=conversation_history,
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response.choices[0].message.content)
            ats_score = int(data.get("ats_score", 0))
            job_score = int(data.get("job_score", 0))
            html_resume = data.get("html_resume", "")
            page_count_achieved = data.get("page_count_achieved", 0)
            page_utilization = data.get("page_utilization", 0)
            improvements_needed = data.get("improvements_needed", [])
            optimization_applied = data.get("optimization_applied", "")
            sections_included = data.get("sections_included", [])
            keywords_integrated = data.get("keywords_integrated", 0)
            why_hire_me_added = data.get("why_hire_me_added", False)

            # Clean up HTML
            html_resume = post_process_html(html_resume, template_html)

            # Update best scores
            if html_resume and (ats_score > best_ats or job_score > best_job):
                best_resume, best_ats, best_job = html_resume, ats_score, job_score

            logger.info(f"Iteration {iteration}: ATS={ats_score}%, Job={job_score}%, Pages={page_count_achieved}, Utilization={page_utilization}%, WhyHireMe={why_hire_me_added}")

            # Check if target scores achieved AND page count is correct
            target_pages = num_pages or 1
            page_count_ok = page_count_achieved == target_pages
            scores_ok = ats_score >= TARGET_ATS_SCORE and job_score >= TARGET_JOB_SCORE
            
            if scores_ok and page_count_ok:
                if progress_callback:
                    progress_callback(95, f"🎉 TARGET ACHIEVED! ATS: {ats_score}%, Job: {job_score}%, Pages: {page_count_achieved}", iteration, {"ats": ats_score, "job": job_score}, "success")
                logger.info(f"ALL TARGETS ACHIEVED in {iteration} iterations: ATS={ats_score}%, Job={job_score}%, Pages={page_count_achieved}")
                return html_resume, ats_score, job_score, iteration

            # Safety check
            if iteration >= 50:
                logger.warning(f"Reached 50 iterations. Best: ATS={best_ats}%, Job={best_job}%")
                return best_resume or html_resume, best_ats or ats_score, best_job or job_score, iteration

            # Generate intelligent improvement strategy including page count
            improvement_strategy = generate_improvement_strategy_with_pages(
                ats_score, job_score, page_count_achieved, target_pages, page_utilization,
                improvements_needed, job_analysis, resume_analysis, iteration, why_hire_me_added
            )

            # Add to conversation for next iteration
            conversation_history.extend([
                {"role": "assistant", "content": json.dumps(data)},
                {"role": "user", "content": improvement_strategy}
            ])

            # Continue optimization
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Iteration {iteration} failed: {e}")
            if iteration == 1:
                if progress_callback:
                    progress_callback(95, "Using intelligent fallback...", 1, {"ats": 70, "job": 50}, "fallback")
                return _create_intelligent_fallback(resume_text, template_html, job_analysis, resume_analysis), 70, 50, 1
            else:
                return best_resume, best_ats, best_job, iteration


def generate_improvement_strategy_with_pages(
    ats_score: int, 
    job_score: int, 
    page_count_achieved: int, 
    target_pages: int, 
    page_utilization: int,
    improvements_needed: list, 
    job_analysis: dict, 
    resume_analysis: dict, 
    iteration: int,
    why_hire_me_added: bool
) -> str:
    """Generate intelligent improvement strategy including page count enforcement"""
    
    strategy_parts = [
        f"ITERATION {iteration} ANALYSIS:",
        f"- ATS Score: {ats_score}% (Target: {TARGET_ATS_SCORE}%+)",
        f"- Job Score: {job_score}% (Target: {TARGET_JOB_SCORE}%+)",
        f"- Page Count: {page_count_achieved}/{target_pages} pages (Target: EXACTLY {target_pages})",
        f"- Page Utilization: {page_utilization}% (Target: 100%)",
        f"- Why Hire Me Added: {why_hire_me_added}",
        "",
        "INTELLIGENT IMPROVEMENT STRATEGY:"
    ]
    
    # Page count enforcement
    if page_count_achieved != target_pages:
        if page_count_achieved < target_pages:
            strategy_parts.extend([
                f"📄 PAGE COUNT CRITICAL (UNDER TARGET):",
                f"- Current: {page_count_achieved} pages, Need: {target_pages} pages",
                "- EXPAND content in all sections with more detailed bullet points",
                "- Add more comprehensive project descriptions",
                "- Include additional quantified achievements in work experience",
                "- Add more detailed skills explanations",
                "- MUST add 'Why Should You Hire Me?' section to fill remaining space",
                "- Use strategic spacing and formatting to reach target pages"
            ])
        else:
            strategy_parts.extend([
                f"📄 PAGE COUNT CRITICAL (OVER TARGET):",
                f"- Current: {page_count_achieved} pages, Need: {target_pages} pages",
                "- CONDENSE content while maintaining quality",
                "- Use more concise bullet points",
                "- Optimize spacing and formatting",
                "- Combine related bullet points",
                "- Remove less critical details while keeping core achievements"
            ])
    
    # Page utilization optimization
    if page_utilization < 95:
        strategy_parts.extend([
            f"",
            f"📊 PAGE UTILIZATION IMPROVEMENT (Current: {page_utilization}%):",
            "- Fill remaining white space at bottom of pages",
            "- Add 'Why Should You Hire Me?' section if not already present",
            "- Expand existing sections with more content",
            "- Use better spacing distribution",
            "- Add more bullet points to work experience and projects"
        ])
    
    # ATS-specific improvements
    if ats_score < TARGET_ATS_SCORE:
        ats_gap = TARGET_ATS_SCORE - ats_score
        strategy_parts.extend([
            f"",
            f"🎯 ATS OPTIMIZATION (Need {ats_gap}% improvement):",
            "- Integrate more technical keywords from job analysis",
            "- Ensure all priority skills are included in skills section",
            "- Use exact terminology from job description",
            "- Improve section formatting and structure"
        ])
        
        if job_analysis:
            priority_skills = job_analysis.get('priority_skills', [])[:5]
            strategy_parts.append(f"- MUST include these priority skills: {', '.join(priority_skills)}")
    
    # Job match improvements  
    if job_score < TARGET_JOB_SCORE:
        job_gap = TARGET_JOB_SCORE - job_score
        strategy_parts.extend([
            f"",
            f"🎯 JOB MATCH OPTIMIZATION (Need {job_gap}% improvement):",
            "- Rewrite professional summary to mirror job requirements more closely",
            "- Transform work experience to highlight job-relevant achievements",
            "- Add more role-specific action verbs and terminology",
            "- Emphasize qualifications and experience that match job needs"
        ])
        
        if job_analysis:
            job_title = job_analysis.get('job_title', '')
            action_verbs = job_analysis.get('action_verbs', [])[:5]
            strategy_parts.extend([
                f"- Include job title terminology: {job_title}",
                f"- Use these action verbs: {', '.join(action_verbs)}"
            ])
    
    # Why Should You Hire Me section guidance
    if not why_hire_me_added and (page_count_achieved < target_pages or page_utilization < 90):
        strategy_parts.extend([
            f"",
            "💡 'WHY SHOULD YOU HIRE ME?' SECTION REQUIRED:",
            "- Add this section to fill remaining page space",
            "- Include 3-5 compelling bullet points",
            "- Highlight unique value proposition for the role",
            "- Emphasize quantified achievements and impact",
            "- Connect directly to job requirements and company needs",
            "- Use this format:",
            "  <h2>Why Should You Hire Me?</h2>",
            "  <div class='section-content'>",
            "  <ul>",
            "  <li>[Compelling reason based on job match]</li>",
            "  <li>[Unique skill/experience highlight]</li>",
            "  <li>[Quantified achievement/impact]</li>",
            "  <li>[Cultural fit/expertise demonstration]</li>",
            "  <li>[Value proposition for company]</li>",
            "  </ul>",
            "  </div>"
        ])
    
    # Specific improvements from LLM
    if improvements_needed:
        strategy_parts.extend([
            "",
            "📋 SPECIFIC IMPROVEMENTS NEEDED:",
            *[f"- {improvement}" for improvement in improvements_needed[:5]]
        ])
    
    # Advanced optimization based on analysis
    strategy_parts.extend([
        "",
        "🚀 ADVANCED OPTIMIZATION:",
        f"- Target EXACTLY {target_pages} page(s) with 100% utilization",
        "- Ensure every section contributes to job match",
        "- Use quantified achievements with metrics",
        "- Include industry-specific terminology",
        "- Optimize keyword density naturally",
        "- Match the tone and style of job description",
        "- NO blank spaces allowed at bottom of pages"
    ])
    
    # Page-specific recommendations
    if target_pages == 1:
        strategy_parts.extend([
            "",
            "📄 ONE-PAGE OPTIMIZATION:",
            "- Tight, concise formatting with no wasted space",
            "- 4-6 bullet points per work experience",
            "- Compact but comprehensive skills section",
            "- Brief but impactful professional summary"
        ])
    elif target_pages == 2:
        strategy_parts.extend([
            "",
            "📄 TWO-PAGE OPTIMIZATION:",
            "- Balanced content distribution across both pages",
            "- Detailed work experience descriptions",
            "- Comprehensive skills and projects sections",
            "- Extended professional summary if needed"
        ])
    elif target_pages >= 3:
        strategy_parts.extend([
            "",
            "📄 THREE+ PAGE OPTIMIZATION:",
            "- Detailed descriptions for all sections",
            "- Multiple bullet points per achievement",
            "- Comprehensive project descriptions",
            "- Detailed skills categorization",
            "- Extended 'Why Should You Hire Me?' section"
        ])
    
    return "\n".join(strategy_parts)


def post_process_html(html_resume: str, original_template: str) -> str:
    """Clean and validate the generated HTML"""
    
    # Remove any remaining template conditionals
    html_resume = re.sub(r'\{\{#if_\w+\}\}', '', html_resume)
    html_resume = re.sub(r'\{\{/if_\w+\}\}', '', html_resume)
    html_resume = re.sub(r'\{\{\w+\}\}', '', html_resume)
    
    # Ensure proper HTML structure
    if not html_resume.startswith('<!DOCTYPE html>'):
        # Extract style from original template
        style_match = re.search(r'<style>(.*?)</style>', original_template, re.DOTALL)
        style_content = style_match.group(1) if style_match else ""
        
        html_resume = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Optimized Resume</title>
<style>
{style_content}
</style>
</head>
<body>
{html_resume}
</body>
</html>"""
    
    # Clean up extra whitespace
    html_resume = re.sub(r'\n\s*\n\s*\n', '\n\n', html_resume)
    
    return html_resume


def _create_intelligent_fallback(resume_text: str, template_html: str, job_analysis: dict, resume_analysis: dict) -> str:
    """Create intelligent fallback using LLM analysis"""
    try:
        # Extract key information
        contact_info = resume_analysis.get('personal_info', {}) if resume_analysis else {}
        work_experiences = resume_analysis.get('work_experiences', []) if resume_analysis else []
        education = resume_analysis.get('education', []) if resume_analysis else []
        projects = resume_analysis.get('projects', []) if resume_analysis else []
        
        # Generate intelligent professional summary
        job_title = job_analysis.get('job_title', 'Professional') if job_analysis else 'Professional'
        priority_skills = job_analysis.get('priority_skills', [])[:5] if job_analysis else []
        
        if priority_skills:
            summary = f"Results-driven {job_title} with expertise in {', '.join(priority_skills)}. Proven track record of delivering impactful solutions and driving business growth through innovative approaches and technical excellence."
        else:
            summary = f"Experienced {job_title} with proven expertise and strong track record of delivering innovative solutions and driving organizational success."
        
        # Build sections HTML
        sections_html = []
        
        # Header and contact
        sections_html.append(f"""
<h1>{contact_info.get('name', 'Professional Candidate')}</h1>
<p class="contact">{contact_info.get('email', 'email@example.com')} • {contact_info.get('phone', '(555) 123-4567')} • {contact_info.get('location', 'Location')}</p>

<h2>Professional Summary</h2>
<div class="section-content">{summary}</div>""")
        
        # Work Experience
        if work_experiences:
            work_html = ""
            for exp in work_experiences[:4]:
                work_html += f"""
<div class="job-entry">
    <h3>{exp.get('title', 'Professional Role')} — {exp.get('company', 'Company')}</h3>
    <p><em>{exp.get('dates', 'Date Range')}</em></p>
    <ul>
        <li>Led strategic initiatives resulting in measurable business impact and operational improvements</li>
        <li>Collaborated with cross-functional teams to deliver high-quality solutions and achieve organizational objectives</li>
        <li>Implemented innovative approaches that enhanced efficiency and drove continuous improvement</li>
    </ul>
</div>"""
        else:
            work_html = """
<div class="job-entry">
    <h3>Professional Experience</h3>
    <ul><li>Extensive professional background with relevant industry experience and proven results</li></ul>
</div>"""
        
        sections_html.append(f"""
<h2>Work Experience</h2>
<div class="section-content">{work_html}</div>""")
        
        # Projects (if they exist)
        if projects:
            projects_html = ""
            for project in projects[:3]:
                projects_html += f"""
<div class="job-entry">
    <h3>{project.get('title', 'Project Title')}</h3>
    <ul><li>{project.get('description', 'Developed comprehensive solution addressing key technical and business requirements')}</li></ul>
</div>"""
            sections_html.append(f"""
<h2>Projects</h2>
<div class="section-content">{projects_html}</div>""")
        
        # Education
        if education:
            edu_html = ""
            for edu in education[:2]:
                edu_html += f"<p><strong>{edu.get('degree', 'Degree')}, {edu.get('institution', 'Institution')} — {edu.get('dates', 'Year')}</strong></p>"
        else:
            edu_html = "<p><strong>Relevant Education and Training</strong></p>"
        
        sections_html.append(f"""
<h2>Education</h2>
<div class="section-content">{edu_html}</div>""")
        
        # Optimized Skills
        if job_analysis:
            all_skills = []
            for skill_category in ['technical_skills', 'programming_languages', 'tools_platforms', 'frameworks_libraries', 'soft_skills']:
                all_skills.extend(job_analysis.get(skill_category, [])[:5])
            skills_text = ", ".join(all_skills[:20]) if all_skills else "Technical Skills, Problem Solving, Leadership, Communication, Project Management"
        else:
            skills_text = "Technical Skills, Problem Solving, Leadership, Communication, Project Management"
        
        sections_html.append(f"""
<h2>Skills</h2>
<div class="section-content">{skills_text}</div>""")
        
        # Extract style from template
        style_match = re.search(r'<style>(.*?)</style>', template_html, re.DOTALL)
        style_content = style_match.group(1) if style_match else ""
        
        # Combine all sections
        final_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Optimized Resume</title>
<style>
{style_content}
</style>
</head>
<body>
{''.join(sections_html)}
</body>
</html>"""
        
        return final_html
        
    except Exception as e:
        logger.error(f"Intelligent fallback failed: {e}")
        return template_html


# ───────────────────────  PDF Download  ───────────────────────

@login_required(login_url="login")
def download_pdf_ajax(request: HttpRequest, resume_id: int) -> HttpResponse:
    """
    Tailored-resume PDF download with:
    • Per-user rate limits (configurable)
    • Cache / session fallback
    • Filename sanitising
    """
    # ── 1. Resolve rate-limit caps ───────────────────────────────────────
    LIMIT_15, LIMIT_MONTH = 3, 6            # safe defaults
    if not request.user.is_superuser:
        # a) user.profile fields (preferred – add IntegerFields to your profile model)
        if hasattr(request.user, "profile"):
            LIMIT_15 = request.user.profile.limit_15_days or LIMIT_15
            LIMIT_MONTH = request.user.profile.limit_month or LIMIT_MONTH
        # b) session override (set by your custom admin panel)
        sess_key = f"user_{request.user.id}_download_limits"
        if (custom := request.session.get(sess_key)):
            LIMIT_15   = custom.get("per_15_days", LIMIT_15)
            LIMIT_MONTH = custom.get("per_month", LIMIT_MONTH)

        # actual usage counters
        past_15      = now() - timedelta(days=15)
        month_start  = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        count_15     = DownloadLog.objects.filter(user=request.user,
                                                  downloaded__gte=past_15).count()
        count_month  = DownloadLog.objects.filter(user=request.user,
                                                  downloaded__gte=month_start).count()

        if count_15 >= LIMIT_15 or count_month >= LIMIT_MONTH:
            wa_number  = settings.WHATSAPP_PHONE_NUMBER
            wa_msg     = settings.WHATSAPP_DEFAULT_MESSAGE
            contact_url = f"https://wa.me/916303858671?text=Hi! Can you please increase my qouta?"
            return JsonResponse({
                "message": (
                    "🚫 You have crossed your free limit. "
                    "Please contact us on WhatsApp to increase the quota."
                ),
                "contact_url": contact_url,
                "limit_15": LIMIT_15,
                "limit_month": LIMIT_MONTH,
            }, status=429)

    # ── 2. Load pre-generated HTML (cache → session) ────────────────────
    cache_key   = f"tailored_resume_{request.user.id}_{resume_id}"
    session_key = "tailored_resume"
    data        = cache.get(cache_key) or {"tailored_resume": request.session.get(session_key)}
    html_resume = data.get("tailored_resume")

    if not html_resume:
        return JsonResponse({"error": "Generate resume first"}, status=400)

    # ── 3. Ensure resume belongs to user ─────────────────────────────────
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)

    # ── 4. Build safe filename -------------------------------------------------
    safe = lambda s: re.sub(r"[^A-Za-z0-9 _-]+", "", s).strip().lower()
    tpl_meta   = next((t for t in TEMPLATES_LIST if t["id"] == data.get("template_id")), None)
    style_name = (tpl_meta["name"].split()[0] + " style") if tpl_meta else "style"
    filename   = f"{safe(resume.user.username)} - {safe(style_name)} - llm-optimized.pdf"

    # ── 5. Render → PDF + log download ───────────────────────────────────
    pdf_html  = render_to_string("resume/pdf_template.html", {"final_resume": html_resume})
    pdf_bytes = HTML(string=pdf_html).write_pdf()
    DownloadLog.objects.create(user=request.user, resume=resume)  # keep a trail

    # ── 6. Ship it ───────────────────────────────────────────────────────
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

# ─────────────────────  Template List AJAX  ─────────────────────

@login_required(login_url="login")
def get_templates_ajax(request: HttpRequest) -> JsonResponse:
    """Get templates with login protection - Task 14"""
    return JsonResponse({"templates": TEMPLATES_LIST})

# ────────────────────────  Resume API  ────────────────────────

class ResumeAPIView(View):
    """Resume API with login protection - Task 14"""
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure user is logged in
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, resume_id=None):
        """Get resume(s) for the current user"""
        try:
            if resume_id:
                r = get_object_or_404(Resume, id=resume_id, user=request.user)
                return JsonResponse({
                    "id": r.id,
                    "filename": r.file.name,
                    "created_at": r.created_at.isoformat(),
                    "file_size": r.file_size,
                    "extracted_text": (
                        (r.extracted_text[:500] + "…")
                        if r.extracted_text and len(r.extracted_text) > 500
                        else r.extracted_text
                    )
                })
            
            # Get all resumes for user
            qs = Resume.objects.filter(user=request.user).order_by('-created_at')
            return JsonResponse({
                "resumes": [
                    {
                        "id": r.id,
                        "filename": r.file.name,
                        "created_at": r.created_at.isoformat(),
                        "file_size": r.file_size
                    }
                    for r in qs
                ]
            })
        except Exception as exc:
            logger.exception("API GET error: %s", exc)
            return JsonResponse({"error": str(exc)}, status=500)
    
    def delete(self, request, resume_id):
        """Delete a specific resume"""
        try:
            if not resume_id:
                return JsonResponse({"error": "Resume ID required"}, status=400)
            
            resume = get_object_or_404(Resume, id=resume_id, user=request.user)
            
            # Store filename for response
            filename = resume.file.name
            
            # Delete the file from storage
            if resume.file:
                try:
                    resume.file.delete(save=False)
                except Exception as e:
                    logger.warning(f"Failed to delete file {resume.file.name}: {e}")
            
            # Delete the database record
            resume.delete()
            
            logger.info(f"Resume {resume_id} ({filename}) deleted by user {request.user.id}")
            
            return JsonResponse({
                "success": True,
                "message": f"Resume '{filename}' deleted successfully",
                "deleted_id": resume_id
            })
            
        except Resume.DoesNotExist:
            return JsonResponse({"error": "Resume not found"}, status=404)
        except Exception as exc:
            logger.exception("Resume deletion failed: %s", exc)
            return JsonResponse({"error": f"Failed to delete resume: {str(exc)}"}, status=500)
    
    # def put(self, request, resume_id):
    #     """Update resume metadata (optional enhancement)"""
    #     try:
    #         resume = get_object_or_404(Resume, id=resume_id, user=request.user)
            
    #         # Parse JSON data
    #         try:
    #             data = json.loads(request.body)
    #         except json.JSONDecodeError:
    #             return JsonResponse({"error": "Invalid JSON data"}, status=400)
            
    #         # Update allowed fields (you can extend this)
    #         updated_fields = []
            
    #         # Example: Allow updating a custom name/title
    #         if 'title' in data:
    #             # You'd need to add a title field to your Resume model first
    #             # resume.title = data['title']
    #             # updated_fields.append('title')
    #             pass
            
    #         if updated_fields:
    #             resume.save(update_fields=updated_fields)
    #             return JsonResponse({
    #                 "success": True,
    #                 "message": f"Resume updated: {', '.join(updated_fields)}",
    #                 "updated_fields": updated_fields
    #             })
    #         else:
    #             return JsonResponse({"message": "No fields to update"})
                
    #     except Resume.DoesNotExist:
    #         return JsonResponse({"error": "Resume not found"}, status=404)
    #     except Exception as exc:
    #         logger.exception("Resume update failed: %s", exc)
    #         return JsonResponse({"error": f"Failed to update resume: {str(exc)}"}, status=500)


# ─────────────────────  Initial Analysis AJAX  ─────────────────────

@require_http_methods(["POST"])
@login_required(login_url="login")
def analyze_resume_ajax(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body)
        job_desc = data.get("job_description", "")
        
        # Let LLM do the analysis
        job_analysis = analyze_job_with_llm(job_desc)
        
        if job_analysis:
            return JsonResponse({
                "missing_keywords": job_analysis.get('key_keywords', [])[:10],
                "action_items": [
                    f"Add {job_analysis.get('job_title', 'target role')} terminology",
                    f"Include {len(job_analysis.get('technical_skills', []))} technical skills",
                    f"Integrate {len(job_analysis.get('priority_skills', []))} priority requirements"
                ]
            })
        else:
            return JsonResponse({
                "missing_keywords": ["Analysis pending"],
                "action_items": [
                    "Comprehensive job analysis in progress",
                    "Technical skills extraction pending",
                    "Keywords identification in progress"
                ]
            })
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return JsonResponse({"error": "Initial analysis failed"}, status=500)


# ─────────────────────  Manual Resume Entry Views  ─────────────────────

@login_required
def manual_resume_create(request):
    """Create a new manual resume with login protection - Task 14"""
    try:
        from .models import ManualResume
        
        if request.method == 'POST':
            form = ManualResumeForm(request.POST)
            if form.is_valid():
                resume = form.save(commit=False)
                resume.user = request.user
                resume.save()
                messages.success(request, 'Basic information saved! Now add your education and experience.')
                return redirect('manual_resume_edit', resume_id=resume.id)
            else:
                # Add form errors to messages
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field.title()}: {error}')
        else:
            form = ManualResumeForm()
            
    except ImportError:
        messages.warning(request, 'Manual resume models not yet migrated. Please run migrations first.')
        form = ManualResumeForm()
        
        if request.method == 'POST':
            if form.is_valid():
                messages.info(request, 'Form validation successful! Please run migrations to save data.')
                return redirect('dashboard')
    
    return render(request, 'resume/manual_entry/create.html', {
        'form': form,
    })


@login_required
def manual_resume_edit(request, resume_id):
    """Edit manual resume with login protection - Task 14"""
    try:
        from .models import ManualResume
        from .forms import (EducationFormSet, WorkExperienceFormSet, 
                           ProjectFormSet, SkillFormSet, CertificationFormSet, LanguageFormSet)
        
        resume = get_object_or_404(ManualResume, id=resume_id, user=request.user)
        
        if request.method == 'POST':
            form = ManualResumeForm(request.POST, instance=resume)
            education_formset = EducationFormSet(request.POST, instance=resume, prefix='education')
            work_formset = WorkExperienceFormSet(request.POST, instance=resume, prefix='work')
            project_formset = ProjectFormSet(request.POST, instance=resume, prefix='projects')
            skill_formset = SkillFormSet(request.POST, instance=resume, prefix='skills')
            cert_formset = CertificationFormSet(request.POST, instance=resume, prefix='certifications')
            lang_formset = LanguageFormSet(request.POST, instance=resume, prefix='languages')
            
            # Validate all forms
            forms_valid = True
            
            if not form.is_valid():
                forms_valid = False
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'Personal Info - {field.title()}: {error}')
            
            if not education_formset.is_valid():
                forms_valid = False
                for i, form_errors in enumerate(education_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Education #{i+1} - {field.title()}: {error}')
            
            if not work_formset.is_valid():
                forms_valid = False
                for i, form_errors in enumerate(work_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Work Experience #{i+1} - {field.title()}: {error}')
            
            if not project_formset.is_valid():
                forms_valid = False
                for i, form_errors in enumerate(project_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Project #{i+1} - {field.title()}: {error}')
            
            if not skill_formset.is_valid():
                forms_valid = False
                for i, form_errors in enumerate(skill_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Skill #{i+1} - {field.title()}: {error}')
            
            if not cert_formset.is_valid():
                forms_valid = False
                for i, form_errors in enumerate(cert_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Certification #{i+1} - {field.title()}: {error}')
            
            if not lang_formset.is_valid():
                forms_valid = False
                for i, form_errors in enumerate(lang_formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f'Language #{i+1} - {field.title()}: {error}')
            
            # Check formset non-form errors
            if education_formset.non_form_errors():
                forms_valid = False
                for error in education_formset.non_form_errors():
                    messages.error(request, f'Education: {error}')
            
            if work_formset.non_form_errors():
                forms_valid = False
                for error in work_formset.non_form_errors():
                    messages.error(request, f'Work Experience: {error}')
            
            if project_formset.non_form_errors():
                forms_valid = False
                for error in project_formset.non_form_errors():
                    messages.error(request, f'Projects: {error}')
            
            if skill_formset.non_form_errors():
                forms_valid = False
                for error in skill_formset.non_form_errors():
                    messages.error(request, f'Skills: {error}')
            
            if cert_formset.non_form_errors():
                forms_valid = False
                for error in cert_formset.non_form_errors():
                    messages.error(request, f'Certifications: {error}')
            
            if lang_formset.non_form_errors():
                forms_valid = False
                for error in lang_formset.non_form_errors():
                    messages.error(request, f'Languages: {error}')
            
            if forms_valid:
                with transaction.atomic():
                    try:
                        resume = form.save()
                        education_formset.save()
                        work_formset.save()
                        project_formset.save()
                        skill_formset.save()
                        cert_formset.save()
                        lang_formset.save()
                        
                        resume.is_complete = True
                        resume.save()
                        
                        messages.success(request, 'Resume saved successfully!')
                        return redirect('manual_resume_preview', resume_id=resume.id)
                    except Exception as e:
                        messages.error(request, f'Error saving resume: {str(e)}')
            else:
                messages.error(request, 'Please correct the errors above and try again.')
        else:
            form = ManualResumeForm(instance=resume)
            education_formset = EducationFormSet(instance=resume, prefix='education')
            work_formset = WorkExperienceFormSet(instance=resume, prefix='work')
            project_formset = ProjectFormSet(instance=resume, prefix='projects')
            skill_formset = SkillFormSet(instance=resume, prefix='skills')
            cert_formset = CertificationFormSet(instance=resume, prefix='certifications')
            lang_formset = LanguageFormSet(instance=resume, prefix='languages')
        
        return render(request, 'resume/manual_entry/full_form.html', {
            'form': form,
            'education_formset': education_formset,
            'work_formset': work_formset,
            'project_formset': project_formset,
            'skill_formset': skill_formset,
            'cert_formset': cert_formset,
            'lang_formset': lang_formset,
            'resume': resume,
        })
        
    except ImportError:
        messages.error(request, 'Manual resume models not available. Please run migrations first.')
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('dashboard')
        


@login_required
def manual_resume_preview(request, resume_id):
    """Preview the completed manual resume"""
    try:
        from .models import ManualResume
        resume = get_object_or_404(ManualResume, id=resume_id, user=request.user)
        
        return render(request, 'resume/manual_entry/preview.html', {
            'resume': resume,
        })
        
    except ImportError:
        messages.error(request, 'Manual resume models not available. Please run migrations first.')
        return redirect('dashboard')


@login_required
def manual_resume_list(request):
    """List all manual resumes for the current user"""
    try:
        from .models import ManualResume
        resumes = ManualResume.objects.filter(user=request.user)
        
        return render(request, 'resume/manual_entry/list.html', {
            'resumes': resumes,
        })
        
    except ImportError:
        messages.info(request, 'Manual resume functionality will be available after running migrations.')
        return render(request, 'resume/manual_entry/list.html', {
            'resumes': [],
        })


@login_required
def manual_resume_delete(request, resume_id):
    """Delete a manual resume"""
    try:
        from .models import ManualResume
        resume = get_object_or_404(ManualResume, id=resume_id, user=request.user)
        
        if request.method == 'POST':
            resume.delete()
            messages.success(request, 'Resume deleted successfully.')
            return redirect('manual_resume_list')
        
        return render(request, 'resume/manual_entry/confirm_delete.html', {
            'resume': resume,
        })
        
    except ImportError:
        messages.error(request, 'Manual resume models not available. Please run migrations first.')
        return redirect('dashboard')


@login_required
def convert_manual_to_tailored(request, resume_id):
    """Convert manual resume to the tailored resume format for template generation"""
    try:
        from .models import ManualResume
        resume = get_object_or_404(ManualResume, id=resume_id, user=request.user)
        
        if not resume.is_complete:
            messages.error(request, 'Please complete your resume before generating templates.')
            return redirect('manual_resume_edit', resume_id=resume_id)
        
        resume_text = generate_resume_text(resume)
        
        template_resume = Resume.objects.create(
            user=request.user,
            extracted_text=resume_text,
            file_size_bytes=len(resume_text.encode('utf-8'))
        )
        
        request.session['manual_resume_id'] = resume_id
        request.session['converted_resume_id'] = template_resume.id
        
        messages.success(request, 'Resume converted! Now you can select a template and generate your tailored resume.')
        return redirect('dashboard')
        
    except ImportError:
        messages.error(request, 'Manual resume models not available. Please run migrations first.')
        return redirect('dashboard')


def generate_resume_text(manual_resume):
    """Convert ManualResume object to text format for LLM processing"""
    text_parts = []
    
    # Personal Information
    text_parts.append(f"Name: {manual_resume.full_name}")
    text_parts.append(f"Title: {manual_resume.professional_title}")
    text_parts.append(f"Email: {manual_resume.email}")
    text_parts.append(f"Phone: {manual_resume.phone}")
    text_parts.append(f"Location: {manual_resume.city}, {manual_resume.state_province}, {manual_resume.country}")
    
    if manual_resume.linkedin_url:
        text_parts.append(f"LinkedIn: {manual_resume.linkedin_url}")
    if manual_resume.portfolio_url:
        text_parts.append(f"Portfolio: {manual_resume.portfolio_url}")
    
    text_parts.append(f"\nProfessional Summary:\n{manual_resume.professional_summary}")
    
    # Education
    if manual_resume.education_entries.exists():
        text_parts.append("\nEducation:")
        for edu in manual_resume.education_entries.all():
            end_date = edu.end_date.strftime("%B %Y") if edu.end_date else "Present"
            text_parts.append(
                f"• {edu.degree_name}, {edu.institution_name}, {edu.institution_city}, {edu.institution_country} "
                f"({edu.start_date.strftime('%B %Y')} - {end_date})"
            )
            if edu.gpa:
                text_parts.append(f"  GPA: {edu.gpa}")
            if edu.relevant_coursework:
                text_parts.append(f"  Relevant Coursework: {edu.relevant_coursework}")
    
    # Work Experience
    if manual_resume.work_experiences.exists():
        text_parts.append("\nWork Experience:")
        for work in manual_resume.work_experiences.all():
            end_date = work.end_date.strftime("%B %Y") if work.end_date else "Present"
            text_parts.append(
                f"• {work.job_title} at {work.company_name}, {work.company_city}, {work.company_country} "
                f"({work.start_date.strftime('%B %Y')} - {end_date})"
            )
            text_parts.append(f"  {work.responsibilities}")
    
    # Projects
    if manual_resume.projects.exists():
        text_parts.append("\nProjects:")
        for project in manual_resume.projects.all():
            end_date = project.end_date.strftime("%B %Y") if project.end_date else "Ongoing"
            text_parts.append(
                f"• {project.title} - {project.role} "
                f"({project.start_date.strftime('%B %Y')} - {end_date})"
            )
            text_parts.append(f"  {project.description}")
            if project.demo_url:
                text_parts.append(f"  Demo: {project.demo_url}")
    
    # Skills
    if manual_resume.skills.exists():
        text_parts.append("\nSkills:")
        skills_by_type = {}
        for skill in manual_resume.skills.all():
            if skill.skill_type not in skills_by_type:
                skills_by_type[skill.skill_type] = []
            skills_by_type[skill.skill_type].append(f"{skill.name} ({skill.proficiency})")
        
        for skill_type, skills in skills_by_type.items():
            text_parts.append(f"• {skill_type.title()}: {', '.join(skills)}")
    
    # Certifications
    if manual_resume.certifications.exists():
        text_parts.append("\nCertifications:")
        for cert in manual_resume.certifications.all():
            exp_date = f" (Expires: {cert.expiration_date.strftime('%B %Y')})" if cert.expiration_date else ""
            text_parts.append(
                f"• {cert.name}, {cert.issuing_organization} "
                f"({cert.date_obtained.strftime('%B %Y')}){exp_date}"
            )
    
    # Languages
    if manual_resume.languages.exists():
        text_parts.append("\nLanguages:")
        for lang in manual_resume.languages.all():
            text_parts.append(f"• {lang.name} ({lang.proficiency})")
    
    # Volunteer Experience
    if manual_resume.volunteer_experiences.exists():
        text_parts.append("\nVolunteer Experience:")
        for vol in manual_resume.volunteer_experiences.all():
            end_date = vol.end_date.strftime("%B %Y") if vol.end_date else "Present"
            text_parts.append(
                f"• {vol.role_title} at {vol.organization_name}, {vol.city}, {vol.country} "
                f"({vol.start_date.strftime('%B %Y')} - {end_date})"
            )
            text_parts.append(f"  {vol.responsibilities}")
    
    return "\n".join(text_parts)


# ─────────────────────  Fallback Resume Creation  ─────────────────────

def _create_fallback_resume(resume_text: str, template_html: str) -> str:
    """Simple fallback resume creation"""
    try:
        # Extract basic info using simple patterns
        lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
        
        # Find name (usually first non-empty line)
        name = lines[0] if lines else "Professional Candidate"
        
        # Find email and phone
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text)
        phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', resume_text)
        
        # Simple replacements
        replacements = {
            "{{NAME}}": name,
            "{{EMAIL}}": email_match.group() if email_match else "email@example.com",
            "{{PHONE}}": phone_match.group() if phone_match else "(555) 123-4567",
            "{{LOCATION}}": "Location",
            "{{SUMMARY}}": "Results-driven professional with proven expertise and strong analytical skills.",
            "{{WORK_EXPERIENCE}}": "<div class='job-entry'><h3>Professional Experience</h3><ul><li>Extensive background with relevant experience</li></ul></div>",
            "{{EDUCATION}}": "<p><strong>Relevant Education</strong></p>",
            "{{SKILLS}}": "Technical Skills, Problem Solving, Leadership, Communication, Project Management",
            "{{PROJECTS}}": "<div class='job-entry'><h3>Professional Projects</h3><ul><li>Relevant project experience</li></ul></div>"
        }
        
        # Apply replacements
        result = template_html
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        # Remove any remaining placeholders and conditionals
        result = re.sub(r'\{\{[^}]+\}\}', '', result)
        result = re.sub(r'\{\{#if_\w+\}\}', '', result)
        result = re.sub(r'\{\{/if_\w+\}\}', '', result)
        
        return result
        
    except Exception as e:
        logger.error(f"Fallback resume creation failed: {e}")
        return template_html


# ─────────────────────  Admin Views  ─────────────────────

User = get_user_model()

def is_admin_user(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@user_passes_test(is_admin_user, login_url='login')
def admin_dashboard(request):
    """Main admin dashboard with statistics and overview"""
    
    # Get statistics
    total_users = User.objects.count()
    total_resumes = Resume.objects.count()
    total_manual_resumes = 0
    try:
        total_manual_resumes = ManualResume.objects.count()
    except:
        pass
    
    total_downloads = DownloadLog.objects.count()
    
    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_users = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    recent_resumes = Resume.objects.filter(created_at__gte=thirty_days_ago).count()
    recent_downloads = DownloadLog.objects.filter(downloaded__gte=thirty_days_ago).count()
    
    # Weekly activity for charts
    weekly_stats = []
    for i in range(7):
        date = timezone.now() - timedelta(days=i)
        daily_users = User.objects.filter(date_joined__date=date.date()).count()
        daily_resumes = Resume.objects.filter(created_at__date=date.date()).count()
        daily_downloads = DownloadLog.objects.filter(downloaded__date=date.date()).count()
        
        weekly_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'users': daily_users,
            'resumes': daily_resumes,
            'downloads': daily_downloads,
        })
    
    # Top users by activity
    top_users = User.objects.annotate(
        resume_count=Count('resumes'),
        download_count=Count('downloads')
    ).order_by('-resume_count', '-download_count')[:10]
    
    # System settings
    current_settings = {
        'TARGET_ATS_SCORE': getattr(settings, 'TARGET_ATS_SCORE', 92),
        'TARGET_JOB_SCORE': getattr(settings, 'TARGET_JOB_SCORE', 92),
        'DOWNLOADS_PER_15_DAYS': getattr(settings, 'DOWNLOADS_PER_15_DAYS', 3),
        'DOWNLOADS_PER_MONTH': getattr(settings, 'DOWNLOADS_PER_MONTH', 6),
        'MAX_FILE_SIZE_MB': getattr(settings, 'MAX_FILE_SIZE_MB', 10),
    }
    
    context = {
        'total_users': total_users,
        'total_resumes': total_resumes,
        'total_manual_resumes': total_manual_resumes,
        'total_downloads': total_downloads,
        'recent_users': recent_users,
        'recent_resumes': recent_resumes,
        'recent_downloads': recent_downloads,
        'weekly_stats': json.dumps(weekly_stats),
        'top_users': top_users,
        'current_settings': current_settings,
    }
    
    return render(request, 'admin/dashboard.html', context)

@user_passes_test(is_admin_user, login_url='login')
def admin_users(request):
    """User management page"""
    
    # Search and filter
    search_query = request.GET.get('search', '')
    filter_type = request.GET.get('filter', 'all')
    
    users = User.objects.select_related('profile').annotate(
        resume_count=Count('resumes'),
        download_count=Count('downloads')
    )
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if filter_type == 'active':
        thirty_days_ago = timezone.now() - timedelta(days=30)
        users = users.filter(last_login__gte=thirty_days_ago)
    elif filter_type == 'inactive':
        thirty_days_ago = timezone.now() - timedelta(days=30)
        users = users.filter(Q(last_login__lt=thirty_days_ago) | Q(last_login__isnull=True))
    elif filter_type == 'staff':
        users = users.filter(is_staff=True)
    
    # Pagination
    paginator = Paginator(users.order_by('-date_joined'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'filter_type': filter_type,
        'total_users': users.count(),
    }
    
    return render(request, 'admin/users.html', context)

@user_passes_test(is_admin_user, login_url='login')
def admin_user_detail(request, user_id):
    """User detail and edit page"""
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_limits':
            # Update user download limits (store in session or user profile)
            downloads_15_days = int(request.POST.get('downloads_15_days', 3))
            downloads_month = int(request.POST.get('downloads_month', 6))
            
            # Store in user profile or session
            if hasattr(user, 'profile'):
                profile = user.profile
            else:
                profile, created = Profile.objects.get_or_create(user=user)
            
            # Add custom fields to profile if needed
            request.session[f'user_{user.id}_download_limits'] = {
                'per_15_days': downloads_15_days,
                'per_month': downloads_month
            }
            
            messages.success(request, f'Download limits updated for {user.username}')
            
        elif action == 'toggle_staff':
            user.is_staff = not user.is_staff
            user.save()
            status = 'granted' if user.is_staff else 'removed'
            messages.success(request, f'Staff access {status} for {user.username}')
            
        elif action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'Account {status} for {user.username}')
            
        elif action == 'delete_user':
            if user != request.user:  # Don't allow self-deletion
                username = user.username
                user.delete()
                messages.success(request, f'User {username} deleted successfully')
                return redirect('admin_users')
            else:
                messages.error(request, 'Cannot delete your own account')
    
    # Get user statistics
    user_resumes = Resume.objects.filter(user=user)
    user_downloads = DownloadLog.objects.filter(user=user)
    
    try:
        user_manual_resumes = ManualResume.objects.filter(user=user)
    except:
        user_manual_resumes = []
    
    # Get current download limits
    custom_limits = request.session.get(f'user_{user.id}_download_limits', {
        'per_15_days': 3,
        'per_month': 6
    })
    
    context = {
        'user_obj': user,  # Renamed to avoid conflict with request.user
        'user_resumes': user_resumes,
        'user_downloads': user_downloads.order_by('-downloaded')[:10],
        'user_manual_resumes': user_manual_resumes,
        'total_resumes': user_resumes.count(),
        'total_downloads': user_downloads.count(),
        'total_manual_resumes': len(user_manual_resumes),
        'custom_limits': custom_limits,
    }
    
    return render(request, 'admin/user_detail.html', context)

@user_passes_test(is_admin_user, login_url='login')
def admin_settings(request):
    """System settings management"""
    
    if request.method == 'POST':
        # Update environment-based settings
        new_settings = {
            'TARGET_ATS_SCORE': int(request.POST.get('target_ats_score', 92)),
            'TARGET_JOB_SCORE': int(request.POST.get('target_job_score', 92)),
            'DOWNLOADS_PER_15_DAYS': int(request.POST.get('downloads_15_days', 3)),
            'DOWNLOADS_PER_MONTH': int(request.POST.get('downloads_month', 6)),
            'MAX_FILE_SIZE_MB': int(request.POST.get('max_file_size', 10)),
            'LLM_MAX_TOKENS': int(request.POST.get('llm_max_tokens', 4096)),
            'LLM_TEMPERATURE': float(request.POST.get('llm_temperature', 0.2)),
            'LLM_MAX_ITERATIONS': int(request.POST.get('llm_max_iterations', 3)),
        }
        
        # Store settings in session for runtime use
        request.session['admin_settings'] = new_settings
        
        # Update env file
        update_env_file(new_settings)
        
        messages.success(request, 'Settings updated successfully! Restart the application for all changes to take effect.')
    
    # Get current settings
    current_settings = {
        'TARGET_ATS_SCORE': getattr(settings, 'TARGET_ATS_SCORE', 92),
        'TARGET_JOB_SCORE': getattr(settings, 'TARGET_JOB_SCORE', 92),
        'DOWNLOADS_PER_15_DAYS': getattr(settings, 'DOWNLOADS_PER_15_DAYS', 3),
        'DOWNLOADS_PER_MONTH': getattr(settings, 'DOWNLOADS_PER_MONTH', 6),
        'MAX_FILE_SIZE_MB': getattr(settings, 'MAX_FILE_SIZE_MB', 10),
        'LLM_MAX_TOKENS': getattr(settings, 'LLM_MAX_TOKENS', 4096),
        'LLM_TEMPERATURE': getattr(settings, 'LLM_TEMPERATURE', 0.2),
        'LLM_MAX_ITERATIONS': getattr(settings, 'LLM_MAX_ITERATIONS', 3),
    }
    
    # Override with session settings if available
    session_settings = request.session.get('admin_settings', {})
    current_settings.update(session_settings)
    
    context = {
        'settings': current_settings,
    }
    
    return render(request, 'admin/settings.html', context)

@user_passes_test(is_admin_user, login_url='login')
def admin_create_user(request):
    """Create new user account"""
    
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Set additional permissions if specified
            if request.POST.get('is_staff'):
                user.is_staff = True
                user.save()
            
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('admin_user_detail', user_id=user.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.title()}: {error}')
    else:
        form = CustomSignupForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'admin/create_user.html', context)

@user_passes_test(is_admin_user, login_url='login')
def admin_analytics(request):
    """Analytics and reports page"""
    
    # Date range filter
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # User registration trends
    registration_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        daily_registrations = User.objects.filter(date_joined__date=date.date()).count()
        registration_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': daily_registrations
        })
    
    # Resume creation trends
    resume_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        daily_resumes = Resume.objects.filter(created_at__date=date.date()).count()
        resume_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': daily_resumes
        })
    
    # Download trends
    download_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        daily_downloads = DownloadLog.objects.filter(downloaded__date=date.date()).count()
        download_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': daily_downloads
        })
    
    # Top performing users
    top_users = User.objects.annotate(
        total_resumes=Count('resumes'),
        total_downloads=Count('downloads')
    ).order_by('-total_resumes', '-total_downloads')[:20]
    
    # Geographic distribution (if available)
    try:
        country_stats = Profile.objects.values('country').annotate(
            count=Count('user')
        ).order_by('-count')[:10]
    except:
        country_stats = []
    
    context = {
        'days': days,
        'registration_data': json.dumps(registration_data),
        'resume_data': json.dumps(resume_data),
        'download_data': json.dumps(download_data),
        'top_users': top_users,
        'country_stats': country_stats,
    }
    
    return render(request, 'admin/analytics.html', context)

@user_passes_test(is_admin_user, login_url='login')
def admin_system_logs(request):
    """System logs and monitoring"""
    
    # Read log files if available
    log_entries = []
    log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'django.log')
    
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                # Get last 100 lines
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                for line in reversed(recent_lines):
                    if line.strip():
                        log_entries.append(line.strip())
    except Exception as e:
        log_entries.append(f"Error reading log file: {str(e)}")
    
    # System status
    system_status = {
        'total_users': User.objects.count(),
        'active_users_today': User.objects.filter(last_login__date=timezone.now().date()).count(),
        'total_resumes': Resume.objects.count(),
        'resumes_today': Resume.objects.filter(created_at__date=timezone.now().date()).count(),
        'total_downloads': DownloadLog.objects.count(),
        'downloads_today': DownloadLog.objects.filter(downloaded__date=timezone.now().date()).count(),
    }
    
    context = {
        'log_entries': log_entries[:50],  # Show last 50 entries
        'system_status': system_status,
    }
    
    return render(request, 'admin/system_logs.html', context)

def update_env_file(new_settings):
    """Update .env file with new settings"""
    try:
        env_path = os.path.join(settings.BASE_DIR, '.env')
        
        # Read current .env file
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        # Update settings
        settings_map = {
            'TARGET_ATS_SCORE': 'TARGET_ATS_SCORE',
            'TARGET_JOB_SCORE': 'TARGET_JOB_SCORE',
            'DOWNLOADS_PER_15_DAYS': 'DOWNLOADS_PER_15_DAYS',
            'DOWNLOADS_PER_MONTH': 'DOWNLOADS_PER_MONTH',
            'MAX_FILE_SIZE_MB': 'MAX_FILE_SIZE_MB',
            'LLM_MAX_TOKENS': 'LLM_MAX_TOKENS',
            'LLM_TEMPERATURE': 'LLM_TEMPERATURE',
            'LLM_MAX_ITERATIONS': 'LLM_MAX_ITERATIONS',
        }
        
        # Update existing lines or add new ones
        updated_lines = []
        updated_keys = set()
        
        for line in env_lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0]
                if key in settings_map.values():
                    # Find the corresponding new setting
                    for new_key, env_key in settings_map.items():
                        if env_key == key:
                            updated_lines.append(f"{key}={new_settings[new_key]}\n")
                            updated_keys.add(key)
                            break
                else:
                    updated_lines.append(line + '\n')
            else:
                updated_lines.append(line + '\n')
        
        # Add any new settings that weren't in the file
        for new_key, env_key in settings_map.items():
            if env_key not in updated_keys:
                updated_lines.append(f"{env_key}={new_settings[new_key]}\n")
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
            
    except Exception as e:
        print(f"Error updating .env file: {str(e)}")

# AJAX endpoints for real-time updates
@user_passes_test(is_admin_user, login_url='login')
def admin_api_stats(request):
    """API endpoint for real-time statistics"""
    
    stats = {
        'total_users': User.objects.count(),
        'total_resumes': Resume.objects.count(),
        'total_downloads': DownloadLog.objects.count(),
        'users_today': User.objects.filter(date_joined__date=timezone.now().date()).count(),
        'resumes_today': Resume.objects.filter(created_at__date=timezone.now().date()).count(),
        'downloads_today': DownloadLog.objects.filter(downloaded__date=timezone.now().date()).count(),
    }
    
    return JsonResponse(stats)

@user_passes_test(is_admin_user, login_url='login')
def admin_api_user_action(request, user_id):
    """API endpoint for user actions"""
    
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        action = request.POST.get('action')
        
        try:
            if action == 'toggle_active':
                user.is_active = not user.is_active
                user.save()
                return JsonResponse({
                    'success': True,
                    'message': f'User {"activated" if user.is_active else "deactivated"}',
                    'is_active': user.is_active
                })
            
            elif action == 'toggle_staff':
                user.is_staff = not user.is_staff
                user.save()
                return JsonResponse({
                    'success': True,
                    'message': f'Staff access {"granted" if user.is_staff else "removed"}',
                    'is_staff': user.is_staff
                })
            
            elif action == 'reset_downloads':
                DownloadLog.objects.filter(user=user).delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Download history reset for user'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})