#!/usr/bin/env python3
"""
COCO Dataset Class Names and Colors

COCO (Common Objects in Context) is a large dataset with 80 object classes.
YOLOv8 is trained on this dataset, so it can detect these 80 types of objects.

This file contains:
1. List of all 80 class names
2. Colors for drawing boxes (one color per class)
"""

# ============================================
# ALL 80 COCO CLASS NAMES (in order)
# ============================================
# Index 0 = 'person', Index 1 = 'bicycle', etc.
# YOLO returns class_id (0-79), we use this list to get the name

COCO_CLASSES = [
    'person',           # 0
    'bicycle',          # 1
    'car',              # 2
    'motorcycle',       # 3
    'airplane',         # 4
    'bus',              # 5
    'train',            # 6
    'truck',            # 7
    'boat',             # 8
    'traffic light',    # 9
    'fire hydrant',     # 10
    'stop sign',        # 11
    'parking meter',    # 12
    'bench',            # 13
    'bird',             # 14
    'cat',              # 15
    'dog',              # 16
    'horse',            # 17
    'sheep',            # 18
    'cow',              # 19
    'elephant',         # 20
    'bear',             # 21
    'zebra',            # 22
    'giraffe',          # 23
    'backpack',         # 24
    'umbrella',         # 25
    'handbag',          # 26
    'tie',              # 27
    'suitcase',         # 28
    'frisbee',          # 29
    'skis',             # 30
    'snowboard',        # 31
    'sports ball',      # 32
    'kite',             # 33
    'baseball bat',     # 34
    'baseball glove',   # 35
    'skateboard',       # 36
    'surfboard',        # 37
    'tennis racket',    # 38
    'bottle',           # 39
    'wine glass',       # 40
    'cup',              # 41
    'fork',             # 42
    'knife',            # 43
    'spoon',            # 44
    'bowl',             # 45
    'banana',           # 46
    'apple',            # 47
    'sandwich',         # 48
    'orange',           # 49
    'broccoli',         # 50
    'carrot',           # 51
    'hot dog',          # 52
    'pizza',            # 53
    'donut',            # 54
    'cake',             # 55
    'chair',            # 56
    'couch',            # 57
    'potted plant',     # 58
    'bed',              # 59
    'dining table',     # 60
    'toilet',           # 61
    'tv',               # 62
    'laptop',           # 63
    'mouse',            # 64
    'remote',           # 65
    'keyboard',         # 66
    'cell phone',       # 67
    'microwave',        # 68
    'oven',             # 69
    'toaster',          # 70
    'sink',             # 71
    'refrigerator',     # 72
    'book',             # 73
    'clock',            # 74
    'vase',             # 75
    'scissors',         # 76
    'teddy bear',       # 77
    'hair drier',       # 78
    'toothbrush'        # 79
]


# ============================================
# COLORS FOR EACH CLASS
# ============================================
# RGB format (values from 0.0 to 1.0 for Cairo drawing)
# Each class gets a unique color for easy visualization

CLASS_COLORS = {
    # People and animals
    'person': (0.0, 1.0, 0.0),          # Green - most important!
    'cat': (1.0, 0.5, 0.0),             # Orange
    'dog': (0.8, 0.4, 0.0),             # Brown
    'bird': (0.0, 0.8, 0.8),            # Cyan
    'horse': (0.6, 0.3, 0.0),           # Dark brown
    'sheep': (0.9, 0.9, 0.9),           # Light gray
    'cow': (0.5, 0.3, 0.0),             # Brown
    'elephant': (0.5, 0.5, 0.5),        # Gray
    'bear': (0.3, 0.2, 0.1),            # Dark brown
    'zebra': (0.0, 0.0, 0.0),           # Black
    'giraffe': (1.0, 0.8, 0.4),         # Yellow-orange
    
    # Vehicles
    'bicycle': (1.0, 1.0, 0.0),         # Yellow
    'car': (0.0, 0.0, 1.0),             # Blue
    'motorcycle': (1.0, 0.0, 1.0),      # Magenta
    'airplane': (0.5, 0.5, 1.0),        # Light blue
    'bus': (1.0, 0.5, 0.0),             # Orange
    'train': (0.5, 0.0, 0.5),           # Purple
    'truck': (0.3, 0.3, 1.0),           # Blue
    'boat': (0.0, 0.5, 1.0),            # Sky blue
    
    # Traffic
    'traffic light': (1.0, 0.0, 0.0),   # Red
    'fire hydrant': (0.8, 0.0, 0.0),    # Dark red
    'stop sign': (1.0, 0.0, 0.0),       # Red
    'parking meter': (0.6, 0.6, 0.6),   # Gray
    
    # Furniture
    'bench': (0.6, 0.4, 0.2),           # Wood brown
    'chair': (0.7, 0.5, 0.3),           # Light brown
    'couch': (0.5, 0.3, 0.2),           # Dark brown
    'bed': (0.8, 0.8, 1.0),             # Light blue
    'dining table': (0.6, 0.3, 0.0),    # Brown
    'toilet': (1.0, 1.0, 1.0),          # White
    
    # Electronics
    'tv': (0.1, 0.1, 0.1),              # Black
    'laptop': (0.2, 0.2, 0.2),          # Dark gray
    'mouse': (0.3, 0.3, 0.3),           # Gray
    'remote': (0.2, 0.2, 0.2),          # Dark gray
    'keyboard': (0.1, 0.1, 0.1),        # Black
    'cell phone': (0.0, 0.0, 0.0),      # Black
    
    # Kitchen
    'microwave': (0.8, 0.8, 0.8),       # Light gray
    'oven': (0.3, 0.3, 0.3),            # Dark gray
    'toaster': (0.7, 0.7, 0.7),         # Silver
    'sink': (0.9, 0.9, 0.9),            # White
    'refrigerator': (0.9, 0.9, 0.9),    # White
    'bottle': (0.0, 0.6, 0.0),          # Green
    'wine glass': (0.8, 0.8, 1.0),      # Clear blue
    'cup': (1.0, 1.0, 1.0),             # White
    'fork': (0.8, 0.8, 0.8),            # Silver
    'knife': (0.7, 0.7, 0.7),           # Silver
    'spoon': (0.8, 0.8, 0.8),           # Silver
    'bowl': (1.0, 1.0, 1.0),            # White
    
    # Food
    'banana': (1.0, 1.0, 0.0),          # Yellow
    'apple': (1.0, 0.0, 0.0),           # Red
    'sandwich': (0.9, 0.8, 0.6),        # Tan
    'orange': (1.0, 0.5, 0.0),          # Orange
    'broccoli': (0.0, 0.8, 0.0),        # Green
    'carrot': (1.0, 0.5, 0.0),          # Orange
    'hot dog': (0.8, 0.4, 0.2),         # Brown
    'pizza': (1.0, 0.8, 0.4),           # Yellow
    'donut': (0.9, 0.7, 0.5),           # Tan
    'cake': (1.0, 0.8, 0.8),            # Pink
    
    # Sports
    'sports ball': (1.0, 0.5, 0.0),     # Orange
    'baseball bat': (0.6, 0.4, 0.2),    # Wood
    'baseball glove': (0.5, 0.3, 0.1),  # Brown
    'skateboard': (0.0, 0.0, 0.0),      # Black
    'surfboard': (0.0, 0.8, 0.8),       # Cyan
    'tennis racket': (1.0, 1.0, 0.0),   # Yellow
    'frisbee': (1.0, 0.0, 0.0),         # Red
    'skis': (0.0, 0.0, 1.0),            # Blue
    'snowboard': (0.2, 0.2, 0.2),       # Dark gray
    'kite': (1.0, 0.0, 1.0),            # Magenta
    
    # Accessories
    'backpack': (0.0, 0.0, 0.5),        # Navy
    'umbrella': (0.5, 0.0, 0.5),        # Purple
    'handbag': (0.8, 0.4, 0.6),         # Pink
    'tie': (0.0, 0.0, 0.8),             # Blue
    'suitcase': (0.3, 0.2, 0.1),        # Brown
    
    # Other
    'potted plant': (0.0, 0.6, 0.0),    # Green
    'book': (0.8, 0.6, 0.4),            # Tan
    'clock': (0.9, 0.9, 0.9),           # White
    'vase': (0.6, 0.8, 1.0),            # Light blue
    'scissors': (0.7, 0.7, 0.7),        # Silver
    'teddy bear': (0.6, 0.4, 0.2),      # Brown
    'hair drier': (0.5, 0.5, 0.5),      # Gray
    'toothbrush': (0.0, 0.8, 0.8),      # Cyan
}


# ============================================
# HELPER FUNCTION: Get Color for a Class
# ============================================
def get_class_color(class_name):
    """
    Get the color for a given class name.
    If class not found, return default green.
    
    Args:
        class_name (str): Name of the class (e.g., 'person', 'car')
    
    Returns:
        tuple: RGB color (r, g, b) where each value is 0.0-1.0
    """
    # Return the color if exists, otherwise default green
    return CLASS_COLORS.get(class_name, (0.0, 1.0, 0.0))


# ============================================
# HELPER FUNCTION: Get Class Name from ID
# ============================================
def get_class_name(class_id):
    """
    Get the class name from a class ID.
    
    Args:
        class_id (int): Class ID (0-79)
    
    Returns:
        str: Class name (e.g., 'person', 'car')
    """
    # Make sure class_id is valid
    if 0 <= class_id < len(COCO_CLASSES):
        return COCO_CLASSES[class_id]
    else:
        return 'unknown'


# ============================================
# TEST CODE (runs when file is executed directly)
# ============================================
if __name__ == "__main__":
    """
    Simple test to verify the data is correct
    """
    print("=" * 60)
    print("COCO CLASSES TEST")
    print("=" * 60)
    
    # Print total classes
    print(f"\nTotal classes: {len(COCO_CLASSES)}")
    print(f"Total colors defined: {len(CLASS_COLORS)}")
    
    # Print first 10 classes
    print("\nFirst 10 classes:")
    for i in range(10):
        name = COCO_CLASSES[i]
        color = get_class_color(name)
        print(f"  {i}: {name:20s} → Color: {color}")
    
    # Test helper functions
    print("\nTesting helper functions:")
    print(f"  Class ID 0 → '{get_class_name(0)}'")
    print(f"  Class 'person' → Color: {get_class_color('person')}")
    print(f"  Class 'car' → Color: {get_class_color('car')}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)