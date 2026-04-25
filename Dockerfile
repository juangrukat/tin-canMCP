FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY requirements.txt .
COPY pyproject.toml ./

RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY main.py .
COPY app/ ./app/
COPY catalog-runtime/ ./catalog-runtime/
COPY scripts/ ./scripts/
COPY .env.example ./.env.example

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=stdio

CMD ["python", "main.py"]
