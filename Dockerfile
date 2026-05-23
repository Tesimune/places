FROM python:3.13-slim

# Install uv installer binaries
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency specification files first to leverage build caching layers
COPY pyproject.toml uv.lock ./

# Install application dependencies cleanly
RUN uv sync --frozen --no-cache

# Copy over the rest of the application files (including main.py and your static/ folder)
COPY . /app

# Expose the matching internal container port
EXPOSE 8000

# Default fallback command if compose doesn't override it
CMD ["/app/.venv/bin/fastapi", "run", "main.py", "--port", "8000", "--host", "0.0.0.0"]