FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY app/app.py .
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001
EXPOSE 5000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=2)" || exit 1
CMD ["gunicorn","--bind","0.0.0.0:5000","--worker-class","gthread","--workers","2","--threads","4","--timeout","60","app:app"]
