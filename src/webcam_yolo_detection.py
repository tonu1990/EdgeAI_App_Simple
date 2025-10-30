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
from yolo_detector_optimized_phase1 import YOLODetectorNMS as YOLODetector

# Initialize GStreamer
Gst.init(None)

print("\n" + "=" * 70)
print("WEBCAM YOLO OBJECT DETECTION")
print("=" * 70)
print(f"GStreamer version: {Gst.version_string()}")
print("=" * 70 + "\n")

 
####### CONFIGURATION #############
# Get model path from environment variable
MODEL_PATH = os.environ.get('MODEL_PATH', '/models/current.onnx')

# Camera settings
CAMERA_DEVICE = "/dev/video0"
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480
FPS = 30

# Detection settings
DETECTION_WIDTH = 416       # ← match model we are using ONNX converted YOLO
DETECTION_HEIGHT = 416      # ← match model we are using ONNX converted YOLO
CONF_THRESHOLD = 0.5        # Minimum confidence (0.0-1.0)


######## Cairooverlay SHARED STATE (The "Whiteboard") ############
# Detection thread WRITES, Draw callback READS
latest_detections = []
running = True

# Statistics
draw_callback_count = 0
detection_frame_count = 0
 

########## INITIALIZE YOLO DETECTOR ###############
# Check if model exists
if not os.path.exists(MODEL_PATH):     
    print(f"\nERROR: Model file not found at: {MODEL_PATH}") 
    sys.exit(1)

# Create YOLO detector - our custom class 
try:
    yolo_detector = YOLODetector(
        model_path=MODEL_PATH,
        input_size=DETECTION_WIDTH,
        conf_threshold=CONF_THRESHOLD
    )
except Exception as e:     
    print(f"\nERROR: Failed to load YOLO model: {e}")     
    sys.exit(1)

 
# BUS MESSAGE HANDLER
def on_bus_message(bus, message):
    """
    Handle GStreamer bus messages (errors, warnings, etc.)
    """
    global running, main_loop
    t = message.type
    
    if t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"GSTREAMER ERROR: {err}")
        print(f"DEBUG INFO: {debug}") 
        running = False
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
        running = False
        main_loop.quit()
    
    return True


# ==========================================
# PATH 1: CAIRO DRAW CALLBACK
# ==========================================
def on_draw(overlay, context, timestamp, duration):
    """
    Draw callback - called by CairoOverlay for EACH frame (30 FPS)
    
    This is where we draw the bounding boxes on the video!
 
    """
    global draw_callback_count
    draw_callback_count += 1    
    
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
        
        # STEP 1: Draw bounding box 
        context.set_line_width(2)                              # Line thickness
        context.rectangle(x, y, w, h)                          # Draw rectangle
        context.stroke()                                       # Actually draw it
        
        # STEP 2: Draw label background (filled rectangle)
        label = f"{class_name}: {confidence:.2f}"
        label_height = 20
        label_width = len(label) * 8        
        # Make background slightly darker 
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
                       
            detection_frame_count += 1
            
            ################# STEP 2: RUN YOLO DETECTION ###############
            detections = yolo_detector.detect(frame)
            ############################################################

            # Clean up buffer
            buffer.unmap(map_info)
            
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
            
       
        except Exception as e:
            print(f"[DETECTION] Error: {e}")
            time.sleep(0.1)
    
    print("[DETECTION THREAD] Exiting")


# MAIN FUNCTION
# ==========================================
def main():
    """
    Main function - sets up and runs everything
    """
    global appsink, running, main_loop
    
    print("\n[MAIN] Building GStreamer pipeline...")
    
 
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
        "t. ! queue max-size-buffers=1 leaky=downstream ! " #prevents buildup if one branch hiccups 
        "videoconvert ! "                    # Let cairooverlay negotiate format
        "cairooverlay name=overlay ! "       # Drawing happens here
        "videoconvert ! "                    # Convert for display
        "xvimagesink sync=false "
        
        # PATH 2: DETECTION BRANCH (416x416 for YOLO)
        "t. ! queue max-size-buffers=1 leaky=downstream ! "
        "videoconvert ! "
        "videoscale ! "
        f"video/x-raw,format=RGB,width={DETECTION_WIDTH},height={DETECTION_HEIGHT} ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )
    
   
    # Create pipeline
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("[PIPELINE] ✓ Pipeline created\n")
    except Exception as e:
        print(f"[PIPELINE] ERROR: Failed to create pipeline: {e}\n")
        return
    
    # GET PIPELINE ELEMENTS
    overlay = pipeline.get_by_name('overlay')
    appsink = pipeline.get_by_name('sink')
    
    if not overlay or not appsink:
        print("[PIPELINE] ERROR: Could not get pipeline elements\n")
        return    
    print("Got overlay and appsink elements")
    

    # CONNECT CALLBACKS
    # Connect draw callback to cairooverlay
    overlay.connect('draw', on_draw)
    print("Connected draw callback\n")
       
    
    ##### START DETECTION THREAD ########
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    print("Detection thread started\n")
    
 
    ######### START PIPELINE  #############
    print("[MAIN] Starting pipeline...\n")
    ret = pipeline.set_state(Gst.State.PLAYING)
    
    if ret == Gst.StateChangeReturn.FAILURE:
        print("[MAIN] ERROR: Could not start pipeline\n")
        return
    
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
    
    ######## RUN MAIN LOOP ##################
    main_loop = GLib.MainLoop()

    # SET UP BUS
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message)
    print("Bus message handler connected\n")
    
    try:
        main_loop.run()
    except KeyboardInterrupt:
        print("\n\n[MAIN] Stopping...\n")
        running = False
    
  
    # CLEANUP    
    pipeline.set_state(Gst.State.NULL)
    print("[MAIN] ✓ Pipeline stopped")
    
    detection_thread.join(timeout=2)
    print(" Detection thread stopped\n")


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