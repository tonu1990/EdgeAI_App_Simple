#!/usr/bin/env python3
"""
SIMPLE Webcam Flip - Learning appsink and appsrc
Just the essentials!
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np

# Initialize GStreamer (must do this first!)
Gst.init(None)


def on_new_sample(appsink):
    """
    This function is called every time a new frame arrives
    """
    # STEP 1: Get the frame from appsink
    sample = appsink.emit("pull-sample")
    buffer = sample.get_buffer()
    
    # STEP 2: Convert GStreamer buffer to numpy array
    success, map_info = buffer.map(Gst.MapFlags.READ)
    frame = np.ndarray(shape=(480, 640, 3), dtype=np.uint8, buffer=map_info.data)
    
    # STEP 3: Flip the frame upside down
    flipped = np.flipud(frame)
    flipped = np.ascontiguousarray(flipped)  # Make sure memory is continuous
    
    # STEP 4: Clean up the original buffer
    buffer.unmap(map_info)
    
    # STEP 5: Create new buffer with flipped frame
    new_buffer = Gst.Buffer.new_wrapped(flipped.tobytes())
    
    # STEP 6: Push flipped frame to appsrc (so it can be displayed)
    appsrc.emit("push-buffer", new_buffer)
    
    return Gst.FlowReturn.OK


def main():
    print("Starting webcam flip...")
    
    # Build the pipeline string
    pipeline_string = (
        # Part 1: Get video from camera
        "v4l2src device=/dev/video0 ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "video/x-raw,format=RGB ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True "
        
        # Part 2: Display video
        "appsrc name=src is-live=True format=time ! "
        "video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! "
        "xvimagesink sync=false"
    )
    
    # Create the pipeline
    pipeline = Gst.parse_launch(pipeline_string)
    
    # Get the appsink and appsrc elements (make them global so callback can use)
    global appsink, appsrc
    appsink = pipeline.get_by_name("sink")
    appsrc = pipeline.get_by_name("src")
    
    # Tell appsrc what format we'll send it
    caps = Gst.Caps.from_string("video/x-raw,format=RGB,width=640,height=480,framerate=30/1")
    appsrc.set_property("caps", caps)
    
    # Connect our callback function to appsink
    appsink.connect("new-sample", on_new_sample)
    
    # Start the pipeline!
    pipeline.set_state(Gst.State.PLAYING)
    print("Pipeline started! You should see flipped video. Press Ctrl+C to stop.")
    
    # Run the main loop (keeps program running)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopping...")
    
    # Stop the pipeline
    pipeline.set_state(Gst.State.NULL)
    print("Done!")


if __name__ == "__main__":
    main()