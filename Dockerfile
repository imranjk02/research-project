FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn myproject.wsgi:application --bind 0.0.0.0:10000"]