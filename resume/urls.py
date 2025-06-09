# resume/urls.py - Updated with Tasks 11, 13, 14

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ─────────────── Landing & Public Pages ───────────────
    path('', views.landing, name='landing'),
    
    # Task 13: New navigation pages
    path('ats-details/', views.ats_details, name='ats_details'),
    path('our-services/', views.our_services, name='our_services'),
    
    # ─────────────── Authentication URLs ───────────────
    # Task 11: Custom password reset views
    path('password-reset/', 
         views.CustomPasswordResetView.as_view(), 
         name='password_reset'),
    path('password-reset/done/', 
         views.CustomPasswordResetDoneView.as_view(), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('reset/done/', 
         views.CustomPasswordResetCompleteView.as_view(), 
         name='password_reset_complete'),
    
    # Task 11: Custom login view with admin redirect
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path("logout/", views.HardLogoutView.as_view(), name="logout"),
    path('signup/', views.signup, name='signup'),
    
    # ─────────────── Protected Application URLs - Task 14 ───────────────
    # Task 14: All these require login
    path('app/', views.dashboard, name='dashboard'),  # Protected SPA entry
    
    # API endpoints - all protected
    path('api/upload/', views.upload_resume_ajax, name='upload_resume'),
    path('api/generate/<int:resume_id>/<int:template_id>/', views.generate_tailored_resume_ajax, name='generate_resume'),
    path('api/progress/<str:task_id>/', views.check_progress, name='check_progress'),
    path('api/download/<int:resume_id>/', views.download_pdf_ajax, name='download_pdf'),
    path('api/resumes/', views.ResumeAPIView.as_view(), name='resume_list'),
    path('api/resumes/<int:resume_id>/', views.ResumeAPIView.as_view(), name='resume_detail'),
    path('templates/', views.get_templates_ajax, name='get_templates'),
    path('api/analyze/', views.analyze_resume_ajax, name='analyze_resume'),
    
    # Manual resume entry - all protected
    path('manual-resume/create/', views.manual_resume_create, name='manual_resume_create'),
    path('manual-resume/edit/<int:resume_id>/', views.manual_resume_edit, name='manual_resume_edit'),
    path('manual-resume/preview/<int:resume_id>/', views.manual_resume_preview, name='manual_resume_preview'),
    path('manual-resume/list/', views.manual_resume_list, name='manual_resume_list'),
    path('manual-resume/delete/<int:resume_id>/', views.manual_resume_delete, name='manual_resume_delete'),
    path('manual-resume/convert/<int:resume_id>/', views.convert_manual_to_tailored, name='convert_manual_to_tailored'),
    
    # ─────────────── Admin Panel URLs ───────────────
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin-panel/settings/', views.admin_settings, name='admin_settings'),
    path('admin-panel/create-user/', views.admin_create_user, name='admin_create_user'),
    path('admin-panel/analytics/', views.admin_analytics, name='admin_analytics'),
    path('admin-panel/logs/', views.admin_system_logs, name='admin_system_logs'),
    
    # Admin API endpoints
    path('admin-panel/api/stats/', views.admin_api_stats, name='admin_api_stats'),
    path('admin-panel/api/user/<int:user_id>/action/', views.admin_api_user_action, name='admin_api_user_action'),
]