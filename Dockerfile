
FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

RUN python manage.py migrate

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:10000"]
