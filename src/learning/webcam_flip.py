#!/usr/bin/env python3
"""
SIMPLE Webcam Flip - Learning appsink and appsrc
TWO separate pipelines connected through Python
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import sys

# Initialize GStreamer (must do this first!)
Gst.init(None)

# Global variables for pipelines and elements
capture_pipeline = None
display_pipeline = None
appsink = None
appsrc = None


def on_new_sample(sink):
    """
    This function is called every time a new frame arrives
    """
    # STEP 1: Get the frame from appsink
    sample = sink.emit("pull-sample")
    if not sample:
        return Gst.FlowReturn.ERROR
        
    buffer = sample.get_buffer()
    
    # STEP 2: Convert GStreamer buffer to numpy array
    success, map_info = buffer.map(Gst.MapFlags.READ)
    if not success:
        return Gst.FlowReturn.ERROR
        
    frame = np.ndarray(shape=(480, 640, 3), dtype=np.uint8, buffer=map_info.data)
    
    # STEP 3: Flip the frame upside down
    flipped = np.flipud(frame)
    flipped = np.ascontiguousarray(flipped)  # Make sure memory is continuous
    
    # STEP 4: Clean up the original buffer
    buffer.unmap(map_info)
    
    # STEP 5: Create new buffer with flipped frame
    new_buffer = Gst.Buffer.new_wrapped(flipped.tobytes())
    
    # STEP 6: Push flipped frame to appsrc (so it can be displayed)
    ret = appsrc.emit("push-buffer", new_buffer)
    
    return Gst.FlowReturn.OK


def main():
    global capture_pipeline, display_pipeline, appsink, appsrc
    
    print("=" * 50)
    print("Starting webcam flip...")
    print("=" * 50)
    
    # BUILD TWO SEPARATE PIPELINES!
    
    # PIPELINE 1: Capture from camera to appsink (Python exit)
    capture_string = (
        "v4l2src device=/dev/video0 ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "video/x-raw,format=RGB ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
    # PIPELINE 2: appsrc to display (Python entrance)
    display_string = (
        "appsrc name=src is-live=True format=time ! "
        "video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "xvimagesink sync=false"
    )
    
    print("Creating CAPTURE pipeline...")
    capture_pipeline = Gst.parse_launch(capture_string)
    if not capture_pipeline:
        print("ERROR: Failed to create capture pipeline!")
        sys.exit(1)
    
    print("Creating DISPLAY pipeline...")
    display_pipeline = Gst.parse_launch(display_string)
    if not display_pipeline:
        print("ERROR: Failed to create display pipeline!")
        sys.exit(1)
    
    # Get the appsink and appsrc elements
    appsink = capture_pipeline.get_by_name("sink")
    appsrc = display_pipeline.get_by_name("src")
    
    if not appsink or not appsrc:
        print("ERROR: Could not get appsink or appsrc!")
        sys.exit(1)
    
    print("Configuring appsrc...")
    # Tell appsrc what format we'll send it
    caps = Gst.Caps.from_string("video/x-raw,format=RGB,width=640,height=480,framerate=30/1")
    appsrc.set_property("caps", caps)
    
    print("Connecting callback...")
    # Connect our callback function to appsink
    appsink.connect("new-sample", on_new_sample)
    
    # Start BOTH pipelines!
    print("Starting CAPTURE pipeline...")
    ret = capture_pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Could not start capture pipeline!")
        sys.exit(1)
    
    print("Starting DISPLAY pipeline...")
    ret = display_pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Could not start display pipeline!")
        sys.exit(1)
    
    print("=" * 50)
    print("Pipeline started! You should see flipped video.")
    print("Press Ctrl+C to stop.")
    print("=" * 50)
    
    # Run the main loop (keeps program running)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping...")
    
    # Stop BOTH pipelines
    print("Cleaning up...")
    capture_pipeline.set_state(Gst.State.NULL)
    display_pipeline.set_state(Gst.State.NULL)
    print("Done!")


if __name__ == "__main__":
    main()