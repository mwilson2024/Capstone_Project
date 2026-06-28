# Base image: PyTorch + CUDA + cuDNN already installed.
# This saves you from manually installing CUDA drivers/toolkit yourself,
# which is the most common source of pain in GPU Docker setups.
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# Install system-level dependencies.
# opencv (cv2) needs some OS libraries that aren't in a minimal Python image.
# ffmpeg is needed for moviepy to actually encode video.
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
# Everything from here on happens relative to /app.
WORKDIR /app

# Copy ONLY requirements first, not the whole project.
# This is a caching trick: Docker caches each step (layer). If you change
# your code but not your dependencies, this layer is reused and you skip
# re-installing everything on every build, which saves a lot of time.
COPY requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your project (code, model files if local, etc.)
COPY . .

# Document which port the app listens on (informational, doesn't actually
# publish it -- that happens at `docker run` time with -p).
EXPOSE 8000

# The command that runs when the container starts.
# --host 0.0.0.0 is required -- without it, the app only listens inside
# the container and you can't reach it from outside.
CMD ["uvicorn", "mainAPI:app", "--host", "0.0.0.0", "--port", "8000"]
