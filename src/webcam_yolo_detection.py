#!/usr/bin/env python3
"""
Webcam YOLO Object Detection with GStreamer

MAIN APPLICATION FILE

This is the entry point that:
1. Loads the YOLO model from environment variable
2. Creates GStreamer pipeline with tee (two paths)
3. Runs detection in a separate thread
4. Draws bounding boxes using CairoOverlay

ARCHITECTURE:
Camera → tee → Path 1: Display (cairooverlay draws boxes)
          └─→ Path 2: Detection (YOLO inference)

Boxes are shared via global variable (the "whiteboard")
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import threading
import time
import sys
import os

# Import our custom modules
from yolo_detector import YOLODetector
from coco_classes import get_class_color

# Initialize GStreamer
Gst.init(None)

print("\n" + "=" * 70)
print("WEBCAM YOLO OBJECT DETECTION")
print("=" * 70)
print(f"GStreamer version: {Gst.version_string()}")
print("=" * 70 + "\n")

# ==========================================
# CONFIGURATION
# ==========================================

# Get model path from environment variable
MODEL_PATH = os.environ.get('MODEL_PATH', '/models/current.onnx')

# Camera settings
CAMERA_DEVICE = "/dev/video0"
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480
FPS = 30

# Detection settings
# Detection settings
DETECTION_WIDTH = 640       # ← match model we are using ONNX converted YOLO
DETECTION_HEIGHT = 640      # ← match model we are using ONNX converted YOLO

CONF_THRESHOLD = 0.5        # Minimum confidence (0.0-1.0)
NMS_THRESHOLD = 0.45        # NMS IoU threshold

# ==========================================
# SHARED STATE (The "Whiteboard")
# ==========================================
# Detection thread WRITES, Draw callback READS
latest_detections = []
running = True

# Statistics
draw_callback_count = 0
detection_frame_count = 0

# ==========================================
# INITIALIZE YOLO DETECTOR
# ==========================================
print(f"[SETUP] Model path: {MODEL_PATH}")

# Check if model exists
if not os.path.exists(MODEL_PATH):
    print(f"\n{'!' * 70}")
    print(f"ERROR: Model file not found at: {MODEL_PATH}")
    print(f"Make sure you mounted the model directory correctly!")
    print(f"{'!' * 70}\n")
    sys.exit(1)

# Create YOLO detector
try:
    yolo_detector = YOLODetector(
        model_path=MODEL_PATH,
        input_size=DETECTION_WIDTH,
        conf_threshold=CONF_THRESHOLD,
        nms_threshold=NMS_THRESHOLD
    )
except Exception as e:
    print(f"\n{'!' * 70}")
    print(f"ERROR: Failed to load YOLO model: {e}")
    print(f"{'!' * 70}\n")
    sys.exit(1)


# ==========================================
# BUS MESSAGE HANDLER
# ==========================================
def on_bus_message(bus, message):
    """
    Handle GStreamer bus messages (errors, warnings, etc.)
    """
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
    """
    Draw callback - called by CairoOverlay for EACH frame (30 FPS)
    
    This is where we draw the bounding boxes on the video!
    
    Args:
        overlay: The cairooverlay element
        context: Cairo drawing context (like a canvas)
        timestamp: Frame timestamp
        duration: Frame duration
    """
    global draw_callback_count
    draw_callback_count += 1
    
    # Log first few frames
    if draw_callback_count <= 3:
        print(f"[DRAW] Frame {draw_callback_count}")
    elif draw_callback_count == 4:
        print("[DRAW] Drawing continuously (will report every 100 frames)...")
    
    if draw_callback_count % 100 == 0:
        print(f"[DRAW] Frame {draw_callback_count}, {len(latest_detections)} objects")
    
    # Read from shared variable (the "whiteboard")
    detections = latest_detections
    
    # If no detections, nothing to draw
    if not detections:
        return
    
    # Draw each detected object
    for detection in detections:
        # Extract box coordinates
        x = detection['x']
        y = detection['y']
        w = detection['w']
        h = detection['h']
        class_name = detection['class_name']
        confidence = detection['confidence']
        
        # Get color for this class
        color = get_class_color(class_name)
        
        # STEP 1: Draw bounding box
        context.set_source_rgb(color[0], color[1], color[2])  # Set color
        context.set_line_width(2)                              # Line thickness
        context.rectangle(x, y, w, h)                          # Draw rectangle
        context.stroke()                                       # Actually draw it
        
        # STEP 2: Draw label background (filled rectangle)
        label = f"{class_name}: {confidence:.2f}"
        label_height = 20
        label_width = len(label) * 8
        
        # Make background slightly darker
        context.set_source_rgba(color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, 0.8)
        context.rectangle(x, y - label_height, label_width, label_height)
        context.fill()
        
        # STEP 3: Draw label text
        context.set_source_rgb(1, 1, 1)  # White text
        context.select_font_face("Sans", 0, 1)  # Font: Sans, normal, bold
        context.set_font_size(12)
        context.move_to(x + 2, y - 5)
        context.show_text(label)


# ==========================================
# PATH 2: DETECTION THREAD
# ==========================================
def detection_loop():
    """
    Detection thread - runs continuously in background
    
    WORKFLOW:
    1. Pull frame from appsink (416x416 RGB)
    2. Run YOLO detection
    3. Scale coordinates from 416x416 to 640x480
    4. Update shared variable (write to "whiteboard")
    5. Repeat!
    """
    global latest_detections, running, detection_frame_count
    
    print("\n[DETECTION THREAD] Started!")
    print(f"[DETECTION THREAD] Processing at {DETECTION_WIDTH}x{DETECTION_HEIGHT}")
    print(f"[DETECTION THREAD] Confidence threshold: {CONF_THRESHOLD}\n")
    
    # Calculate scale factors for coordinate conversion
    # Detection runs on 416x416, display is 640x480
    scale_x = DISPLAY_WIDTH / DETECTION_WIDTH
    scale_y = DISPLAY_HEIGHT / DETECTION_HEIGHT
    
    print(f"[DETECTION THREAD] Scale factors: x={scale_x:.2f}, y={scale_y:.2f}\n")
    
    while running:
        try:
            # STEP 1: Pull frame from appsink
            sample = appsink.emit('pull-sample')
            if not sample:
                time.sleep(0.01)
                continue
            
            buffer = sample.get_buffer()
            
            # Extract frame as numpy array
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                continue
            
            # Create numpy array view of the buffer
            # Shape: (height, width, channels)
            frame = np.ndarray(
                shape=(DETECTION_HEIGHT, DETECTION_WIDTH, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )
            
            # Clean up buffer
            buffer.unmap(map_info)
            
            detection_frame_count += 1
            
            # Log first few frames
            if detection_frame_count <= 3:
                print(f"[DETECTION] Processing frame {detection_frame_count}")
            elif detection_frame_count == 4:
                print("[DETECTION] Processing continuously...\n")
            
            # STEP 2: Run YOLO detection
            detections = yolo_detector.detect(frame)
            
            # STEP 3: Scale coordinates to display size
            scaled_detections = []
            for det in detections:
                # Scale from detection size to display size
                scaled_det = {
                    'x': int(det['x'] * scale_x),
                    'y': int(det['y'] * scale_y),
                    'w': int(det['w'] * scale_x),
                    'h': int(det['h'] * scale_y),
                    'class_id': det['class_id'],
                    'class_name': det['class_name'],
                    'confidence': det['confidence']
                }
                scaled_detections.append(scaled_det)
            
            # STEP 4: Update shared variable (write to "whiteboard")
            latest_detections = scaled_detections
            
            # Log detections periodically
            if detection_frame_count % 50 == 0:
                print(f"[DETECTION] Frame {detection_frame_count}: {len(detections)} objects detected")
                if detections:
                    for det in detections[:3]:  # Show first 3
                        print(f"  - {det['class_name']}: {det['confidence']:.2f}")
        
        except Exception as e:
            print(f"[DETECTION] Error: {e}")
            time.sleep(0.1)
    
    print("[DETECTION THREAD] Exiting")


# ==========================================
# MAIN FUNCTION
# ==========================================
def main():
    """
    Main function - sets up and runs everything
    """
    global appsink, running, main_loop
    
    print("\n[MAIN] Building GStreamer pipeline...")
    
    # ==========================================
    # BUILD GSTREAMER PIPELINE
    # ==========================================
    # Note: Two branches with proper format handling for cairooverlay
    
    pipeline_str = (
        # SOURCE: Camera
        f"v4l2src device={CAMERA_DEVICE} ! "
        
        # Decode MJPEG (common format for USB webcams)
        "image/jpeg,width=640,height=480,framerate=30/1 ! "
        "jpegdec ! "
        
        # Convert to common format
        "videoconvert ! "
        
        # TEE: Split into two paths
        "tee name=t "
        
        # PATH 1: DISPLAY BRANCH (30 FPS, smooth)
        "t. ! queue ! "
        "videoconvert ! "                    # Let cairooverlay negotiate format
        "cairooverlay name=overlay ! "       # Drawing happens here
        "videoconvert ! "                    # Convert for display
        "xvimagesink sync=false "
        
        # PATH 2: DETECTION BRANCH (416x416 for YOLO)
        "t. ! queue ! "
        "videoconvert ! "
        "videoscale ! "
        f"video/x-raw,format=RGB,width={DETECTION_WIDTH},height={DETECTION_HEIGHT} ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
    print(f"\n[PIPELINE] Configuration:")
    print(f"  Display: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT} @ {FPS} FPS")
    print(f"  Detection: {DETECTION_WIDTH}x{DETECTION_HEIGHT}")
    print(f"  Camera: {CAMERA_DEVICE}\n")
    
    # Create pipeline
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("[PIPELINE] ✓ Pipeline created\n")
    except Exception as e:
        print(f"[PIPELINE] ERROR: Failed to create pipeline: {e}\n")
        return
    
    # ==========================================
    # GET PIPELINE ELEMENTS
    # ==========================================
    overlay = pipeline.get_by_name('overlay')
    appsink = pipeline.get_by_name('sink')
    
    if not overlay or not appsink:
        print("[PIPELINE] ERROR: Could not get pipeline elements\n")
        return
    
    print("[PIPELINE] ✓ Got overlay and appsink elements")
    
    # ==========================================
    # CONNECT CALLBACKS
    # ==========================================
    # Connect draw callback to cairooverlay
    overlay.connect('draw', on_draw)
    print("[PIPELINE] ✓ Connected draw callback\n")
    
    # ==========================================
    # SET UP BUS
    # ==========================================
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message)
    print("[PIPELINE] ✓ Bus message handler connected\n")
    
    # ==========================================
    # START DETECTION THREAD
    # ==========================================
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    print("[MAIN] ✓ Detection thread started\n")
    
    # ==========================================
    # START PIPELINE
    # ==========================================
    print("[MAIN] Starting pipeline...\n")
    ret = pipeline.set_state(Gst.State.PLAYING)
    
    if ret == Gst.StateChangeReturn.FAILURE:
        print("[MAIN] ERROR: Could not start pipeline\n")
        return
    
    print("=" * 70)
    print("SYSTEM RUNNING!")
    print("=" * 70)
    print("What you should see:")
    print("  ✓ Webcam window opens")
    print("  ✓ Objects detected with bounding boxes")
    print("  ✓ Class labels (person, car, etc.)")
    print("  ✓ Confidence scores")
    print("\nPerformance:")
    print(f"  Display: 30 FPS (smooth)")
    print(f"  Detection: ~20 FPS (YOLO inference)")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")
    
    # Give pipeline time to start
    time.sleep(3)
    
    # Status check
    print(f"[STATUS CHECK] After 3 seconds:")
    print(f"  Draw callbacks: {draw_callback_count}")
    print(f"  Detection frames: {detection_frame_count}")
    print(f"  Current detections: {len(latest_detections)}\n")
    
    if draw_callback_count == 0:
        print("  ⚠ WARNING: Draw callback not running!\n")
    if detection_frame_count == 0:
        print("  ⚠ WARNING: Detection not running!\n")
    
    # ==========================================
    # RUN MAIN LOOP
    # ==========================================
    main_loop = GLib.MainLoop()
    
    try:
        main_loop.run()
    except KeyboardInterrupt:
        print("\n\n[MAIN] Stopping...\n")
        running = False
    
    # ==========================================
    # CLEANUP
    # ==========================================
    print("[MAIN] Final statistics:")
    print(f"  Total frames drawn: {draw_callback_count}")
    print(f"  Total frames detected: {detection_frame_count}\n")
    
    pipeline.set_state(Gst.State.NULL)
    print("[MAIN] ✓ Pipeline stopped")
    
    detection_thread.join(timeout=2)
    print("[MAIN] ✓ Detection thread stopped\n")
    
    print("=" * 70)
    print("SHUTDOWN COMPLETE")
    print("=" * 70 + "\n")


# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{'!' * 70}")
        print(f"FATAL ERROR: {e}")
        print(f"{'!' * 70}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)