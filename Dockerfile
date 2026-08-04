FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /service

RUN addgroup --system validator \
    && adduser --system --ingroup validator --home /nonexistent validator

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip install --no-cache-dir .

USER validator
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
