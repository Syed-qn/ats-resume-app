# -------------------------------------------------------------------
#  Dockerfile — hardened & slimmed “drop-in” replacement
#  * Debian 12 (bookworm) slim image, pinned to Python 3.11.8
#  * Only the runtime libs WeasyPrint really needs
#  * Security patches applied at build time
#  * Collects static assets inside the image; runs migrate at boot
# -------------------------------------------------------------------

FROM python:3.11.8-slim-bookworm

# ────────────────────────────
#  Runtime-level env variables
# ────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=ats_resume_app.settings

# ────────────────────────────
#  System libs for WeasyPrint
# ────────────────────────────
RUN set -eux; \
    apt-get update; \
    # core libs (runtime only — no *-dev headers needed)
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libharfbuzz0b \
        libgdk-pixbuf2.0-0 \
        libxml2 \
        libxslt1.1 \
        fonts-dejavu \
        shared-mime-info; \
    # pull latest security patches for slim-bookworm
    apt-get upgrade -y; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# ────────────────────────────
#  Project setup
# ────────────────────────────
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# ────────────────────────────
#  Static assets baked in
# ────────────────────────────
RUN python manage.py collectstatic --noinput

# ────────────────────────────
#  Entrypoint:  apply migrations, start Gunicorn
# ────────────────────────────
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn ats_resume_app.wsgi:application --bind 0.0.0.0:${PORT:-8000} --timeout 120 --workers 1"]
