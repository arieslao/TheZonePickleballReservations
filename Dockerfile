# Use plain Python image instead of Playwright image
FROM python:3.11-slim

# Install system dependencies needed by Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN playwright install chromium

# Copy application code
COPY . .

# Create session directory
RUN mkdir -p session_data

# Expose port
EXPOSE 5000

# Run gunicorn
CMD ["sh", "-c", "exec gunicorn slack_server:app --bind 0.0.0.0:${PORT:-5000} --timeout 120 --workers 1"]
