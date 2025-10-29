"""
Export YOLOv8n to ONNX for Raspberry Pi 5 (CPU + ONNX Runtime)
Produces: inbox/yolov8n_416_nms_fp32.onnx

Optimizations included (each explained inline):
- opset=12           → maximum ARM/ORT compatibility; avoids slow fallbacks
- imgsz=416          → fixed 416×416 (static shape) for faster ORT optimization
- batch=1            → static batch for simpler, faster graph on CPU
- nms=True           → fuse NMS inside the graph (C++ in ORT → no Python NMS)
- conf=0.50          → your chosen score threshold baked into NMS
- iou=0.45           → typical IoU threshold for NMS (adjust later if needed)
- simplify=True      → ONNX graph simplification (removes redundant ops)

Notes:
- This exports **FP32** (full precision). Run INT8 PTQ later as a separate step.
- We keep only the NMS-fused file (no raw backup).
"""

import os
from pathlib import Path
from ultralytics import YOLO


# Model weights to start from 
# Change this to use different models 
# YOLO8n -> yolov8n.pt ,  YOLO10n -> yolov10n.pt ,YOLO11n -> yolo11n.pt
# YOLO8s -> yolov8s.pt ,  YOLO10s -> yolov10s.pt ,YOLO11s -> yolo11s.pt
WEIGHTS = "yolov8s.pt"

# --- Load model ---------------------------------------------------------------
# Loads Ultralytics YOLOv8n in Python (PyTorch under the hood)
model = YOLO(WEIGHTS)

# --- Export knobs (Pi-5 friendly) --------------------------------------------
IMGSZ = 416      # Static 416×416: sweet-spot for ~25–30 FPS on Pi 5 CPU
OPSET = 12       # Broadly supported by ONNX Runtime builds on ARM
BATCH = 1        # Static batch avoids dynamic shape overhead on CPU

# NMS thresholds baked into the graph (industrial style: fixed at export)
CONF_THRES = 0.50   # Confidence threshold
IOU_THRES  = 0.45   # Typical NMS IoU; tune offline if needed, then re-export

# --- Export to ONNX (single artifact) ----------------------------------------
# Key switches explained:
# - format="onnx": export to ONNX IR for portable, fast inference on ORT.
# - opset=12: ensures operators match what Pi-side ORT optimizes well.
# - imgsz=416: fixes input to [1,3,416,416]; ORT can pre-plan/fuse ops better.
# - batch=1: locks batch dimension; simpler model, less overhead on CPU.
# - nms=True: fuses Non-Max Suppression IN the graph; no Python NMS on Pi.
# - conf / iou: baked into NMS node; deterministic outputs & stable latency.
# - simplify=True: runs ONNX simplifier to remove redundant ops & constants.
# - dynamic=False: implied by fixed imgsz & batch; keeps shapes static.
exported_path = model.export(
    format="onnx",
    opset=OPSET,
    imgsz=IMGSZ,
    batch=BATCH,
    nms=True,
    conf=CONF_THRES,
    iou=IOU_THRES,
    simplify=True,
    dynamic=False,
)
 