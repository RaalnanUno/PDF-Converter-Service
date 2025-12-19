FROM python:3.11-slim

# Install LibreOffice (headless conversion) + a few font packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Service listens on 8080
EXPOSE 8080

# Gunicorn is more production-like than Flask dev server
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
