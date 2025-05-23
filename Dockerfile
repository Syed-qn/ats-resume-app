# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=ats_resume_app.settings \
    WEBS_CONCURRENCY=3

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Start Gunicorn server
CMD ["gunicorn", "ats_resume_app.wsgi:application", "--bind", "0.0.0.0:$PORT"]