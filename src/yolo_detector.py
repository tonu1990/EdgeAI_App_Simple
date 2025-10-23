#!/usr/bin/env python3
"""
YOLO Detector Class

This file contains the YOLODetector class which handles:
1. Loading the ONNX model
2. Preprocessing frames
3. Running inference
4. Post-processing results (NMS, filtering)

BEGINNER NOTE:
Think of this class as a "YOLO machine" - you feed it a frame,
it gives you back detected objects with bounding boxes.
"""

import numpy as np
import onnxruntime as ort
import cv2
import os
from coco_classes import COCO_CLASSES, get_class_name


class YOLODetector:
    """
    YOLO Object Detector using ONNX Runtime
    
    This class wraps all YOLO functionality in one place.
    """
    
    def __init__(self, model_path, input_size=416, conf_threshold=0.65, nms_threshold=0.45):
        """
        Initialize the YOLO detector
        
        Args:
            model_path (str): Path to ONNX model file
            input_size (int): Model input size (416 or 640)
            conf_threshold (float): Confidence threshold (0.0-1.0)
            nms_threshold (float): NMS IoU threshold (0.0-1.0)
        """
        print("\n" + "=" * 60)
        print("YOLO DETECTOR INITIALIZATION")
        print("=" * 60)
        
        # Store configuration
        self.model_path = model_path
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        
        # Will be set when model is loaded
        self.session = None
        self.input_name = None
        self.output_name = None
        
        # Pre-allocate input array for faster preprocessing
        # Shape: (1, 3, input_size, input_size)
        # Batch=1, Channels=3 (RGB), Height=input_size, Width=input_size
        self.input_array = np.zeros((1, 3, input_size, input_size), dtype=np.float32)
        
        print(f"Configuration:")
        print(f"  Model path: {model_path}")
        print(f"  Input size: {input_size}x{input_size}")
        print(f"  Confidence threshold: {conf_threshold}")
        print(f"  NMS threshold: {nms_threshold}")
        
        # Load the model
        self.load_model()
    
    
    def load_model(self):
        """
        Load the ONNX model and validate it
        """
        print(f"\n[LOADING MODEL]")
        
        # Check if model file exists
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        print(f"  ✓ Model file exists")
        
        # Create ONNX Runtime session with optimizations
        session_options = ort.SessionOptions()
        
        # OPTIMIZATION 1: Enable all graph optimizations
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # OPTIMIZATION 2: Use all CPU cores (Raspberry Pi 5 has 4 cores)
        session_options.intra_op_num_threads = 4
        session_options.inter_op_num_threads = 4
        
        print(f"  Loading model with ONNX Runtime...")
        
        try:
            # Create the inference session
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=session_options,
                providers=['CPUExecutionProvider']  # Use CPU (no GPU on Pi)
            )
            print(f"  ✓ Model loaded successfully")
        
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
        
        # Get input and output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        # Get input shape to verify
        input_shape = self.session.get_inputs()[0].shape
        output_shape = self.session.get_outputs()[0].shape
        
        print(f"\n[MODEL INFO]")
        print(f"  Input name: {self.input_name}")
        print(f"  Input shape: {input_shape}")
        print(f"  Output name: {self.output_name}")
        print(f"  Output shape: {output_shape}")
        print(f"  Number of classes: {len(COCO_CLASSES)}")
        
        print("\n" + "=" * 60)
        print("YOLO DETECTOR READY!")
        print("=" * 60 + "\n")
    
    
    def preprocess(self, frame):
        """
        Preprocess a frame for YOLO inference
        
        STEPS:
        1. Frame comes in as numpy array (H, W, 3) with values 0-255
        2. Normalize: divide by 255.0 → values become 0.0-1.0
        3. Transpose: (H, W, C) → (C, H, W) - YOLO wants channels first
        4. Already have batch dimension in self.input_array
        
        Args:
            frame (np.ndarray): Input frame (H, W, 3) uint8 RGB
        
        Returns:
            np.ndarray: Preprocessed array (1, 3, H, W) float32
        """
        # Normalize and transpose in one go (efficient!)
        # Extract each color channel, normalize, and place in input_array
        self.input_array[0, 0, :, :] = frame[:, :, 0] / 255.0  # R channel
        self.input_array[0, 1, :, :] = frame[:, :, 1] / 255.0  # G channel
        self.input_array[0, 2, :, :] = frame[:, :, 2] / 255.0  # B channel
        
        return self.input_array
    
    
    def postprocess(self, predictions):
        """
        Post-process YOLO predictions
        
        YOLO OUTPUT FORMAT (YOLOv8):
        - Shape: (1, 84, 8400)
        - 84 = 4 (bbox: x, y, w, h) + 80 (class scores)
        - 8400 = number of predictions
        
        STEPS:
        1. Remove batch dimension: (1, 84, 8400) → (84, 8400)
        2. Transpose: (84, 8400) → (8400, 84)
        3. Split: boxes (8400, 4) and scores (8400, 80)
        4. Get max score and class for each prediction
        5. Filter by confidence threshold
        6. Apply NMS to remove duplicates
        
        Args:
            predictions (np.ndarray): Raw model output (1, 84, 8400)
        
        Returns:
            list: List of detections [{x, y, w, h, class_id, class_name, confidence}, ...]
        """
        # Step 1 & 2: Remove batch and transpose
        predictions = predictions[0].T  # (8400, 84)
        
        # Step 3: Split boxes and scores
        boxes = predictions[:, :4]      # (8400, 4) - x, y, w, h
        scores = predictions[:, 4:]     # (8400, 80) - class scores
        
        # Step 4: Get max class score and class ID for each prediction
        class_ids = np.argmax(scores, axis=1)           # (8400,)
        confidences = np.max(scores, axis=1)            # (8400,)
        
        # Step 5: Filter by confidence threshold
        mask = confidences > self.conf_threshold
        filtered_boxes = boxes[mask]
        filtered_class_ids = class_ids[mask]
        filtered_confidences = confidences[mask]
        
        # If no detections, return empty list
        if len(filtered_boxes) == 0:
            return []
        
        # Step 6: Apply NMS (Non-Maximum Suppression)
        # Convert from center format (x, y, w, h) to corner format (x1, y1, x2, y2)
        boxes_xyxy = self.xywh_to_xyxy(filtered_boxes)
        
        # Run NMS
        keep_indices = self.non_max_suppression(boxes_xyxy, filtered_confidences)
        
        # Build final detection list
        detections = []
        for idx in keep_indices:
            x, y, w, h = filtered_boxes[idx]
            class_id = int(filtered_class_ids[idx])
            confidence = float(filtered_confidences[idx])
            
            detections.append({
                'x': float(x),
                'y': float(y),
                'w': float(w),
                'h': float(h),
                'class_id': class_id,
                'class_name': get_class_name(class_id),
                'confidence': confidence
            })
        
        return detections
    
    
    def xywh_to_xyxy(self, boxes):
        """
        Convert boxes from center format to corner format
        
        YOLO format (xywh): [x_center, y_center, width, height]
        Corner format (xyxy): [x1, y1, x2, y2] (top-left, bottom-right)
        
        Args:
            boxes (np.ndarray): Boxes in xywh format (N, 4)
        
        Returns:
            np.ndarray: Boxes in xyxy format (N, 4)
        """
        boxes_xyxy = np.copy(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1 = x_center - width/2
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1 = y_center - height/2
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2 = x_center + width/2
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2 = y_center + height/2
        return boxes_xyxy
    
    
    def non_max_suppression(self, boxes, scores):
        """
        Non-Maximum Suppression (NMS) - Remove duplicate/overlapping boxes
        
        ALGORITHM:
        1. Sort boxes by confidence (highest first)
        2. Keep the highest confidence box
        3. Remove all boxes that overlap too much (IoU > threshold)
        4. Repeat for remaining boxes
        
        Uses OpenCV's built-in NMS for speed
        
        Args:
            boxes (np.ndarray): Boxes in xyxy format (N, 4)
            scores (np.ndarray): Confidence scores (N,)
        
        Returns:
            list: Indices of boxes to keep
        """
        # OpenCV NMS expects float32
        boxes = boxes.astype(np.float32)
        scores = scores.astype(np.float32)
        
        # Run NMS
        indices = cv2.dnn.NMSBoxes(
            bboxes=boxes.tolist(),
            scores=scores.tolist(),
            score_threshold=self.conf_threshold,
            nms_threshold=self.nms_threshold
        )
        
        # OpenCV returns indices in a specific format, flatten it
        if len(indices) > 0:
            return indices.flatten().tolist()
        else:
            return []
    
    
    def detect(self, frame):
        """
        Main detection method - call this to detect objects in a frame
        
        This is the only method you need to call from outside!
        
        Args:
            frame (np.ndarray): Input frame (H, W, 3) uint8 RGB
        
        Returns:
            list: List of detections with scaled coordinates
        """
        # Step 1: Preprocess
        input_data = self.preprocess(frame)
        
        # Step 2: Run inference
        predictions = self.session.run(
            [self.output_name],
            {self.input_name: input_data}
        )[0]
        
        # Step 3: Post-process
        detections = self.postprocess(predictions)
        
        return detections


# ============================================
# TEST CODE
# ============================================
if __name__ == "__main__":
    """
    Test the YOLODetector with a dummy frame
    This helps verify the model loading works
    """
    import sys
    
    print("\n" + "=" * 60)
    print("YOLO DETECTOR TEST")
    print("=" * 60)
    
    # Check if model path provided
    if len(sys.argv) < 2:
        print("\nUsage: python3 yolo_detector.py /path/to/model.onnx")
        print("\nExample:")
        print("  python3 yolo_detector.py /models/current.onnx")
        sys.exit(1)
    
    model_path = sys.argv[1]
    
    try:
        # Create detector
        detector = YOLODetector(
            model_path=model_path,
            input_size=416,
            conf_threshold=0.5
        )
        
        # Create a dummy frame (random noise)
        print("\n[TEST] Creating dummy frame...")
        dummy_frame = np.random.randint(0, 255, (416, 416, 3), dtype=np.uint8)
        print(f"  Frame shape: {dummy_frame.shape}")
        
        # Run detection
        print("\n[TEST] Running detection on dummy frame...")
        detections = detector.detect(dummy_frame)
        
        print(f"\n[RESULT] Found {len(detections)} objects")
        for i, det in enumerate(detections):
            print(f"  {i+1}. {det['class_name']}: {det['confidence']:.2f}")
        
        print("\n" + "=" * 60)
        print("TEST PASSED! ✓")
        print("=" * 60 + "\n")
    
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)