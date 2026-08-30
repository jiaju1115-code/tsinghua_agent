FROM python:3.12-slim
WORKDIR /app
COPY apps/tsingask_v2/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=4)"
CMD ["python", "-m", "uvicorn", "apps.tsingask_v2.backend.main:app", "--host", "0.0.0.0", "--port", "8765"]
