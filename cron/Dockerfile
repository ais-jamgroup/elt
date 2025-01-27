FROM python:3.9-slim

# Install additional dependencies
RUN apt-get update && apt-get install -y bash curl cron && rm -rf /var/lib/apt/lists/*

# Set up a virtual environment for Python packages
RUN python3 -m venv /app/venv

# Activate the virtual environment and install Python dependencies
RUN /app/venv/bin/pip install pandas sqlalchemy pymysql

# Add crontab file
COPY crontab /etc/crontabs/root

# Ensure the virtual environment is activated when running Python
ENV PATH="/app/venv/bin:$PATH"

# Start cron in foreground
CMD ["cron", "-f"]
