FROM python:3.13-slim AS production
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY app ./app
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM production AS test
USER root
COPY requirements-test.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-test.lock
COPY tests ./tests
RUN chown -R appuser:appuser /app
USER appuser
CMD ["python", "-m", "pytest"]
