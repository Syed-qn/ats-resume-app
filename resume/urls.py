# resume/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Main SPA page
    path('', views.home, name='home'),
    path('templates/', views.get_templates_ajax, name='templates'),
    
    # AJAX API endpoints
    path('api/upload/', views.upload_resume_ajax, name='upload_resume_ajax'),
    path('api/generate/<int:resume_id>/<int:template_id>/', views.generate_tailored_resume_ajax, name='generate_tailored_resume_ajax'),
    path('api/download/<int:resume_id>/', views.download_pdf_ajax, name='download_pdf_ajax'),
    path('api/templates/', views.get_templates_ajax, name='get_templates_ajax'),
    
    # RESTful API for resume management
    path('api/resumes/', views.ResumeAPIView.as_view(), name='resume_list_api'),
    path('api/resumes/<int:resume_id>/', views.ResumeAPIView.as_view(), name='resume_detail_api'),
    
    # Legacy endpoints (keep for backward compatibility)
    path('upload/', views.upload_resume_ajax, name='upload_resume'),
    path('select/<int:resume_id>/', views.home, name='select_resume'),
    path('job-description/<int:resume_id>/', views.home, name='enter_job_description'),
    path('choose-template/<int:resume_id>/', views.home, name='choose_template'),
    path('generate/<int:resume_id>/<int:template_id>/', views.generate_tailored_resume_ajax, name='generate_tailored_resume'),
    path('download/<int:resume_id>/', views.download_pdf_ajax, name='download_pdf'),
    path('api/analyze/', views.analyze_resume_ajax, name='analyze_resume_ajax'),
]
