#!/usr/bin/env python3
"""
WEBCAM FLIP EXAMPLE - Learning appsink and appsrc

PURPOSE:
This program demonstrates the loop-back pattern in GStreamer.
It captures webcam frames, flips them upside down in Python,
and displays the flipped result.

ARCHITECTURE:
Two separate GStreamer pipelines connected through Python:
  Pipeline 1: Camera → appsink (frames EXIT to Python)
  Pipeline 2: appsrc → Display (frames ENTER from Python)
  
Python sits in the middle, processing each frame.
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import sys

# ==========================================
# EVENT 1: INITIALIZATION
# ==========================================
# Initialize GStreamer library
# MUST be called before any GStreamer operations!
# This sets up internal GStreamer state and loads plugins
Gst.init(None)

# Global variables to hold pipelines and elements
# We make these global so the callback function can access them
capture_pipeline = None  # Pipeline 1: Camera to appsink
display_pipeline = None  # Pipeline 2: appsrc to display
appsink = None          # Element that exits frames to Python
appsrc = None           # Element that enters frames from Python


# ==========================================
# EVENT 8: CALLBACK FUNCTION (Runs automatically for each frame)
# ==========================================
def on_new_sample(sink):
    """
    AUTOMATIC FRAME PROCESSOR
    
    This function is called by GStreamer for EVERY frame that arrives.
    You don't call it yourself - GStreamer calls it automatically!
    Runs 30 times per second (30 FPS).
    
    THE FRAME JOURNEY IN THIS FUNCTION:
    1. Frame arrives at appsink (from camera)
    2. Pull frame into Python
    3. Convert to numpy array
    4. Flip upside down
    5. Push back to appsrc (for display)
    
    Args:
        sink: The appsink element (passed automatically by GStreamer)
    
    Returns:
        Gst.FlowReturn.OK: Tells GStreamer everything went fine
    """
    
    # ==========================================
    # STEP 1: GET THE FRAME FROM APPSINK
    # ==========================================
    # "pull-sample" is a signal that retrieves one frame
    # A "sample" is a package containing the frame buffer + metadata
    sample = sink.emit("pull-sample")
    
    # Safety check: Make sure we got a sample
    if not sample:
        print("WARNING: No sample received!")
        return Gst.FlowReturn.ERROR
    
    # Extract the actual buffer (raw frame data) from the sample
    buffer = sample.get_buffer()
    
    # ==========================================
    # STEP 2: MAP BUFFER TO READABLE MEMORY
    # ==========================================
    # GStreamer buffers are memory blocks we need to "map" to access
    # Mapping makes the memory readable by Python
    # Gst.MapFlags.READ means we only read, not write
    success, map_info = buffer.map(Gst.MapFlags.READ)
    
    # Check if mapping succeeded
    if not success:
        print("ERROR: Could not map buffer to memory!")
        return Gst.FlowReturn.ERROR
    
    # ==========================================
    # STEP 3: CONVERT TO NUMPY ARRAY
    # ==========================================
    # Create a numpy array as a VIEW of the buffer memory
    # This doesn't copy data - it just wraps the existing memory
    # 
    # Shape breakdown:
    #   (480, 640, 3) = (height, width, channels)
    #   480 = height in pixels
    #   640 = width in pixels  
    #   3 = RGB channels (Red, Green, Blue)
    #
    # dtype=np.uint8: Each color value is 0-255 (unsigned 8-bit integer)
    frame = np.ndarray(
        shape=(480, 640, 3), 
        dtype=np.uint8, 
        buffer=map_info.data
    )
    
    # ==========================================
    # STEP 4: FLIP THE FRAME UPSIDE DOWN
    # ==========================================
    # np.flipud = "flip up-down" (vertical flip)
    # This reverses the row order: top becomes bottom, bottom becomes top
    flipped = np.flipud(frame)
    
    # Make the flipped array contiguous in memory
    # Some operations create non-contiguous arrays (data scattered in memory)
    # GStreamer needs contiguous memory, so we ensure it here
    flipped = np.ascontiguousarray(flipped)
    
    # ==========================================
    # STEP 5: CLEANUP ORIGINAL BUFFER
    # ==========================================
    # IMPORTANT: Always unmap after you're done reading!
    # This releases the memory lock and allows GStreamer to reuse the buffer
    buffer.unmap(map_info)
    
    # ==========================================
    # STEP 6: CREATE NEW GSTREAMER BUFFER
    # ==========================================
    # Convert our numpy array back into a GStreamer buffer
    # .tobytes() converts the array to raw bytes
    # Gst.Buffer.new_wrapped() wraps those bytes in a GStreamer buffer
    new_buffer = Gst.Buffer.new_wrapped(flipped.tobytes())
    
    # ==========================================
    # STEP 7: PUSH TO APPSRC FOR DISPLAY
    # ==========================================
    # "push-buffer" signal sends the frame into the display pipeline
    # This is where the frame RE-ENTERS GStreamer from Python
    ret = appsrc.emit("push-buffer", new_buffer)
    
    # Check if push was successful
    if ret != Gst.FlowReturn.OK:
        print(f"WARNING: push-buffer returned {ret}")
    
    # Tell GStreamer this callback succeeded
    return Gst.FlowReturn.OK


# ==========================================
# MAIN FUNCTION: SETS UP EVERYTHING
# ==========================================
def main():
    """
    MAIN SETUP AND EXECUTION
    
    This function:
    1. Creates two separate pipelines
    2. Configures appsink and appsrc
    3. Connects the callback
    4. Starts both pipelines
    5. Runs the main loop
    6. Cleans up on exit
    """
    
    # Make our global variables accessible in this function
    global capture_pipeline, display_pipeline, appsink, appsrc
    
    print("=" * 50)
    print("WEBCAM FLIP - Learning appsink/appsrc")
    print("=" * 50)
    
    # ==========================================
    # EVENT 2: CREATE PIPELINE 1 - CAPTURE
    # ==========================================
    # This pipeline: Camera → Conversion → appsink
    # Ends at appsink (frames exit to Python here)
    
    capture_string = (
        # SOURCE: Get video from USB webcam
        "v4l2src device=/dev/video0 ! "
        
        # CAPS FILTER: Set resolution and framerate
        # 640x480 at 30 frames per second
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        
        # CONVERT: Change to a common format
        "videoconvert ! "
        
        # CAPS FILTER: Force RGB format
        # RGB is easy to work with in numpy (Red, Green, Blue order)
        "video/x-raw,format=RGB ! "
        
        # SINK: appsink - the exit point to Python
        # Properties:
        #   name=sink - so we can find it later
        #   emit-signals=True - allows callbacks
        #   max-buffers=1 - only keep latest frame (don't build up queue)
        #   drop=True - drop old frames if Python is slow
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
    print("\n[1/7] Creating CAPTURE pipeline...")
    print(f"      {capture_string}")
    
    # Parse the string and create the pipeline object
    capture_pipeline = Gst.parse_launch(capture_string)
    
    # Check if creation succeeded
    if not capture_pipeline:
        print("ERROR: Failed to create capture pipeline!")
        sys.exit(1)
    print("      ✓ Capture pipeline created")
    
    # ==========================================
    # EVENT 2: CREATE PIPELINE 2 - DISPLAY
    # ==========================================
    # This pipeline: appsrc → Conversion → Display
    # Starts at appsrc (frames enter from Python here)
    
    display_string = (
        # SOURCE: appsrc - the entrance point from Python
        # Properties:
        #   name=src - so we can find it later
        #   is-live=True - this is live video (not a file)
        #   format=time - use time-based format
        "appsrc name=src is-live=True format=time ! "
        
        # CAPS FILTER: Tell pipeline what format to expect
        # Must match what we'll push from Python
        "video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
        
        # CONVERT: Convert from RGB to whatever display needs
        "videoconvert ! "
        
        # SINK: Display on screen
        # sync=false - don't wait for exact timing, just display fast
        "xvimagesink sync=false"
    )
    
    print("\n[2/7] Creating DISPLAY pipeline...")
    print(f"      {display_string}")
    
    # Parse the string and create the pipeline object
    display_pipeline = Gst.parse_launch(display_string)
    
    # Check if creation succeeded
    if not display_pipeline:
        print("ERROR: Failed to create display pipeline!")
        sys.exit(1)
    print("      ✓ Display pipeline created")
    
    # ==========================================
    # EVENT 3: GET ELEMENT REFERENCES
    # ==========================================
    # Extract the named elements so we can interact with them
    
    print("\n[3/7] Getting element references...")
    
    # Find appsink in capture pipeline by the name we gave it
    appsink = capture_pipeline.get_by_name("sink")
    
    # Find appsrc in display pipeline by the name we gave it
    appsrc = display_pipeline.get_by_name("src")
    
    # Verify we got both elements
    if not appsink or not appsrc:
        print("ERROR: Could not find appsink or appsrc elements!")
        sys.exit(1)
    print("      ✓ Got appsink from capture pipeline")
    print("      ✓ Got appsrc from display pipeline")
    
    # ==========================================
    # EVENT 4: CONFIGURE APPSRC
    # ==========================================
    # Tell appsrc what format of data we'll be pushing to it
    
    print("\n[4/7] Configuring appsrc...")
    
    # Create a caps (capabilities) string describing our frame format
    # This is like declaring the "data type" for frames
    caps_string = "video/x-raw,format=RGB,width=640,height=480,framerate=30/1"
    caps = Gst.Caps.from_string(caps_string)
    
    # Set the caps on appsrc
    # Now appsrc knows what to expect when we push frames
    appsrc.set_property("caps", caps)
    print(f"      ✓ Set caps: {caps_string}")
    
    # ==========================================
    # EVENT 5: CONNECT CALLBACK
    # ==========================================
    # Register our processing function to be called for each frame
    
    print("\n[5/7] Connecting callback function...")
    
    # "new-sample" is a SIGNAL that appsink emits when a frame arrives
    # We connect our on_new_sample function to this signal
    # GStreamer will call on_new_sample() automatically for each frame
    appsink.connect("new-sample", on_new_sample)
    print("      ✓ Callback connected to appsink")
    print("      → on_new_sample() will be called for each frame")
    
    # ==========================================
    # EVENT 6: START BOTH PIPELINES
    # ==========================================
    # Transition from NULL → PLAYING state
    
    print("\n[6/7] Starting pipelines...")
    
    # Start the CAPTURE pipeline
    # This begins capturing frames from the camera
    ret = capture_pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Could not start capture pipeline!")
        sys.exit(1)
    print("      ✓ Capture pipeline PLAYING (camera active)")
    
    # Start the DISPLAY pipeline
    # This opens the display window and prepares to receive frames
    ret = display_pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Could not start display pipeline!")
        sys.exit(1)
    print("      ✓ Display pipeline PLAYING (window open)")
    
    print("\n" + "=" * 50)
    print("RUNNING!")
    print("=" * 50)
    print("You should see your webcam feed UPSIDE DOWN")
    print("Callback is processing 30 frames per second")
    print("Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    
    # ==========================================
    # EVENT 7: RUN MAIN LOOP
    # ==========================================
    # Keep the program alive and process events
    
    # Create the main loop
    # This is an event loop that keeps the program running
    loop = GLib.MainLoop()
    
    try:
        # Run the loop (BLOCKS HERE until interrupted)
        # While this is running:
        #   - Capture pipeline grabs frames
        #   - on_new_sample() is called for each frame
        #   - Display pipeline shows frames
        # This continues indefinitely until Ctrl+C
        loop.run()
        
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("\n\nReceived interrupt signal (Ctrl+C)")
        print("Shutting down gracefully...")
    
    # ==========================================
    # EVENT 9: CLEANUP
    # ==========================================
    # Stop pipelines and release resources
    
    print("\n[7/7] Cleaning up...")
    
    # Stop the capture pipeline