#!/usr/bin/env python3
"""
WEBCAM RANDOM BOX - HEAVILY INSTRUMENTED DEBUG VERSION

This version has extensive logging to help diagnose issues
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
print("WEBCAM RANDOM BOX - DEBUG VERSION")
print("=" * 70)
print(f"GStreamer version: {Gst.version_string()}")
print(f"Python version: {sys.version}")
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
# BUS MESSAGE HANDLER (Error Detection)
# ==========================================
def on_bus_message(bus, message):
    """
    Catch all GStreamer messages (errors, warnings, state changes)
    """
    t = message.type
    
    if t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"\n{'!' * 70}")
        print(f"GSTREAMER ERROR: {err}")
        print(f"DEBUG INFO: {debug}")
        print(f"{'!' * 70}\n")
        sys.exit(1)
    
    elif t == Gst.MessageType.WARNING:
        warn, debug = message.parse_warning()
        print(f"\nWARNING: {warn}")
        print(f"DEBUG: {debug}\n")
    
    elif t == Gst.MessageType.STATE_CHANGED:
        if message.src.get_name() == 'pipeline0':
            old, new, pending = message.parse_state_changed()
            print(f"[PIPELINE STATE] {old.value_nick} → {new.value_nick}")
    
    elif t == Gst.MessageType.EOS:
        print("\n[BUS] End of stream")
        main_loop.quit()
    
    return True


# ==========================================
# PATH 1: CAIRO DRAW CALLBACK
# ==========================================
def on_draw(overlay, context, timestamp, duration):
    """
    Called by CairoOverlay for each frame
    """
    global draw_callback_count
    draw_callback_count += 1
    
    # Log first few callbacks
    if draw_callback_count <= 5:
        print(f"[DRAW CALLBACK #{draw_callback_count}] Called! timestamp={timestamp}")
    elif draw_callback_count == 6:
        print(f"[DRAW CALLBACK] Now running silently (called {draw_callback_count} times so far)...")
    
    # Print every 100 frames
    if draw_callback_count % 100 == 0:
        print(f"[DRAW CALLBACK] Still running... ({draw_callback_count} total frames drawn)")
    
    # Read from shared variable
    boxes = latest_detections
    
    if not boxes:
        # Log first few times when no boxes
        if draw_callback_count <= 10:
            print(f"[DRAW CALLBACK #{draw_callback_count}] No boxes to draw yet")
        return
    
    # Log when we first get boxes
    if draw_callback_count <= 10 or (draw_callback_count <= 30 and draw_callback_count % 5 == 0):
        print(f"[DRAW CALLBACK #{draw_callback_count}] Drawing {len(boxes)} boxes!")
    
    # Set drawing style
    context.set_source_rgb(0, 1, 0)  # Green
    context.set_line_width(3)
    
    # Draw each box
    for i, box in enumerate(boxes):
        x, y, w, h = box['x'], box['y'], box['w'], box['h']
        
        # Draw rectangle
        context.rectangle(x, y, w, h)
        context.stroke()
        
        # Draw label
        context.move_to(x, y - 5)
        context.set_font_size(14)
        context.show_text(f"Box{i+1}")


# ==========================================
# PATH 2: DETECTION THREAD
# ==========================================
def detection_loop():
    """
    Runs in separate thread
    """
    global latest_detections, running, detection_frame_count
    
    print("\n[DETECTION THREAD] Starting...")
    
    # Calculate scale factors
    scale_x = DISPLAY_WIDTH / DETECTION_WIDTH
    scale_y = DISPLAY_HEIGHT / DETECTION_HEIGHT
    
    print(f"[DETECTION THREAD] Scale factors: x={scale_x}, y={scale_y}")
    print(f"[DETECTION THREAD] Waiting for frames from appsink...\n")
    
    consecutive_failures = 0
    max_failures = 10
    
    while running:
        try:
            # Pull frame from appsink
            sample = appsink.emit('pull-sample')
            
            if not sample:
                consecutive_failures += 1
                if consecutive_failures <= 3:
                    print(f"[DETECTION THREAD] No sample received (attempt {consecutive_failures})")
                if consecutive_failures >= max_failures:
                    print(f"[DETECTION THREAD] ERROR: Failed to get sample {max_failures} times. Appsink might not be producing frames!")
                    time.sleep(1)
                    consecutive_failures = 0
                continue
            
            # Reset failure counter on success
            if consecutive_failures > 0:
                print(f"[DETECTION THREAD] Sample received successfully after {consecutive_failures} failures")
                consecutive_failures = 0
            
            buffer = sample.get_buffer()
            
            # Extract frame
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                print("[DETECTION THREAD] ERROR: Could not map buffer!")
                continue
            
            # Create numpy array
            frame = np.ndarray(
                shape=(DETECTION_HEIGHT, DETECTION_WIDTH, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            
            buffer.unmap(map_info)
            
            detection_frame_count += 1
            
            # Log first few frames
            if detection_frame_count <= 5:
                print(f"[DETECTION THREAD] Processed frame #{detection_frame_count}, shape={frame.shape}")
            elif detection_frame_count == 6:
                print(f"[DETECTION THREAD] Now processing silently...")
            
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
            
            # Update shared variable
            latest_detections = detections
            
            # Log first update
            if detection_frame_count == 1:
                print(f"[DETECTION THREAD] First detection update! {len(detections)} boxes")
                print(f"[DETECTION THREAD] Sample box: {detections[0]}")
            
            # Print progress every 30 frames
            if detection_frame_count % 30 == 0:
                print(f"[DETECTION THREAD] Progress: {detection_frame_count} frames processed, {len(detections)} boxes")
            
            # Simulate processing time
            time.sleep(0.05)
        
        except Exception as e:
            print(f"[DETECTION THREAD] EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)
    
    print("[DETECTION THREAD] Exiting...")


# ==========================================
# MAIN
# ==========================================
def main():
    global appsink, running, main_loop
    
    print("[MAIN] Starting main function...")
    
    # ==========================================
    # CHECK CAMERA DEVICE
    # ==========================================
    import os
    if not os.path.exists(CAMERA_DEVICE):
        print(f"\n{'!' * 70}")
        print(f"ERROR: Camera device {CAMERA_DEVICE} does not exist!")
        print(f"Available video devices:")
        os.system("ls -la /dev/video*")
        print(f"{'!' * 70}\n")
        return
    else:
        print(f"[MAIN] ✓ Camera device {CAMERA_DEVICE} exists")
    
    # ==========================================
    # CHECK DISPLAY
    # ==========================================
    display = os.environ.get('DISPLAY')
    if not display:
        print(f"\n{'!' * 70}")
        print(f"ERROR: DISPLAY environment variable not set!")
        print(f"{'!' * 70}\n")
        return
    else:
        print(f"[MAIN] ✓ DISPLAY={display}")
    
    # ==========================================
    # BUILD PIPELINE
    # ==========================================
    print("\n[MAIN] Building pipeline...")
    print(f"[MAIN]   Display: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT} @ {FPS} FPS")
    print(f"[MAIN]   Detection: {DETECTION_WIDTH}x{DETECTION_HEIGHT}")
    
    pipeline_str = (
        f"v4l2src device={CAMERA_DEVICE} ! "
        f"video/x-raw,width={DISPLAY_WIDTH},height={DISPLAY_HEIGHT},framerate={FPS}/1 ! "
        "videoconvert ! "
        "video/x-raw,format=RGB ! "
        "tee name=t ! "
        "queue ! "
        "cairooverlay name=overlay ! "
        "videoconvert ! "
        "xvimagesink sync=false "
        "t. ! "
        "queue ! "
        "videoscale ! "
        f"video/x-raw,width={DETECTION_WIDTH},height={DETECTION_HEIGHT} ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
    print(f"\n[MAIN] Pipeline string:")
    print(f"  {pipeline_str}\n")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("[MAIN] ✓ Pipeline created successfully")
    except Exception as e:
        print(f"\n{'!' * 70}")
        print(f"ERROR: Failed to create pipeline!")
        print(f"Exception: {e}")
        print(f"{'!' * 70}\n")
        return
    
    # ==========================================
    # GET ELEMENTS
    # ==========================================
    print("\n[MAIN] Getting pipeline elements...")
    
    overlay = pipeline.get_by_name('overlay')
    if not overlay:
        print("ERROR: Could not find cairooverlay element!")
        print("Checking if cairooverlay plugin is available...")
        os.system("gst-inspect-1.0 cairooverlay")
        return
    else:
        print("[MAIN] ✓ Got cairooverlay element")
    
    appsink = pipeline.get_by_name('sink')
    if not appsink:
        print("ERROR: Could not find appsink element!")
        return
    else:
        print("[MAIN] ✓ Got appsink element")
    
    # ==========================================
    # CONNECT CALLBACKS
    # ==========================================
    print("\n[MAIN] Connecting callbacks...")
    
    try:
        overlay.connect('draw', on_draw)
        print("[MAIN] ✓ Connected draw callback to cairooverlay")
    except Exception as e:
        print(f"ERROR: Failed to connect draw callback: {e}")
        return
    
    # ==========================================
    # SET UP BUS
    # ==========================================
    print("\n[MAIN] Setting up message bus...")
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message)
    print("[MAIN] ✓ Bus message handler connected")
    
    # ==========================================
    # START DETECTION THREAD
    # ==========================================
    print("\n[MAIN] Starting detection thread...")
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    print("[MAIN] ✓ Detection thread started")
    
    # ==========================================
    # START PIPELINE
    # ==========================================
    print("\n[MAIN] Starting pipeline...")
    print("[MAIN] Transitioning to PLAYING state...")
    
    ret = pipeline.set_state(Gst.State.PLAYING)
    
    if ret == Gst.StateChangeReturn.FAILURE:
        print(f"\n{'!' * 70}")
        print("ERROR: Unable to set pipeline to PLAYING state!")
        print(f"{'!' * 70}\n")
        return
    elif ret == Gst.StateChangeReturn.ASYNC:
        print("[MAIN] State change is ASYNC, waiting...")
        ret, state, pending = pipeline.get_state(Gst.CLOCK_TIME_NONE)
        print(f"[MAIN] Final state: {state.value_nick}")
    else:
        print("[MAIN] ✓ Pipeline is PLAYING")
    
    # ==========================================
    # RUN MAIN LOOP
    # ==========================================
    print("\n" + "=" * 70)
    print("PIPELINE RUNNING!")
    print("=" * 70)
    print("What you should see:")
    print("  1. A window opens with webcam feed")
    print("  2. Green boxes appear randomly")
    print("  3. Draw callback logs appearing")
    print("  4. Detection thread logs appearing")
    print("\nIf you don't see a window:")
    print("  - Check if window appeared behind terminal")
    print("  - Check logs below for errors")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")
    
    # Give pipeline time to start
    time.sleep(2)
    
    # Check if callbacks are being called
    print(f"[MAIN] Status check after 2 seconds:")
    print(f"  Draw callbacks: {draw_callback_count}")
    print(f"  Detection frames: {detection_frame_count}")
    
    if draw_callback_count == 0:
        print("\n  ⚠ WARNING: Draw callback not being called!")
        print("  This means cairooverlay is not receiving frames")
    
    if detection_frame_count == 0:
        print("\n  ⚠ WARNING: Detection thread not receiving frames!")
        print("  This means appsink is not producing frames")
    
    print()
    
    # Run main loop
    main_loop = GLib.MainLoop()
    
    try:
        main_loop.run()
    except KeyboardInterrupt:
        print("\n\n[MAIN] Received Ctrl+C, stopping...")
        running = False
    
    # ==========================================
    # CLEANUP
    # ==========================================
    print("\n[MAIN] Cleaning up...")
    
    print(f"[MAIN] Final statistics:")
    print(f"  Total draw callbacks: {draw_callback_count}")
    print(f"  Total detection frames: {detection_frame_count}")
    
    pipeline.set_state(Gst.State.NULL)
    print("[MAIN] ✓ Pipeline stopped")
    
    detection_thread.join(timeout=2)
    print("[MAIN] ✓ Detection thread stopped")
    
    print("\n" + "=" * 70)
    print("DONE!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{'!' * 70}")
        print(f"FATAL EXCEPTION IN MAIN:")
        print(f"{e}")
        print(f"{'!' * 70}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)