FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py quote_pdf.py quote_pdf_backup.py ./
COPY thiago-reis-pro ./thiago-reis-pro
ENV PORT=8000
CMD ["sh","-c","gunicorn -w 2 -b 0.0.0.0:${PORT:-8000} server:app"]
