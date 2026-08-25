FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -e .

EXPOSE 8010

CMD ["uvicorn", "adp_da.api:app", "--host", "0.0.0.0", "--port", "8010"]
