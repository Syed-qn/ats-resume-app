FROM python:3.11-slim

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libcairo2 \
    pango1.0-tools \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libxml2 \
    libxslt1.1 \
    libgobject-2.0-0 \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Gunicorn start command
CMD gunicorn --bind 0.0.0.0:$PORT ats_resume_app.wsgi:application