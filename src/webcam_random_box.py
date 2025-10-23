#!/usr/bin/env python3
"""
WEBCAM RANDOM BOX - Learning CairoOverlay Approach

ARCHITECTURE:
Camera → tee → Path 1: cairooverlay → Display (30 FPS, smooth!)
          └─→ Path 2: appsink → Python (generates random boxes)

Key Concept: Video never leaves GStreamer, only coordinates cross boundary
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import threading
import random
import time

# Initialize GStreamer
Gst.init(None)

# ==========================================
# SHARED STATE: The "Whiteboard"
# ==========================================
# Both paths access this variable:
# - Detection thread WRITES
# - Draw callback READS
latest_detections = []
running = True

# ==========================================
# CONFIGURATION
# ==========================================
CAMERA_DEVICE = "/dev/video0"
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480
DETECTION_WIDTH = 320    # Smaller for faster processing
DETECTION_HEIGHT = 240
FPS = 30

# ==========================================
# PATH 1: CAIRO DRAW CALLBACK
# ==========================================
def on_draw(overlay, context, timestamp, duration):
    """
    Called by CairoOverlay for EVERY display frame (30 FPS)
 
    """
    # Read from shared variable (whatever is there right now)
    boxes = latest_detections
    
    if not boxes:
        return  # No boxes to draw yet
    
    # Set drawing style
    context.set_source_rgb(0, 1, 0)  # Green color (R, G, B from 0-1)
    context.set_line_width(3)         # Thick lines
    
    # Draw each bounding box
    for box in boxes:
        x, y, w, h = box['x'], box['y'], box['w'], box['h']
        
        # Draw rectangle outline
        context.rectangle(x, y, w, h)
        context.stroke()
        
        # Draw a label (optional)
        context.move_to(x, y - 5)
        context.set_font_size(14)
        context.show_text(f"Box {box['confidence']:.2f}")


# ==========================================
# PATH 2: DETECTION THREAD
# ==========================================
def detection_loop():
    """
    Runs in separate thread, continuously:
    1. Pulls frames from appsink
    2. "Detects" objects (generates random boxes)
    3. Scales coordinates to display size
    4. Updates shared variable
    """
    global latest_detections, running
    
    print("\n[DETECTION THREAD] Started!")
    
    # Calculate scale factors (detection size → display size)
    scale_x = DISPLAY_WIDTH / DETECTION_WIDTH
    scale_y = DISPLAY_HEIGHT / DETECTION_HEIGHT
    
    frame_count = 0
    
    while running:
        # Pull frame from appsink
        sample = appsink.emit('pull-sample')
        if not sample:
            continue
        
        buffer = sample.get_buffer()
        
        # Extract frame as numpy array
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            continue
        
        # Frame shape: (240, 320, 3) - height, width, RGB
        frame = np.ndarray(
            shape=(DETECTION_HEIGHT, DETECTION_WIDTH, 3),
            dtype=np.uint8,
            buffer=map_info.data
        )
        
        # Clean up
        buffer.unmap(map_info)
        
        # ==========================================
        # "DETECTION" LOGIC: Generate random boxes
        # ==========================================
        # In real code, this would be: detections = yolo.detect(frame)
        
        num_boxes = random.randint(1, 3)  # 1-3 random boxes
        detections = []
        
        for i in range(num_boxes):
            # Random position and size (in detection frame coordinates)
            x = random.randint(20, DETECTION_WIDTH - 80)
            y = random.randint(20, DETECTION_HEIGHT - 80)
            w = random.randint(40, 80)
            h = random.randint(40, 80)
            
            # Scale coordinates to DISPLAY size
            detections.append({
                'x': int(x * scale_x),
                'y': int(y * scale_y),
                'w': int(w * scale_x),
                'h': int(h * scale_y),
                'confidence': random.uniform(0.7, 0.99)
            })
        
        # Update shared variable (write to whiteboard)
        latest_detections = detections
        
        # Print progress
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"[DETECTION] Processed {frame_count} frames, {len(detections)} boxes")
        
        # Small delay to simulate processing time
        time.sleep(0.05)  # 50ms = 20 FPS detection rate


# ==========================================
# MAIN: PIPELINE SETUP
# ==========================================
def main():
    global appsink, running
    

    # ==========================================
    # BUILD THE PIPELINE WITH TEE
    # ==========================================
    pipeline_str = (
        # SOURCE: Camera
        f"v4l2src device={CAMERA_DEVICE} ! "
        f"video/x-raw,width={DISPLAY_WIDTH},height={DISPLAY_HEIGHT},framerate={FPS}/1 ! "
        "videoconvert ! "
        "video/x-raw,format=RGB ! "
        
        # TEE: Split into two paths
        "tee name=t ! "
        
        # PATH 1: DISPLAY (High quality, full size)
        "queue ! "
        "cairooverlay name=overlay ! "  # This is where we draw!
        "videoconvert ! "
        "xvimagesink sync=false "
        
        # PATH 2: DETECTION (Low quality, small size)
        "t. ! "
        "queue ! "
        f"videoscale ! "
        f"video/x-raw,width={DETECTION_WIDTH},height={DETECTION_HEIGHT} ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
    print("\n[PIPELINE] Creating...")
    print(f"  Display: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT} @ {FPS} FPS")
    print(f"  Detection: {DETECTION_WIDTH}x{DETECTION_HEIGHT}")
    
    # Create pipeline
    pipeline = Gst.parse_launch(pipeline_str)
    
    # ==========================================
    # GET ELEMENT REFERENCES
    # ==========================================
    # Get cairooverlay element (for drawing)
    overlay = pipeline.get_by_name('overlay')
    if not overlay:
        print("ERROR: Could not find cairooverlay element!")
        return
    
    # Get appsink element (for detection)
    appsink = pipeline.get_by_name('sink')
    if not appsink:
        print("ERROR: Could not find appsink element!")
        return
    
    print("[PIPELINE] Got cairooverlay and appsink elements")
    
    # ==========================================
    # CONNECT DRAW CALLBACK
    # ==========================================
    # Tell cairooverlay to call our on_draw function for each frame
    overlay.connect('draw', on_draw)
    print("[PIPELINE] Connected draw callback to cairooverlay")
    
    # ==========================================
    # START DETECTION THREAD
    # ==========================================
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    print("[PIPELINE] Started detection thread")
    
    # ==========================================
    # START PIPELINE
    # ==========================================
    print("\n[PIPELINE] Starting...")
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Could not start pipeline!")
        return
    
    print("\n" + "=" * 60)
    print("RUNNING!")
    print("=" * 60)
    print("You should see:")
    print("  - Smooth video at 30 FPS")
    print("  - Random green boxes moving around")
    print("  - Boxes update ~20 times per second")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # ==========================================
    # RUN MAIN LOOP
    # ==========================================
    loop = GLib.MainLoop()
    
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n\n[MAIN] Stopping...")
        running = False
    
    # ==========================================
    # CLEANUP
    # ==========================================
    print("[MAIN] Cleaning up...")
    pipeline.set_state(Gst.State.NULL)
    
    # Wait for detection thread to finish
    detection_thread.join(timeout=2)
    
    print("[MAIN] Done!")


# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    main()