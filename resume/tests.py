from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import json
import os
from .models import Resume
from .utils import extract_text_from_file, validate_file

class ResumeModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_resume_creation(self):
        resume = Resume.objects.create(
            user=self.user,
            extracted_text="Test resume content"
        )
        self.assertEqual(str(resume), "testuser's resume #1")
        self.assertEqual(resume.extracted_text, "Test resume content")

class ResumeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ATS Resume Optimizer')
    
    def test_get_templates_ajax(self):
        response = self.client.get(reverse('get_templates_ajax'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('templates', data)
        self.assertGreater(len(data['templates']), 0)

class FileProcessingTest(TestCase):
    def test_validate_file_size(self):
        # Create a mock file that's too large
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile("large.pdf", large_content, content_type="application/pdf")
        
        errors = validate_file(large_file)
        self.assertIn('File size must be less than 10MB', str(errors))
    
    def test_validate_file_extension(self):
        # Create a file with invalid extension
        invalid_file = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        
        errors = validate_file(invalid_file)
        self.assertTrue(any('files are allowed' in error for error in errors))
