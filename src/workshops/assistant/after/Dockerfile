# The capstone image — one build, two services. The compose file in
# phase8-deploy/01-compose runs this same image as the assistant API (default CMD)
# and as the MCP server (command override: python -m assistant.mcp_server --http).
#
# Multi-stage: uv resolves and installs in the first stage, the runtime stage gets
# the finished virtualenv and the source, nothing else. Both stages are bookworm so
# the venv's interpreter path survives the copy.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --group integration --no-dev

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY src/ src/
# Which commit is inside this image, baked in because there is no .git here to
# ask later. `/health` reports it, and a post-deploy smoke check compares it to
# the SHA it just shipped — the only probe that catches a half-finished rollout
# still serving an old, perfectly healthy machine.
ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA}
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "--factory", "assistant.api:create_app", "--host", "0.0.0.0", "--port", "8000"]
