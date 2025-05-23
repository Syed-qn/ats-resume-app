from django import forms
from .models import Resume

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file']
        
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10MB.")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            file_extension = '.' + file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError("Only PDF, DOC, and DOCX files are allowed.")
        
        return file

class JobDescriptionForm(forms.Form):
    job_description = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Paste the complete job description here...',
            'rows': 10,
            'class': 'form-control'
        }), 
        label='Job Description',
        min_length=50,
        help_text='Please paste the complete job description including requirements and responsibilities.'
    )
