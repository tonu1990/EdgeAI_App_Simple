# STEP 1: Choose base image (like choosing a foundation for a house)
# Using official Python image for ARM64 (Raspberry Pi architecture)
FROM python:3.10-slim-bookworm

# STEP 2: Install system dependencies needed for PySide6
# These are like tools needed before building
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
    && rm -rf /var/lib/apt/lists/*

# STEP 3: Set working directory (like creating a project folder)
WORKDIR /app

# STEP 4: Copy requirements file
COPY requirements.txt .

# STEP 5: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# STEP 6: Copy your application code
COPY src/ ./src/

# STEP 7: Set display environment for GUI (allows window to show)
ENV DISPLAY=:0

# STEP 8: Command to run when container starts
CMD ["python", "src/main.py"]