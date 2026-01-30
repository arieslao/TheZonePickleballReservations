# Use official Playwright image which has all dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create session directory
RUN mkdir -p session_data

# Expose port (Railway will set PORT env var)
EXPOSE 5000

# Run with gunicorn
CMD gunicorn slack_server:app --bind 0.0.0.0:${PORT:-5000}
