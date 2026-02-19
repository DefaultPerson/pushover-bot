FROM python:3.14-slim

WORKDIR /app

# Install uv for fast package management
RUN pip install --no-cache-dir uv

# Copy and install aiogram-broadcast from libs context
COPY --from=libs aiogram-broadcast/ ./aiogram-broadcast/
RUN uv pip install --system --no-cache ./aiogram-broadcast

# Copy and install main dependencies
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY assets/ ./assets/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "src.main"]
