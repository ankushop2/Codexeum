FROM node:24-bookworm-slim AS frontend
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.23.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/package.json
RUN pnpm install --frozen-lockfile
COPY frontend ./frontend
RUN pnpm build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 PORT=80
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY app.py ./
COPY --from=frontend /app/public ./public
RUN useradd --create-home battle
USER battle
EXPOSE 80
CMD ["sh", "-c", "exec .venv/bin/gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 app:app"]
