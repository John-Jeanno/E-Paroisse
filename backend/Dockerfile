FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system django && adduser --system --ingroup django django

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2 \
        libxml2-dev \
        libxslt1.1 \
        libxslt1-dev \
        zlib1g-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential libxml2-dev libxslt1-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=django:django . .
RUN mkdir -p /app/data /app/media /app/private_documents /app/staticfiles /app/models \
    && chown -R django:django /app/data /app/media /app/private_documents /app/staticfiles
RUN python scripts/download_french_voice.py

USER django
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
