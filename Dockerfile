# Use a lightweight Python base image
FROM python:3.10-slim AS builder

# Set the working directory
WORKDIR /app

# Install dependencies in a virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir "unstructured[pdf]"

# Use a final lightweight image
FROM python:3.10-slim AS final

# Install system dependencies required for OpenCV & PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application files
COPY . .

# Use virtual environment in PATH
ENV PATH="/opt/venv/bin:$PATH"

# Expose Streamlit's default port
EXPOSE 8501

# Optimize Streamlit
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_RUN_ON_SAVE=true

# Run the Streamlit app
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
