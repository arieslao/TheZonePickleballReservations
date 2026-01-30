#!/bin/bash
set -e

echo "=== Entrypoint starting ==="
echo "PORT: ${PORT:-not set}"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Contents: $(ls -la)"

echo "=== Testing imports ==="
python -c "
import sys
print('Python path:', sys.path)
try:
    print('Importing flask...', end=' ')
    import flask
    print('OK')
except Exception as e:
    print('FAILED:', e)

try:
    print('Importing slack_server...', end=' ')
    import slack_server
    print('OK')
    print('  app object:', slack_server.app)
except Exception as e:
    print('FAILED:', e)
    import traceback
    traceback.print_exc()
"

echo "=== Starting gunicorn ==="
exec gunicorn slack_server:app --bind 0.0.0.0:${PORT:-5000} --timeout 120 --workers 1 --access-logfile - --error-logfile -
