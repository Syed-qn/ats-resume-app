# resume/admin.py  – drop-in replacement
from django.contrib import admin
from django.db import models          # NEW
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import path
from django import forms
from .models import Profile

from .models import (
    Resume, Template, ManualResume, Education, WorkExperience,
    Project, Skill, Certification, Award, Language, VolunteerExperience
)

# ─────────────────────────  Limit changer  ─────────────────────────
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "limit_15_days", "limit_month", "country", "city")
    list_editable = ("limit_15_days", "limit_month")
    search_fields = ("user__username", "user__email")

# ─────────────────────────  Core models  ─────────────────────────

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'file', 'created_at')
    list_filter  = ('created_at', 'user')
    search_fields = ('user__username', 'file')
    readonly_fields = ('created_at', 'extracted_text')


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name')
    search_fields = ('name',)


# ────────────────────────  LLM provider switch  ────────────────────────

class LLMSettings(models.Model):
    """Unmanaged stub so Django admin is happy (no DB table)."""
    class Meta:
        managed = False
        verbose_name = "LLM Settings"
        verbose_name_plural = "LLM Settings"


class LLMSettingsForm(forms.Form):
    llm_provider = forms.ChoiceField(
        choices=[("gpt", "OpenAI GPT"), ("deepseek", "DeepSeek")],
        initial=getattr(settings, "LLM_PROVIDER", "gpt"),
        widget=forms.RadioSelect,
        label="Active LLM engine",
    )


@admin.register(LLMSettings)                   # ← FIXED
class LLMSettingsAdmin(admin.ModelAdmin):
    change_form_template = "admin/llm_switch.html"

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "switch/",
                self.admin_site.admin_view(self.switch_llm),
                name="llm-switch",
            ),
        ]
        return extra + urls

    def switch_llm(self, request):
        form = LLMSettingsForm(request.POST)
        if form.is_valid():
            provider = form.cleaned_data["llm_provider"]
            # Persist however you like; here we patch at runtime
            settings.LLM_PROVIDER = provider
            self.message_user(request, f"LLM switched to {provider.upper()}")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


# ────────────────────────  Inline & related admins  ────────────────────────

class EducationInline(admin.TabularInline):
    model   = Education
    extra   = 1
    fields  = ('degree_name', 'institution_name', 'start_date',
               'end_date', 'is_current', 'order')
    ordering = ('order', '-start_date')


class WorkExperienceInline(admin.TabularInline):
    model   = WorkExperience
    extra   = 1
    fields  = ('job_title', 'company_name', 'start_date',
               'end_date', 'is_current', 'order')
    ordering = ('order', '-start_date')


class ProjectInline(admin.TabularInline):
    model   = Project
    extra   = 1
    fields  = ('title', 'role', 'start_date',
               'end_date', 'is_ongoing', 'order')
    ordering = ('order', '-start_date')


class SkillInline(admin.TabularInline):
    model   = Skill
    extra   = 3
    fields  = ('skill_type', 'name', 'proficiency', 'order')
    ordering = ('skill_type', 'order')


class CertificationInline(admin.TabularInline):
    model   = Certification
    extra   = 1
    fields  = ('name', 'issuing_organization', 'date_obtained',
               'expiration_date', 'order')
    ordering = ('order', '-date_obtained')


class LanguageInline(admin.TabularInline):
    model   = Language
    extra   = 1
    fields  = ('name', 'proficiency', 'order')
    ordering = ('order',)


@admin.register(ManualResume)
class ManualResumeAdmin(admin.ModelAdmin):
    list_display  = ('id', 'full_name', 'user', 'professional_title',
                     'is_complete', 'updated_at')
    list_filter   = ('is_complete', 'created_at', 'updated_at')
    search_fields = ('full_name', 'user__username',
                     'professional_title', 'email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'is_complete', 'created_at', 'updated_at')
        }),
        ('Personal Information', {
            'fields': (
                'full_name', 'professional_title', 'email', 'phone',
                'city', 'state_province', 'country',
                'linkedin_url', 'portfolio_url'
            )
        }),
        ('Professional Summary', {'fields': ('professional_summary',)}),
    )

    inlines = [
        EducationInline, WorkExperienceInline, ProjectInline,
        SkillInline, CertificationInline, LanguageInline,
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# ────────────────────────  Direct model admins  ────────────────────────

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display  = ('degree_name', 'institution_name', 'resume',
                     'start_date', 'end_date')
    list_filter   = ('institution_country', 'start_date', 'is_current')
    search_fields = ('degree_name', 'institution_name', 'resume__full_name')


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display  = ('job_title', 'company_name', 'resume',
                     'start_date', 'end_date')
    list_filter   = ('company_country', 'start_date', 'is_current')
    search_fields = ('job_title', 'company_name', 'resume__full_name')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display  = ('title', 'role', 'resume', 'start_date', 'end_date')
    list_filter   = ('start_date', 'is_ongoing')
    search_fields = ('title', 'role', 'resume__full_name')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display  = ('name', 'skill_type', 'proficiency', 'resume')
    list_filter   = ('skill_type', 'proficiency')
    search_fields = ('name', 'resume__full_name')


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display  = ('name', 'issuing_organization', 'resume',
                     'date_obtained', 'expiration_date')
    list_filter   = ('issuing_organization', 'date_obtained')
    search_fields = ('name', 'issuing_organization', 'resume__full_name')


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display  = ('name', 'proficiency', 'resume')
    list_filter   = ('proficiency',)
    search_fields = ('name', 'resume__full_name')
