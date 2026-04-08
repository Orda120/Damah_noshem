FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace/apps/api

COPY apps/api/pyproject.toml /workspace/apps/api/pyproject.toml
RUN pip install --upgrade pip && pip install -e .[dev]

COPY . /workspace

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
