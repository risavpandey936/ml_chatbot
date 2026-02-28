FROM python:3.10-slim

WORKDIR /app

# Install dependencies for Node.js
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend code and build it via NPM
COPY frontend/package.json ./frontend/
# If package-lock.json exists, uncomment the copy below, but for safety just use package.json
# COPY frontend/package-lock.json ./frontend/
RUN cd frontend && npm install
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# Copy the backend code and pipeline logic
COPY backend/ ./backend/
COPY pipeline/ ./pipeline/

ENV PORT=8000
EXPOSE $PORT

# Run via uvicorn directly
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
