# STEP 1: Choose base image
FROM python:3.10-slim-bookworm

# STEP 2: Install ALL required system dependencies for PySide6
RUN apt-get update && apt-get install -y \
    # Core system libraries
    libgl1 \
    libglib2.0-0 \
    libdbus-1-3 \
    #  EGL interface for OpenGL - Raspberry Pi 5 has a GPU, but without libegl1, Qt can't use it
    libegl1 \ 
    # Font rendering
    libfontconfig1 \
    libfreetype6 \
    # X11 core libraries
    libx11-6 \
    libx11-xcb1 \
    libxext6 \
    libxrender1 \
    libsm6 \
    libice6 \
    # XCB base
    libxcb1 \
    # XCB extensions
    libxcb-cursor0 \
    libxcb-glx0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    # Keyboard support
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    # GStreamer dependencies
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-x \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    python3-gi \
    gir1.2-gst-rtsp-server-1.0 \
    libgirepository1.0-dev \
    # V4L2 for USB camera
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# STEP 3: Set working directory
WORKDIR /app

# STEP 4: Copy requirements file
COPY requirements.txt .

# STEP 5: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# STEP 6: Copy your application code
COPY src/ ./src/

# STEP 7: Set environment variables
ENV DISPLAY=:0
ENV QT_QPA_PLATFORM=xcb
ENV QT_DEBUG_PLUGINS=0

# STEP 8: Command to run when container starts
CMD ["python", "src/main.py"]