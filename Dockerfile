FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/mobilitypro
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd -m -u 10001 mobilitypro
COPY backend/ ./backend/
COPY apps/ ./apps/
RUN mkdir -p /var/lib/mobilitypro/documents && chown -R mobilitypro:mobilitypro /var/lib/mobilitypro
USER mobilitypro
ENV APP_ENV=production PRIVATE_DOCS=/var/lib/mobilitypro/documents
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=8s --start-period=25s --retries=3 \
 CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/api/health',timeout=4)" || exit 1
CMD ["sh", "-c", "python -c 'from backend.migrate import migrate; migrate()' && exec uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips=*"]
