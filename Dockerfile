# STEP 1: Choose base image
FROM python:3.10-slim-bookworm

# STEP 2: Install system dependencies (INCLUDING EGL!)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-cursor0 \
    libxcb-xfixes0 \
    libegl1 \
    libxkbcommon0 \
    libxcb-glx0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libfontconfig1 \
    libfreetype6 \
    libx11-6 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# STEP 3: Set working directory
WORKDIR /app

# STEP 4: Copy requirements file
COPY requirements.txt .

# STEP 5: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# STEP 6: Copy your application code
COPY src/ ./src/

# STEP 7: Set display environment
ENV DISPLAY=:0

# STEP 8: Command to run when container starts
CMD ["python", "src/main.py"]