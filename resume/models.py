from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, URLValidator

User = get_user_model()

class Resume(models.Model):
    """
    Stores an uploaded résumé.  'user' can be NULL for old legacy rows,
    but new entries created via the app always set it.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,          # <-- keep nullable to pass migration
        blank=True,
        related_name="resumes",
    )
    file = models.FileField(upload_to="resumes/")
    extracted_text = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    file_size_bytes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.user.username if self.user else "Orphan"
        return f"{who}'s résumé #{self.id}"

    # human-readable size
    @property
    def file_size(self):
        size = self.file_size_bytes or (self.file.size if self.file else 0)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


class Template(models.Model):
    name        = models.CharField(max_length=255, unique=True)
    content     = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DownloadLog(models.Model):
    """Each PDF download → one entry, so we can enforce quotas."""
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="downloads",
    )
    downloaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes  = [models.Index(fields=["user", "downloaded"])]
        ordering = ["-downloaded"]

    def __str__(self):
        return f"{self.user.username} @ {timezone.localtime(self.downloaded):%Y-%m-%d %H:%M}"

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name="profile")
    country_code = models.CharField(max_length=5, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Profile({self.user.username})"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, **kwargs):
    """
    Ensure every User has a matching Profile.
    We **never** touch instance.profile directly, because that attribute
    triggers a query and raises RelatedObjectDoesNotExist when no row exists.
    """
    # get_or_create returns (object, created_boolean)
    Profile.objects.get_or_create(user=instance)

# ADD THESE TO YOUR EXISTING resume/models.py file

class ManualResume(models.Model):
    """Manual resume entry with structured data"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="manual_resumes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=False)
    
    # Personal Information
    full_name = models.CharField(max_length=100)
    professional_title = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    linkedin_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    
    # Professional Summary
    professional_summary = models.TextField(
        help_text="2-3 sentences summarizing your career goals and key strengths"
    )
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.full_name}'s Manual Resume"

class Education(models.Model):
    """Education entries for manual resume"""
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='education_entries')
    degree_name = models.CharField(max_length=200)
    institution_name = models.CharField(max_length=200)
    institution_city = models.CharField(max_length=100)
    institution_country = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # null means "Present"
    is_current = models.BooleanField(default=False)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    relevant_coursework = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-start_date']

class WorkExperience(models.Model):
    """Work experience entries for manual resume"""
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='work_experiences')
    job_title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    company_city = models.CharField(max_length=100)
    company_country = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    responsibilities = models.TextField(
        help_text="Enter 3-5 bullet points describing key accomplishments, technologies used, and metrics"
    )
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-start_date']

class Project(models.Model):
    """Project entries for manual resume"""
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    role = models.CharField(max_length=100, help_text="e.g., Team Lead, Contributor")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_ongoing = models.BooleanField(default=False)
    description = models.TextField(
        help_text="2-4 sentences detailing objectives, technologies/frameworks used, and outcome"
    )
    demo_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-start_date']

class Skill(models.Model):
    """Skills for manual resume"""
    SKILL_TYPES = [
        ('technical', 'Technical Skills'),
        ('soft', 'Soft Skills'),
        ('tools', 'Tools & Platforms'),
    ]
    
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='skills')
    skill_type = models.CharField(max_length=20, choices=SKILL_TYPES)
    name = models.CharField(max_length=100)
    proficiency = models.CharField(
        max_length=20, 
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ],
        default='intermediate'
    )
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['skill_type', 'order', 'name']
        unique_together = ['resume', 'name']

class Certification(models.Model):
    """Certifications for manual resume"""
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    date_obtained = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-date_obtained']

class Award(models.Model):
    """Awards and honors for manual resume"""
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='awards')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    date_received = models.DateField()
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-date_received']

class Language(models.Model):
    """Language proficiencies for manual resume"""
    PROFICIENCY_LEVELS = [
        ('native', 'Native'),
        ('fluent', 'Fluent'),
        ('professional', 'Professional'),
        ('intermediate', 'Intermediate'),
        ('beginner', 'Beginner'),
    ]
    
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='languages')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']

class VolunteerExperience(models.Model):
    """Volunteer experience for manual resume"""
    resume = models.ForeignKey(ManualResume, on_delete=models.CASCADE, related_name='volunteer_experiences')
    role_title = models.CharField(max_length=200)
    organization_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    responsibilities = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-start_date']