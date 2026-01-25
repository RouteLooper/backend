FROM python:3.11-slim

# Reduce Python overhead
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Install dependencies first (layer caching = faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app

# Make sure GPX directory exists
RUN mkdir -p /app/gpx

# Expose the port (Azure injects PORT env var)
EXPOSE 8000

# Run the server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
