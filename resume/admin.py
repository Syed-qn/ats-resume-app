from django.contrib import admin
from .models import Resume, Template

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'file', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'file')
    readonly_fields = ('created_at', 'extracted_text')

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
