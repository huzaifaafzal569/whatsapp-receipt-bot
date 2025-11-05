FROM python:3.10

WORKDIR /app

# Install system dependencies (important for paddleocr + opencv)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt /app/requirements.txt

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel
RUN python -m pip install uvicorn
RUN python -m pip install celery

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt
# RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='es)"



# Copy app files
COPY ./app /app

EXPOSE 8000

CMD ["python", "-m","uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
