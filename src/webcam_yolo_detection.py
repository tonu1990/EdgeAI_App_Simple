#!/usr/bin/env python3
"""
Webcam YOLO Object Detection with GStreamer

Main responsibilities:
1) Load YOLO NMS-fused ONNX model
2) Build GStreamer pipeline with tee → Display and Detection branches
3) Run detection in a background thread
4) Draw boxes via cairooverlay (uses a shared "whiteboard" list)
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import numpy as np
import threading
import time
import sys
import os

from yolo_detector_optimized_phase1 import YOLODetectorNMS as YOLODetector

# Init GStreamer
Gst.init(None)

print("\nWEBCAM YOLO OBJECT DETECTION") 
print(f"\nGStreamer version: {Gst.version_string()}")
print("=" * 70 + "\n")

# ---------- CONFIG ----------
MODEL_PATH = os.environ.get('MODEL_PATH', '/models/current.onnx')
CAMERA_DEVICE = "/dev/video0"

DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480

DETECTION_WIDTH = 416
DETECTION_HEIGHT = 416
CONF_THRESHOLD = 0.5

# Shared state for overlay
latest_detections = []    # detection thread writes; draw callback reads
running = True

# MainLoop ref for bus handler (set in main() before starting pipeline)
main_loop = None

# ---------------- Bus handler ----------------
def on_bus_message(bus, message):
    """
    Handle GStreamer bus messages (errors, warnings, EOS).
    We can safely call main_loop.quit() because main() creates it before PLAYING.
    """
    global running, main_loop
    t = message.type

    if t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"GSTREAMER ERROR: {err}\nDEBUG: {debug}")
        running = False
        if main_loop:
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
        if main_loop:
            main_loop.quit()

    return True


# ---------------- Overlay draw callback ----------------
def on_draw(overlay, context, timestamp, duration):
    """
    Draw bounding boxes + labels for each frame on the display branch.
    """
    detections = latest_detections
    if not detections:
        return

    for det in detections:
        x = det['x']
        y = det['y']
        w = det['w']
        h = det['h']
        class_name = det['class_name']
        confidence = det['confidence']

        # 1) Box outline
        context.set_line_width(2)
        context.rectangle(x, y, w, h)
        context.stroke()

        # 2) Label background (now semi-transparent + clamped to screen top)
        label = f"{class_name}: {confidence:.2f}"
        label_height = 20
        label_width = len(label) * 8

        # Clamp label so it never goes above the frame
        label_y = y - label_height if (y - label_height) >= 0 else y + label_height

        # Semi-transparent black background so video stays visible under text
        context.set_source_rgba(0, 0, 0, 0.6)
        context.rectangle(x, label_y, label_width, label_height)
        context.fill()

        # 3) Label text (white)
        context.set_source_rgb(1, 1, 1)
        context.select_font_face("Sans", 0, 1)  # normal, bold
        context.set_font_size(12)
        context.move_to(x + 2, label_y + label_height - 5)
        context.show_text(label)


# ---------------- Detection thread ----------------
def detection_loop():
    """
    Pull frames from appsink → run YOLO → scale boxes → update shared 'latest_detections'.
    """
    global latest_detections, running

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

            # Build an array view over the mapped memory (416x416x3 RGB)
            frame = np.ndarray(
                shape=(DETECTION_HEIGHT, DETECTION_WIDTH, 3),
                dtype=np.uint8,
                buffer=map_info.data
            )

            # Run detection BEFORE unmapping to keep memory valid
            detections = yolo_detector.detect(frame)

            # Now safe to unmap
            buffer.unmap(map_info)

            # Scale detections from 416x416 → 640x480 for drawing
            scaled = []
            for d in detections:
                scaled.append({
                    'x': int(d['x'] * scale_x),
                    'y': int(d['y'] * scale_y),
                    'w': int(d['w'] * scale_x),
                    'h': int(d['h'] * scale_y),
                    'class_id': d['class_id'],
                    'class_name': d['class_name'],
                    'confidence': d['confidence']
                })

            latest_detections = scaled

        except Exception as e:
            print(f"[DETECTION] Error: {e}")
            time.sleep(0.1)

    print("[DETECTION THREAD Exiting")


# ---------------- Main ----------------
def main():
    """
    Build pipeline → prepare bus & main loop → start detection thread → PLAY → run loop.
    """
    global appsink, running, main_loop

    print("\n[MAIN] Building GStreamer pipeline...")

    pipeline_str = (
        f"v4l2src device={CAMERA_DEVICE} ! "
        "image/jpeg,width=640,height=480,framerate=30/1 ! "
        "jpegdec ! "
        "videoconvert ! "
        "tee name=t "
        # Display branch (leaky queue keeps latency bounded)
        "t. ! queue max-size-buffers=1 leaky=downstream ! "
        "videoconvert ! "
        "cairooverlay name=overlay ! "
        "videoconvert ! "
        "xvimagesink sync=false "
        # Detection branch → RGB 416x416 → appsink (drop frames, no backlog)
        "t. ! queue max-size-buffers=1 leaky=downstream ! "
        "videoconvert ! "
        "videoscale ! "
        f"video/x-raw,format=RGB,width={DETECTION_WIDTH},height={DETECTION_HEIGHT} ! "
        "appsink name=sink emit-signals=True max-buffers=1 drop=True"
    )

    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print("[PIPELINE] Created")
    except Exception as e:
        print(f"[PIPELINE] ERROR creating pipeline: {e}")
        return

    # Get elements
    overlay = pipeline.get_by_name('overlay')
    appsink = pipeline.get_by_name('sink')
    if not overlay or not appsink:
        print("[PIPELINE] ERROR: Could not get overlay/appsink")
        return

    # Create the GLib main loop BEFORE we start the pipeline,
    # so the bus handler can always call main_loop.quit().
    main_loop = GLib.MainLoop()

    # Bus watch BEFORE starting PLAYING (so we catch early errors)
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect('message', on_bus_message)

    # Connect draw callback (overlay)
    overlay.connect('draw', on_draw)

    # Start detection thread
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()

    # Start pipeline
    print("[MAIN] Starting pipeline...")
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("[MAIN] ERROR: Could not start pipeline")
        return

    # Optional: short delay to let things settle 
    time.sleep(2)
 

    # Run the main loop (Ctrl+C to exit)
    try:
        main_loop.run()
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping (Ctrl+C)...")
        running = False

    # Cleanup
    pipeline.set_state(Gst.State.NULL)
    print("[MAIN] Pipeline stopped")

    detection_thread.join(timeout=2)
    print("[MAIN] Detection thread stopped")


# Entry point guard: keep it, also good practice for Docker
if __name__ == "__main__":
    try:
        # Ensure model exists before building the pipeline
        if not os.path.exists(MODEL_PATH):
            print(f"\nERROR: Model file not found at: {MODEL_PATH}")
            sys.exit(1)

        # Build YOLO detector (Phase-1 ORT tuned)
        yolo_detector = YOLODetector(
            model_path=MODEL_PATH,
            input_size=DETECTION_WIDTH,
            conf_threshold=CONF_THRESHOLD
        )

        main()
    except Exception as e:
        print(f"\n{'!' * 70}")
        print(f"FATAL ERROR: {e}")
        print(f"{'!' * 70}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
