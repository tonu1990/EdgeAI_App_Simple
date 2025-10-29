#!/usr/bin/env python3
"""
YOLO Detector for NMS-Baked Models

This is a SIMPLIFIED version specifically for YOLO models exported with nms=True.

Your model format:
- Input: [1, 3, 416, 416] - RGB image
- Output: [1, 300, 6] - NMS already applied
- Each detection: [x1, y1, x2, y2, confidence, class_id]

BEGINNER NOTE:
This detector is simpler because the model already did the hard work (NMS).
We just need to:
1. Preprocess frames (normalize)
2. Run inference
3. Convert coordinates and filter by confidence
"""

import numpy as np
import onnxruntime as ort
import os
from coco_classes import COCO_CLASSES, get_class_name


class YOLODetectorNMS:
    """
    YOLO Object Detector for NMS-Baked Models (nms=True)
    
    Simplified detector for models that have NMS built-in.
    Much faster and simpler than standard YOLO post-processing!
    """
    
    def __init__(self, model_path, input_size=416, conf_threshold=0.5):
        """
        Initialize the YOLO detector
        
        Args:
            model_path (str): Path to ONNX model file
            input_size (int): Model input size (must match export: 416)
            conf_threshold (float): Confidence threshold (0.0-1.0)
        """
        print("\n" + "=" * 60)
        print("YOLO DETECTOR (NMS-BAKED MODEL)")
        print("=" * 60)
        
        # Store configuration
        self.model_path = model_path
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        
        # Will be set when model is loaded
        self.session = None
        self.input_name = None
        self.output_name = None
        
        # Pre-allocate input array for faster preprocessing
        # Shape: (1, 3, input_size, input_size)
        self.input_array = np.zeros((1, 3, input_size, input_size), dtype=np.float32)
        
        print(f"Configuration:")
        print(f"  Model path: {model_path}")
        print(f"  Input size: {input_size}x{input_size}")
        print(f"  Confidence threshold: {conf_threshold}")
        print(f"  Model type: NMS-baked (nms=True)")
        
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
        
        # Enable all graph optimizations
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Use all CPU cores (Raspberry Pi 5 has 4 cores)
        session_options.intra_op_num_threads = 4
        session_options.inter_op_num_threads = 4
        
        print(f"  Loading model with ONNX Runtime...")
        
        try:
            # Create the inference session
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=session_options,
                providers=['CPUExecutionProvider']
            )
            print(f"  ✓ Model loaded successfully")
        
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
        
        # Get input and output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
        # Get shapes
        input_shape = self.session.get_inputs()[0].shape
        output_shape = self.session.get_outputs()[0].shape
        
        print(f"\n[MODEL INFO]")
        print(f"  Input name: {self.input_name}")
        print(f"  Input shape: {input_shape}")
        print(f"  Output name: {self.output_name}")
        print(f"  Output shape: {output_shape}")
        
        # Validate output shape
        if len(output_shape) != 3 or output_shape[2] != 6:
            print(f"\n  ⚠ WARNING: Expected output shape [1, N, 6], got {output_shape}")
            print(f"  This detector is designed for NMS-baked models (nms=True)")
            print(f"  Your model might use a different format!")
        else:
            print(f"  ✓ Output format confirmed: [1, {output_shape[1]}, 6] (NMS-baked)")
        
        print(f"  Number of classes: {len(COCO_CLASSES)}")
        
        print("\n" + "=" * 60)
        print("YOLO DETECTOR READY!")
        print("=" * 60 + "\n")
    
    
    def preprocess(self, frame):
        """
        Preprocess a frame for YOLO inference
        
        Input: numpy array (H, W, 3) with values 0-255 (uint8)
        Output: numpy array (1, 3, H, W) with values 0.0-1.0 (float32)
        
        Args:
            frame (np.ndarray): Input frame (H, W, 3) uint8 RGB
        
        Returns:
            np.ndarray: Preprocessed array (1, 3, H, W) float32
        """
        # Normalize each channel (divide by 255) and place in correct position
        # This is FAST because we pre-allocated input_array
        self.input_array[0, 0, :, :] = frame[:, :, 0] / 255.0  # R channel
        self.input_array[0, 1, :, :] = frame[:, :, 1] / 255.0  # G channel
        self.input_array[0, 2, :, :] = frame[:, :, 2] / 255.0  # B channel
        
        return self.input_array
    
    
    def postprocess(self, predictions):
        """
        Post-process YOLO predictions for NMS-baked models
        
        Input format: [1, N, 6] where N is max detections (usually 300)
        Each detection: [x1, y1, x2, y2, confidence, class_id]
        
        - x1, y1: Top-left corner coordinates
        - x2, y2: Bottom-right corner coordinates  
        - confidence: Detection confidence (0.0-1.0)
        - class_id: COCO class ID (0-79)
        
        Since NMS is already done by the model, we just:
        1. Filter by confidence threshold
        2. Convert coordinates from corner to center format
        3. Validate and return detections
        
        Args:
            predictions (np.ndarray): Raw model output [1, N, 6]
        
        Returns:
            list: List of detections [{x, y, w, h, class_id, class_name, confidence}, ...]
        """
        # Remove batch dimension: (1, N, 6) -> (N, 6)
        predictions = predictions[0]
        
        detections = []
        
        # Process each detection
        for pred in predictions:
            # Unpack the detection
            x1, y1, x2, y2, confidence, class_id = pred
            
            # FILTER 1: Confidence threshold
            if confidence < self.conf_threshold:
                continue
            
            # FILTER 2: Valid class ID
            class_id = int(class_id)
            if class_id < 0 or class_id >= len(COCO_CLASSES):
                continue
            
            # FILTER 3: Valid box dimensions
            width = x2 - x1
            height = y2 - y1
            
            if width <= 0 or height <= 0:
                continue
            
            # Convert from corner format (x1,y1,x2,y2) to:
            # Drawing format: (x_topleft, y_topleft, width, height)
            x_topleft = float(x1)
            y_topleft = float(y1)
            
            # Create detection dictionary
            detection = {
                'x': x_topleft,
                'y': y_topleft,
                'w': float(width),
                'h': float(height),
                'class_id': class_id,
                'class_name': get_class_name(class_id),
                'confidence': float(confidence)
            }
            
            detections.append(detection)
        
        return detections
    
    
    def detect(self, frame):
        """
        Main detection method - THE ONLY METHOD YOU NEED TO CALL!
        
        This runs the complete pipeline:
        1. Preprocess frame
        2. Run ONNX inference
        3. Post-process results
        
        Args:
            frame (np.ndarray): Input frame (H, W, 3) uint8 RGB
        
        Returns:
            list: List of detections with coordinates ready for drawing
        
        Example:
            detections = detector.detect(frame)
            for det in detections:
                x, y, w, h = det['x'], det['y'], det['w'], det['h']
                label = f"{det['class_name']}: {det['confidence']:.2f}"
                # Draw box and label...
        """
        # STEP 1: Preprocess
        input_data = self.preprocess(frame)
        
        # STEP 2: Run inference
        predictions = self.session.run(
            [self.output_name],
            {self.input_name: input_data}
        )[0]
        
        # STEP 3: Post-process
        detections = self.postprocess(predictions)
        
        return detections
    
    
    def get_stats(self):
        """
        Get detector statistics and info
        
        Returns:
            dict: Detector information
        """
        return {
            'model_path': self.model_path,
            'input_size': self.input_size,
            'conf_threshold': self.conf_threshold,
            'model_type': 'NMS-baked (nms=True)',
            'num_classes': len(COCO_CLASSES),
            'input_shape': self.session.get_inputs()[0].shape,
            'output_shape': self.session.get_outputs()[0].shape
        }
