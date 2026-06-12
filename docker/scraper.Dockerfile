FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY scraper/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the scraper package
COPY scraper/ /app/scraper/

# Copy the analytics package
COPY analytics/ /app/analytics/

ENTRYPOINT ["python", "-m", "scraper"]