FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    MCP_TRANSPORT=stdio \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN useradd --create-home --uid 10001 mcp
USER mcp

EXPOSE 8000

# Default is stdio (docker run -i). For HTTP: -e MCP_TRANSPORT=streamable-http -p 8000:8000
CMD ["python", "-m", "zendesk_mcp"]
