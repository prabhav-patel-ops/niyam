FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY app ./app
COPY web ./web
COPY .env.example ./
RUN useradd --uid 10001 --create-home niyam && mkdir -p data/prices data/benchmark data/fundamentals var && chown -R niyam:niyam /app
USER niyam
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
