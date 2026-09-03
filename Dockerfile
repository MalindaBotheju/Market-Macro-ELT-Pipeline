FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2-binary build backends / dbt-postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# One entrypoint: run extract+load, then dbt run, then dbt test.
# Fails (non-zero exit) if any stage fails, which is what makes the GitHub
# Actions job go red instead of silently succeeding on a broken pipeline.
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
