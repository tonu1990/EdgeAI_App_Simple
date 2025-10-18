# STEP 1: Use Debian base to avoid dual-Python issue
# debian:bookworm has single Python 3.11 installation
FROM debian:bookworm-slim

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# STEP 2: Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python installation
    python3 \
    python3-pip \
    python3-venv \
    # GStreamer + Python bindings (pre-compiled for Python 3.11)
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-x \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgirepository1.0-dev \
    gir1.2-gst-rtsp-server-1.0 \
    # Core system libraries
    libgl1 \
    libglib2.0-0 \
    libdbus-1-3 \
    # EGL interface for OpenGL - Raspberry Pi 5 GPU support
    libegl1 \
    # Font rendering
    libfontconfig1 \
    libfreetype6 \
    fontconfig \
    fonts-dejavu-core \
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
    # V4L2 for USB camera
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Build font cache for better text rendering
RUN fc-cache -f -v

# STEP 3: Set working directory
WORKDIR /app

# STEP 4: Copy requirements file
COPY requirements.txt .

# STEP 5: Create virtual environment with system-site-packages flag
# This allows venv to access system's python3-gi while keeping pip packages isolated
RUN python3 -m venv /opt/venv --system-site-packages && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# STEP 6: Copy your application code
COPY src/ ./src/

# STEP 7: Set environment variables
# Add venv to PATH so 'python' uses venv's Python (which can see python3-gi)
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    DISPLAY=:0 \
    QT_QPA_PLATFORM=xcb \
    QT_DEBUG_PLUGINS=0 \
    GST_DEBUG=2 \
    PYTHONUNBUFFERED=1

# STEP 8: Command to run when container starts
CMD ["python", "src/main.py"]
