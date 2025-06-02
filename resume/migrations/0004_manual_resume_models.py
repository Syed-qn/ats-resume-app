# Create this file: resume/migrations/0004_manual_resume_models.py
# Run: python manage.py makemigrations resume
# Then: python manage.py migrate

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resume', '0003_profile'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManualResume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_complete', models.BooleanField(default=False)),
                ('full_name', models.CharField(max_length=100)),
                ('professional_title', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=20)),
                ('city', models.CharField(max_length=100)),
                ('state_province', models.CharField(blank=True, max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('linkedin_url', models.URLField(blank=True, null=True)),
                ('portfolio_url', models.URLField(blank=True, null=True)),
                ('professional_summary', models.TextField(help_text='2-3 sentences summarizing your career goals and key strengths')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manual_resumes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='VolunteerExperience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_title', models.CharField(max_length=200)),
                ('organization_name', models.CharField(max_length=200)),
                ('city', models.CharField(max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=False)),
                ('responsibilities', models.TextField()),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='volunteer_experiences', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', '-start_date'],
            },
        ),
        migrations.CreateModel(
            name='WorkExperience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_title', models.CharField(max_length=200)),
                ('company_name', models.CharField(max_length=200)),
                ('company_city', models.CharField(max_length=100)),
                ('company_country', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=False)),
                ('responsibilities', models.TextField(help_text='Enter 3-5 bullet points describing key accomplishments, technologies used, and metrics')),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_experiences', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', '-start_date'],
            },
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill_type', models.CharField(choices=[('technical', 'Technical Skills'), ('soft', 'Soft Skills'), ('tools', 'Tools & Platforms')], max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('proficiency', models.CharField(choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced'), ('expert', 'Expert')], default='intermediate', max_length=20)),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to='resume.manualresume')),
            ],
            options={
                'ordering': ['skill_type', 'order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('role', models.CharField(help_text='e.g., Team Lead, Contributor', max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_ongoing', models.BooleanField(default=False)),
                ('description', models.TextField(help_text='2-4 sentences detailing objectives, technologies/frameworks used, and outcome')),
                ('demo_url', models.URLField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', '-start_date'],
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('proficiency', models.CharField(choices=[('native', 'Native'), ('fluent', 'Fluent'), ('professional', 'Professional'), ('intermediate', 'Intermediate'), ('beginner', 'Beginner')], max_length=20)),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='languages', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Education',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('degree_name', models.CharField(max_length=200)),
                ('institution_name', models.CharField(max_length=200)),
                ('institution_city', models.CharField(max_length=100)),
                ('institution_country', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=False)),
                ('gpa', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('relevant_coursework', models.TextField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='education_entries', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', '-start_date'],
            },
        ),
        migrations.CreateModel(
            name='Certification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('issuing_organization', models.CharField(max_length=200)),
                ('date_obtained', models.DateField()),
                ('expiration_date', models.DateField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certifications', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', '-date_obtained'],
            },
        ),
        migrations.CreateModel(
            name='Award',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('issuing_organization', models.CharField(max_length=200)),
                ('date_received', models.DateField()),
                ('description', models.TextField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('resume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awards', to='resume.manualresume')),
            ],
            options={
                'ordering': ['order', '-date_received'],
            },
        ),
        migrations.AddConstraint(
            model_name='skill',
            constraint=models.UniqueConstraint(fields=('resume', 'name'), name='unique_skill_per_resume'),
        ),
    ]