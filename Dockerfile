FROM python:3.11-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required by WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libgdk-pixbuf2.0-0 \
    libgdk-pixbuf2.0-dev \
    libxml2 \
    libxslt1.1 \
    libglib2.0-0 \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment variable for Django
ENV DJANGO_SETTINGS_MODULE=ats_resume_app.settings

# Collect static files and run migrations before starting server
RUN mkdir -p /app/staticfiles
# after
RUN python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput

# Final entrypoint to apply migrations and start gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn ats_resume_app.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 1"]