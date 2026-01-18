"""
Hybrid Vision Architecture - Usage Example

This script demonstrates how to use the hybrid scanner that combines
Windows Accessibility API with visual object detection.
"""

from src.vision.scanner import UIScanner, HybridScanner, VisualDetector
from src.vision.capture import ScreenCapture
from PIL import Image


def example_api_only():
    """Example 1: Traditional API-only scanning (current default)"""
    print("=" * 80)
    print("EXAMPLE 1: API-Only Scanning (Current Default)")
    print("=" * 80)
    
    # Initialize API-only scanner
    scanner = UIScanner()
    
    # Scan active window
    elements = scanner.scan_active_window()
    
    print(f"✅ Found {len(elements)} elements via API")
    scanner.print_elements(elements)
    
    # Capture screen and visualize
    with ScreenCapture() as capture:
        screenshot = capture.capture()
        
        # Draw overlay (green boxes for API elements)
        annotated = scanner.draw_ui_overlay(screenshot, elements)
        annotated.save("output_api_only.png")
        print("\n💾 Saved visualization: output_api_only.png")


def example_hybrid_mode():
    """Example 2: Hybrid mode (API + Vision) - requires model"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Hybrid Mode (API + Vision)")
    print("=" * 80)
    
    # Initialize hybrid scanner
    # Note: This will use API-only if no model is provided
    scanner = HybridScanner(
        enable_visual=True,
        model_path=None,  # Set to your model path when available
        iou_threshold=0.5  # 50% overlap = duplicate
    )
    
    # Capture screenshot for visual detection
    with ScreenCapture() as capture:
        screenshot = capture.capture()
    
    # Perform hybrid scan
    elements = scanner.scan(screenshot, detect_icons=True)
    
    print(f"✅ Found {len(elements)} total elements")
    
    # Count by source
    api_count = sum(1 for e in elements if e.get('source') == 'api')
    vision_count = sum(1 for e in elements if e.get('source') == 'vision')
    
    print(f"   - API elements: {api_count}")
    print(f"   - Vision elements: {vision_count}")
    
    # Draw overlay with different colors for each source
    annotated = scanner.ui_scanner.draw_ui_overlay(
        screenshot,
        elements,
        api_color=(0, 255, 0),      # Green for API
        vision_color=(255, 165, 0)   # Orange for Vision
    )
    annotated.save("output_hybrid.png")
    print("\n💾 Saved visualization: output_hybrid.png")
    print("   - Green boxes = API-detected elements")
    print("   - Orange boxes = Vision-detected elements")


def example_icon_detection():
    """Example 3: Specific icon detection for unlabeled elements"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Icon Detection (for unlabeled elements)")
    print("=" * 80)
    
    scanner = HybridScanner(
        enable_visual=True,
        model_path=None  # Set when model available
    )
    
    # Capture screenshot
    with ScreenCapture() as capture:
        screenshot = capture.capture()
    
    # Detect specific icon types
    target_icons = [
        'hamburger_menu',
        'close_button',
        'search_icon',
        'more_options'
    ]
    
    icons = scanner.detect_unlabeled_icons(screenshot, icon_types=target_icons)
    
    print(f"✅ Found {len(icons)} unlabeled icons")
    
    # Group by icon type
    icon_types = {}
    for icon in icons:
        icon_type = icon.get('icon_type', 'unknown')
        icon_types[icon_type] = icon_types.get(icon_type, 0) + 1
    
    for icon_type, count in icon_types.items():
        print(f"   - {icon_type}: {count}")


def example_iou_merging():
    """Example 4: Understanding IoU-based merging"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: IoU-Based Element Merging")
    print("=" * 80)
    
    scanner = HybridScanner(iou_threshold=0.5)
    
    # Demonstrate IoU calculation
    rect1 = (100, 100, 50, 50)  # x, y, width, height
    rect2 = (125, 125, 50, 50)  # Overlapping rectangle
    rect3 = (200, 200, 50, 50)  # Non-overlapping rectangle
    
    iou_overlap = scanner._calculate_iou(rect1, rect2)
    iou_separate = scanner._calculate_iou(rect1, rect3)
    
    print(f"IoU between overlapping rectangles: {iou_overlap:.3f}")
    print(f"IoU between separate rectangles: {iou_separate:.3f}")
    print(f"\nWith threshold {scanner.iou_threshold}:")
    print(f"  - Overlapping elements (IoU={iou_overlap:.3f}) → Merged ✅")
    print(f"  - Separate elements (IoU={iou_separate:.3f}) → Keep both ✅")


def example_model_integration_guide():
    """Example 5: Guide for integrating actual detection models"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Model Integration Guide")
    print("=" * 80)
    
    print("""
To integrate a real visual detection model, follow these steps:

1. INSTALL MODEL DEPENDENCIES
   For YOLO (Ultralytics):
   >>> pip install ultralytics torch torchvision

   For ONNX Runtime:
   >>> pip install onnxruntime opencv-python

2. TRAIN OR DOWNLOAD MODEL
   - Train custom UI detector on your dataset
   - Or use pre-trained models:
     * OmniParser: https://github.com/microsoft/OmniParser
     * YOLO: https://github.com/ultralytics/ultralytics

3. MODIFY VisualDetector CLASS
   Update src/vision/scanner.py:

   # In _load_model():
   from ultralytics import YOLO
   self.model = YOLO(model_path)

   # In detect_elements():
   results = self.model(image, conf=self.confidence_threshold)
   for detection in results[0].boxes:
       # Extract bounding box, confidence, class
       # Create element dict
       # Return list

4. USE HYBRID SCANNER
   scanner = HybridScanner(
       enable_visual=True,
       model_path="path/to/model.pt"
   )
   elements = scanner.scan(screenshot)

RECOMMENDED MODELS:
- OmniParser: Pre-trained on UI elements
- YOLOv8: Fast, accurate, easy to train
- Faster R-CNN: Higher accuracy, slower
- DETR: Transformer-based detection
    """)


if __name__ == "__main__":
    # Run examples
    print("\n🔬 HYBRID VISION ARCHITECTURE - EXAMPLES\n")
    
    try:
        # Example 1: Current default behavior (API-only)
        example_api_only()
        
        # Example 2: Hybrid mode (will use API-only until model loaded)
        example_hybrid_mode()
        
        # Example 3: Icon detection
        example_icon_detection()
        
        # Example 4: IoU merging demonstration
        example_iou_merging()
        
        # Example 5: Model integration guide
        example_model_integration_guide()
        
        print("\n" + "=" * 80)
        print("✅ All examples completed!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Note: Some examples require an active window to scan.")
