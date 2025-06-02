# ats_resume_app/urls.py - Main project URLs configuration
# Updated for Tasks 10-14

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import HttpResponse

def health_check(request):
    """Simple health check endpoint"""
    return HttpResponse("OK - All systems operational!", content_type="text/plain")

def robots_txt(request):
    """Robots.txt for SEO"""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /admin-panel/",
        "Allow: /",
        "Allow: /ats-details/",
        "Allow: /our-services/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

urlpatterns = [
    # ====== ADMIN INTERFACE ======
    path('admin/', admin.site.urls),
    
    # ====== MAIN APPLICATION ROUTES ======
    path('', include('resume.urls')),
    
    # ====== HEALTH CHECK & MONITORING ======
    path('health/', health_check, name='health_check'),
    path('robots.txt', robots_txt, name='robots_txt'),
    
    # ====== FAVICON HANDLING ======
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
]