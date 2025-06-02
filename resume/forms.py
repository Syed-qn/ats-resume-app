# resume/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django_countries.fields import CountryField
import phonenumbers
from django.forms import modelformset_factory, inlineformset_factory
from .models import (
    ManualResume, Education, WorkExperience, Project, 
    Skill, Certification, Award, Language, VolunteerExperience
)

from .models import Resume, Profile

User = get_user_model()

# Build a dropdown of all country dialing codes with a sample region label
COUNTRY_CODE_CHOICES = []
for code, regions in phonenumbers.COUNTRY_CODE_TO_REGION_CODE.items():
    if not regions:
        continue
    # Use the first region code for display (e.g. "US (+1)")
    label = f"{regions[0]} (+{code})"
    COUNTRY_CODE_CHOICES.append((str(code), label))
COUNTRY_CODE_CHOICES.sort(key=lambda x: int(x[0]))


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ["file"]

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10 MB.")
            ext = "." + file.name.split(".")[-1].lower()
            if ext not in [".pdf", ".doc", ".docx"]:
                raise forms.ValidationError("Only PDF, DOC, and DOCX files are allowed.")
        return file


class JobDescriptionForm(forms.Form):
    job_description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "placeholder": "Paste the complete job description here…",
                "rows": 10,
                "class": "form-control",
            }
        ),
        label="Job Description",
        min_length=50,
        help_text="Include requirements, responsibilities, must-have skills…",
    )


class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        error_messages={
            'required': 'Email address is required.',
            'invalid': 'Please enter a valid email address.'
        }
    )
    
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        label="Country code",
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Please select your country code.',
            'invalid_choice': 'Please select a valid country code.'
        }
    )
    
    phone_number = forms.CharField(
        max_length=20,
        label="Phone number",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. 5551234567",
            'class': 'form-control'
        }),
        error_messages={
            'required': 'Phone number is required.',
            'max_length': 'Phone number is too long.'
        }
    )
    
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "Your city",
            'class': 'form-control'
        }),
        error_messages={
            'required': 'City is required.',
            'max_length': 'City name is too long.'
        }
    )
    
    country = CountryField().formfield(
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        error_messages={
            'required': 'Please select your country.',
            'invalid_choice': 'Please select a valid country.'
        }
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "country_code",
            "phone_number",
            "city",
            "country",
            "password1",
            "password2",
        )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and improve widgets
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
        
        # Update error messages
        self.fields['username'].error_messages.update({
            'required': 'Username is required.',
            'unique': 'This username is already taken.',
            'invalid': 'Username contains invalid characters.'
        })
        
        self.fields['password1'].error_messages.update({
            'required': 'Password is required.',
        })
        
        self.fields['password2'].error_messages.update({
            'required': 'Please confirm your password.',
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters long.')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and len(phone) < 7:
            raise forms.ValidationError('Please enter a valid phone number.')
        return phone

    def save(self, commit=True):
        # Create User then Profile
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.country_code = self.cleaned_data["country_code"]
            profile.phone_number = self.cleaned_data["phone_number"]
            profile.city = self.cleaned_data["city"]
            profile.country = self.cleaned_data["country"]
            profile.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """
    Enhanced authentication form with better error handling and styling
    """
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            "autofocus": True, 
            "class": "form-control",
            "placeholder": "Enter your username"
        }),
        error_messages={
            'required': 'Username is required.',
        }
    )
    
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your password"
        }),
        error_messages={
            'required': 'Password is required.',
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Invalid username or password. Please try again.",
                    code='invalid_login',
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ManualResumeForm(forms.ModelForm):
    """Main form for personal information and professional summary"""
    
    class Meta:
        model = ManualResume
        fields = [
            'full_name', 'professional_title', 'email', 'phone',
            'city', 'state_province', 'country', 'linkedin_url', 
            'portfolio_url', 'professional_summary'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., John Smith',
                'required': True
            }),
            'professional_title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Data Scientist, Software Engineer',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 (555) 123-4567',
                'required': True
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'New York',
                'required': True
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'NY (optional)'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'United States',
                'required': True
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/yourprofile (optional)'
            }),
            'portfolio_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/yourusername (optional)'
            }),
            'professional_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write 2-3 sentences summarizing your career goals, core strengths, and key achievements...',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add error messages for all fields
        for field_name, field in self.fields.items():
            field.error_messages.update({
                'required': f'{field.label} is required.',
                'invalid': f'Please enter a valid {field.label.lower()}.',
            })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Basic email validation
            import re
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                raise forms.ValidationError('Please enter a valid email address.')
        return email

    def clean_professional_summary(self):
        summary = self.cleaned_data.get('professional_summary')
        if summary and len(summary.split()) < 10:
            raise forms.ValidationError('Professional summary should be at least 10 words.')
        return summary


class EducationForm(forms.ModelForm):
    """Form for education entries"""
    
    class Meta:
        model = Education
        fields = [
            'degree_name', 'institution_name', 'institution_city', 
            'institution_country', 'start_date', 'end_date', 
            'is_current', 'gpa', 'relevant_coursework'
        ]
        widgets = {
            'degree_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Bachelor of Science in Computer Science',
                'required': True
            }),
            'institution_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., University of Dubai',
                'required': True
            }),
            'institution_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dubai',
                'required': True
            }),
            'institution_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UAE',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'placeholder': 'YYYY-MM',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'placeholder': 'YYYY-MM'
            }),
            'is_current': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'gpa': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '4.0',
                'placeholder': '3.75 (optional)'
            }),
            'relevant_coursework': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List relevant courses, honors, or achievements (optional)'
            }),
        }


class WorkExperienceForm(forms.ModelForm):
    """Form for work experience entries"""
    
    class Meta:
        model = WorkExperience
        fields = [
            'job_title', 'company_name', 'company_city', 'company_country',
            'start_date', 'end_date', 'is_current', 'responsibilities'
        ]
        widgets = {
            'job_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., AI & Data Scientist',
                'required': True
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Younoh Media',
                'required': True
            }),
            'company_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dubai',
                'required': True
            }),
            'company_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UAE',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month'
            }),
            'is_current': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'responsibilities': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': '• Improved campaign CTR by 25% using predictive modeling\n• Developed machine learning pipelines using Python and TensorFlow\n• Led cross-functional team of 5 engineers\n• Managed $2M annual budget for data infrastructure\n• Published 3 research papers in top-tier conferences',
                'required': True
            }),
        }


class ProjectForm(forms.ModelForm):
    """Form for project entries"""
    
    class Meta:
        model = Project
        fields = [
            'title', 'role', 'start_date', 'end_date', 
            'is_ongoing', 'description', 'demo_url'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Customer Churn Prediction System',
                'required': True
            }),
            'role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Team Lead, Contributor, Solo Developer',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month'
            }),
            'is_ongoing': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the project objectives, technologies/frameworks used, and outcome or impact. Include metrics when possible.',
                'required': True
            }),
            'demo_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/username/project (optional)'
            }),
        }


class SkillForm(forms.ModelForm):
    """Form for individual skills"""
    
    class Meta:
        model = Skill
        fields = ['skill_type', 'name', 'proficiency']
        widgets = {
            'skill_type': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python, Leadership, Docker',
                'required': True
            }),
            'proficiency': forms.Select(attrs={'class': 'form-control', 'required': True}),
        }


class CertificationForm(forms.ModelForm):
    """Form for certifications"""
    
    class Meta:
        model = Certification
        fields = ['name', 'issuing_organization', 'date_obtained', 'expiration_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Google Cloud Professional Data Engineer',
                'required': True
            }),
            'issuing_organization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Google Cloud',
                'required': True
            }),
            'date_obtained': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'required': True
            }),
            'expiration_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'placeholder': 'Leave blank if no expiration'
            }),
        }


class LanguageForm(forms.ModelForm):
    """Form for languages"""
    
    class Meta:
        model = Language
        fields = ['name', 'proficiency']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., English, Arabic, Spanish',
                'required': True
            }),
            'proficiency': forms.Select(attrs={'class': 'form-control', 'required': True}),
        }


# Create formsets for repeatable sections with improved validation
EducationFormSet = inlineformset_factory(
    ManualResume, Education, form=EducationForm, 
    extra=1, can_delete=True, min_num=1, validate_min=True
)

WorkExperienceFormSet = inlineformset_factory(
    ManualResume, WorkExperience, form=WorkExperienceForm,
    extra=0, can_delete=True, min_num=0, validate_min=False
)

ProjectFormSet = inlineformset_factory(
    ManualResume, Project, form=ProjectForm,
    extra=0, can_delete=True, min_num=0, validate_min=False
)

SkillFormSet = inlineformset_factory(
    ManualResume, Skill, form=SkillForm,
    extra=3, can_delete=True, min_num=1, validate_min=True
)

CertificationFormSet = inlineformset_factory(
    ManualResume, Certification, form=CertificationForm,
    extra=0, can_delete=True, min_num=0, validate_min=False
)

LanguageFormSet = inlineformset_factory(
    ManualResume, Language, form=LanguageForm,
    extra=0, can_delete=True, min_num=0, validate_min=False
)