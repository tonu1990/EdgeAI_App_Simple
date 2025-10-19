# Use Python 3.11 on Debian slim base
# Most portable - works on x86, ARM, any platform with Docker
FROM python:3.11-slim

# Metadata about the image
LABEL maintainer="your-email@example.com"
LABEL description="GStreamer Webcam Preview Application"
LABEL version="1.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install GStreamer and dependencies in a single layer
# This minimizes image size and speeds up builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core GStreamer packages
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-x \
    # Python GStreamer bindings (PyGObject)
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    # X11 libraries for display
    libx11-6 \
    libxv1 \
    # Clean up to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy the Python application
COPY src/webcam_preview.py .

# Make script executable (Linux best practice)
RUN chmod +x webcam_preview.py

# Default command when container starts
CMD ["python3", "webcam_preview.py"]