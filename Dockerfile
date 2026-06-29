FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g., build tools for dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Expose the Streamlit (7860) and FastAPI (8000) ports
EXPOSE 7860
EXPOSE 8000

# Set environment variable so Streamlit knows where to find FastAPI inside the container
ENV API_BASE_URL=http://localhost:8000

# Start FastAPI in the background and Streamlit in the foreground on the port required by Hugging Face (7860)
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port 7860 --server.address 0.0.0.0"]
