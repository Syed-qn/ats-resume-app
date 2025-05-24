# # Use official Python image
# FROM python:3.11-slim

# # Set environment variables
# ENV PYTHONUNBUFFERED=1 \
#     PORT=8000 \
#     DJANGO_SETTINGS_MODULE=ats_resume_app.settings \
#     WEBS_CONCURRENCY=3

# # Set working directory
# WORKDIR /app

# # Install dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy project code
# COPY . .

# # Start Gunicorn server
# CMD gunicorn ats_resume_app.wsgi:application --bind 0.0.0.0:$PORT
FROM python:3.11-slim

# Install required system libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libxml2 \
    libgobject-2.0-0 \
    libxslt1.1 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the app
COPY . .

# Gunicorn start command
CMD gunicorn --bind 0.0.0.0:$PORT ats_resume_app.wsgi:application