#!/usr/bin/env python3
"""
WEBCAM RANDOM BOX - FIXED VERSION
Fixed: CairoOverlay format compatibility
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import threading
import random
import time
import sys

# Initialize GStreamer
Gst.init(None)

print("\n" + "=" * 70)
print("WEBCAM RANDOM BOX - FIXED VERSION")
print("=" * 70)
print(f"GStreamer version: {Gst.version_string()}")
print("=" * 70 + "\n")

# ==========================================
# SHARED STATE
# ==========================================
latest_detections = []
running = True
draw_callback_count = 0
detection_frame_count = 0

# ==========================================
# CONFIGURATION
# ==========================================
CAMERA_DEVICE = "/dev/video0"
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480
DETECTION_WIDTH = 320
DETECTION_HEIGHT = 240
FPS = 30

# ==========================================
# BUS MESSAGE HANDLER
# ==========================================
def on_bus_message(bus, message):
    """Catch GStreamer messages"""
    t = message.type
    
    if t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"\n{'!' * 70}")
        print(f"GSTREAMER ERROR: {err}")
        print(f"DEBUG INFO: {debug}")
        print(f"{'!' * 70}\n")
        main_loop.quit()
    
    elif t == Gst.MessageType.WARNING:
        warn, debug = message.parse_warning()
        print(f"WARNING: {warn}")
    
    elif t == Gst.MessageType.STATE_CHANGED:
        if isinstance(message.src, Gst.Pipeline):
            old, new, pending = message.parse_state_changed()
            print(f"[PIPELINE STATE] {old.value_nick} → {new.value_nick}")
    
    elif t == Gst.MessageType.EOS:
        print("[BUS] End of stream")
        main_loop.quit()
    
    return True


# ==========================================
# PATH 1: CAIRO DRAW CALLBACK
# ==========================================
def on_draw(overlay, context, timestamp, duration):
    """Called by CairoOverlay for each frame"""
    global draw_callback_count
    draw_callback_count += 1
    
    if draw_callback_count <= 3:
        print(f"[DRAW CALLBACK #{draw_callback_count}] Called!")
    elif draw_callback_count == 4:
        print("[DRAW CALLBACK] Running normally (will report every 100 frames)...")
    
    if draw_callback_count % 100 == 0:
        print(f"[DRAW CALLBACK] Frame {draw_callback_count}, {len(latest_detections)} boxes")
    
    boxes = latest_detections
    if not boxes:
        return
    
    # Draw boxes
    context.set_source_rgb(0, 1, 0)  # Green
    context.set_line_width(3)
    
    for i, box in enumerate(boxes):
        x, y, w, h = box['x'], box['y'], box['w'], box['h']
        context.rectangle(x, y, w, h)
        context.stroke()
        
        # Label
        context.move_to(x, y - 5)
        context.set_font_size(14)
        context.show_text(f"Box{i+1}")


# ==========================================
# PATH 2: DETECTION THREAD
# ==========================================
def detection_loop():
    """Runs in separate thread"""
    global latest_detections, running, detection_frame_count
    
    print("[DETECTION THREAD] Started, waiting for frames...\n")
    
    scale_x = DISPLAY_WIDTH / DETECTION_WIDTH
    scale_y = DISPLAY_HEIGHT / DETECTION_HEIGHT
    
    while running:
        try:
            sample = appsink.emit('pull-sample')
            if not sample:
                time.sleep(0.01)
                continue
            
            buffer = sample.get_buffer()
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                continue
            
            # Note: appsink is getting RGB format
            frame = np.ndarray(
                shape=(DETECTION_HEIGHT, DETECTION_WIDTH, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            
            buffer.unmap(map_info)
            
            detection_frame_count += 1
            
            if detection_frame_count <= 3:
                print(f"[DETECTION] Frame #{detection_frame_count} received, shape={frame.shape}")
            elif detection_frame_count == 4:
                print("[DETECTION] Processing frames normally...\n")
            
            if detection_frame_count % 50 == 0:
                print(f"[DETECTION] Processed {detection_frame_count} frames")
            
            # Generate random boxes
            num_boxes = random.randint(1, 3)
            detections = []
            
            for i in range(num_boxes):
                x = random.randint(20, DETECTION_WIDTH - 80)
                y = random.randint(20, DETECTION_HEIGHT - 80)
                w = random.randint(40, 80)
                h = random.randint(40, 80)
                
                detections.append({
                    'x': int(x * scale_x),
                    'y': int(y * scale_y),
                    'w': int(w * scale_x),
                    'h': int(h * scale_y),
                    'confidence': random.uniform(0.7, 0.99)
                })
            
            latest_detections = detections
            
            if detection_frame_count == 1:
                print(f"[DETECTION] First update: {len(detections)} boxes\n")
            
            time.sleep(0.05)
        
        except Exception as e:
            print(f"[DETECTION] Exception: {e}")
            time.sleep(0.1)
    
    print("[DETECTION] Thread exiting")


# ==========================================
# MAIN
# ==========================================
def main():
    global appsink, running, main_loop
    
    print("[MAIN] Building pipeline with fixed format negotiation...\n")
    
    # THE FIX: Use two separate branches with proper format handling
    pipeline_str = (
        # SOURCE
        f"v4l2src device={CAMERA_DEVICE} ! "
        
        # Decode if MJPEG (common for USB webcams)
        "image/jpeg,width=640,height=480,framerate=30/1 ! "
        "jpegdec ! "
        
        # Convert to common format
        "videoconvert ! "
        
        # TEE splits here
        "tee name=t "
        
        # PATH 1: DISPLAY with CairoOverlay
        # Don't force format, let cairooverlay negotiate what it wants
        "t. ! queue ! "
        "videoconvert ! "  # Convert to whatever cairooverlay needs
        "cairooverlay name=overlay ! "
        "videoconvert ! "  # Convert for display
        "xvimagesink sync=false "
        
        # PATH 2: DETECTION
        # Force RGB for easy numpy processing
        "t. ! queue ! "
        "videoconvert ! "
        "videoscale ! "
        f"video/x-raw,format=RGB,width={DETECTION_WIDTH},height={DETECTION_HEIGHT} ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
    print("Pipeline string:")
    print(f"  {pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("[MAIN] ✓ Pipeline created\n")
    except Exception as e:
        print(f"ERROR creating pipeline: {e}\n")
        return
    
    # Get elements
    overlay = pipeline.get_by_name('overlay')
    appsink = pipeline.get_by_name('sink')
    
    if not overlay or not appsink:
        print("ERROR: Could not get pipeline elements\n")
        return
    
    print("[MAIN] ✓ Got overlay and appsink elements")
    
    # Connect callbacks
    overlay.connect('draw', on_draw)
    print("[MAIN] ✓ Connected draw callback")
    
    # Set up bus
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message)
    print("[MAIN] ✓ Bus connected\n")
    
    # Start detection thread
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    print("[MAIN] ✓ Detection thread started\n")
    
    # Start pipeline
    print("[MAIN] Starting pipeline...\n")
    ret = pipeline.set_state(Gst.State.PLAYING)
    
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Could not start pipeline\n")
        return
    
    print("=" * 70)
    print("RUNNING! You should see:")
    print("  - Webcam window opens")
    print("  - Green boxes appear randomly")
    print("  - Logs showing callbacks running")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")
    
    # Give it time to start
    time.sleep(3)
    
    print(f"Status check:")
    print(f"  Draw callbacks: {draw_callback_count}")
    print(f"  Detection frames: {detection_frame_count}\n")
    
    if draw_callback_count == 0:
        print("⚠ WARNING: Draw callback not called yet\n")
    if detection_frame_count == 0:
        print("⚠ WARNING: Detection not receiving frames yet\n")
    
    # Run main loop
    main_loop = GLib.MainLoop()
    
    try:
        main_loop.run()
    except KeyboardInterrupt:
        print("\n\n[MAIN] Stopping...\n")
        running = False
    
    # Cleanup
    print(f"Final stats:")
    print(f"  Draw callbacks: {draw_callback_count}")
    print(f"  Detection frames: {detection_frame_count}\n")
    
    pipeline.set_state(Gst.State.NULL)
    detection_thread.join(timeout=2)
    
    print("Done!\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)