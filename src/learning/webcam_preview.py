#!/usr/bin/env python3
"""
GStreamer Webcam Preview Application
Displays live webcam feed using GStreamer pipeline
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys

def main():
    """Main function to run GStreamer webcam preview"""
    
    # Initialize GStreamer
    Gst.init(None)
    
    # Define the pipeline
    # Uses MJPEG format at 640x480, 30fps with hardware-accelerated display
    pipeline_string = (
        "v4l2src device=/dev/video0 ! "
        "image/jpeg,width=640,height=480,framerate=30/1 ! "
        "jpegdec ! "
        "xvimagesink"
    )
    
    print("Starting GStreamer Webcam Preview...")
    print(f"Pipeline: {pipeline_string}")
    
    # Create pipeline from string
    pipeline = Gst.parse_launch(pipeline_string)
    
    # Start playing
    pipeline.set_state(Gst.State.PLAYING)
    print("Pipeline started successfully!")
    print("Preview window should appear. Press Ctrl+C to stop...")
    
    # Create main loop to keep the application running
    loop = GLib.MainLoop()
    
    try:
        # Run the main loop (blocks here until interrupted)
        loop.run()
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal. Stopping pipeline...")
    
    # Clean shutdown
    pipeline.set_state(Gst.State.NULL)
    print("Pipeline stopped. Goodbye!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())