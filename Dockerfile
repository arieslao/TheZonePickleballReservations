# Use official Playwright image which has all dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers (to match installed playwright version)
RUN playwright install chromium

# Copy application code
COPY . .

# Create session directory
RUN mkdir -p session_data

# Expose port (Railway will set PORT env var)
EXPOSE 5000

# Override the entrypoint from base image and run gunicorn directly
ENTRYPOINT []
CMD ["sh", "-c", "exec gunicorn slack_server:app --bind 0.0.0.0:${PORT:-5000} --timeout 120 --workers 1"]
