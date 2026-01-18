"""
UI Tree Scanner Module
Hybrid vision architecture combining Windows Accessibility API and visual object detection.
"""

from typing import List, Dict, Tuple, Optional, Any
import uiautomation as auto
from PIL import Image, ImageDraw, ImageFont
import time
import numpy as np


class UIScannerError(Exception):
    """Exception raised when UI scanning fails."""
    pass


class VisualDetector:
    """
    Visual object detection for UI elements using computer vision models.
    
    This class provides a placeholder/interface for integrating local detection
    models like OmniParser, YOLO, or other visual recognition systems to detect
    UI elements that may lack accessibility labels.
    
    Attributes:
        model: The loaded detection model (placeholder for future integration).
        confidence_threshold: Minimum confidence score for detections.
        icon_categories: Categories of UI icons to detect.
    """
    
    # Common UI icon types to detect
    ICON_CATEGORIES = {
        'hamburger_menu': 'Three horizontal lines menu icon',
        'close_button': 'X or close icon',
        'back_button': 'Left arrow or back icon',
        'forward_button': 'Right arrow or forward icon',
        'search_icon': 'Magnifying glass icon',
        'settings_icon': 'Gear or cog icon',
        'profile_icon': 'User silhouette icon',
        'notification_icon': 'Bell icon',
        'home_icon': 'House icon',
        'share_icon': 'Share/export icon',
        'like_button': 'Heart or thumbs up icon',
        'comment_icon': 'Speech bubble icon',
        'more_options': 'Three dots (vertical or horizontal)',
        'download_icon': 'Download arrow icon',
        'upload_icon': 'Upload arrow icon',
    }
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.5
    ) -> None:
        """
        Initialize the Visual Detector.
        
        Args:
            model_path: Path to the detection model weights (optional).
            confidence_threshold: Minimum confidence for detections (0.0-1.0).
        
        Note:
            This is a placeholder implementation. To integrate a real model:
            1. Install model dependencies (e.g., ultralytics, torch, onnxruntime)
            2. Load model weights in __init__
            3. Implement actual detection in detect_elements()
        
        Example:
            >>> detector = VisualDetector(confidence_threshold=0.6)
            >>> # Future: detector = VisualDetector("models/ui_detector.pt")
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None  # Placeholder for model instance
        self.icon_categories = self.ICON_CATEGORIES
        
        # Future integration point
        if model_path:
            self._load_model(model_path)
    
    def _load_model(self, model_path: str) -> None:
        """
        Load the visual detection model.
        
        Args:
            model_path: Path to model weights.
        
        Note:
            Placeholder for future model loading logic.
            Example implementations:
            - YOLO: self.model = YOLO(model_path)
            - OmniParser: self.model = OmniParser.load(model_path)
            - ONNX Runtime: self.model = ort.InferenceSession(model_path)
        """
        # TODO: Implement model loading
        # Example for YOLO:
        # from ultralytics import YOLO
        # self.model = YOLO(model_path)
        print(f"⚠️  Visual detection model loading not yet implemented")
        print(f"   Model path: {model_path}")
    
    def detect_elements(
        self,
        image: Image.Image,
        detect_icons: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Detect UI elements in an image using computer vision.
        
        Args:
            image: PIL Image to analyze.
            detect_icons: Whether to specifically detect icon elements.
        
        Returns:
            List of detected elements with structure:
            {
                'source': 'vision',
                'type': str,           # 'button', 'icon', 'text_field', etc.
                'icon_type': str,      # Icon category if applicable
                'rect': (x, y, w, h),  # Bounding box
                'center': (x, y),      # Center coordinates
                'confidence': float,   # Detection confidence (0.0-1.0)
                'name': str            # Inferred name/description
            }
        
        Note:
            This is a placeholder. Real implementation would:
            1. Preprocess image for model input
            2. Run inference
            3. Post-process detections
            4. Filter by confidence threshold
        
        Example:
            >>> detector = VisualDetector()
            >>> screenshot = Image.open("screen.png")
            >>> elements = detector.detect_elements(screenshot)
        """
        # Placeholder implementation
        # In production, this would use the loaded model for detection
        
        if self.model is None:
            # Return empty list if no model loaded
            return []
        
        # TODO: Implement actual visual detection
        # Example pseudo-code for YOLO:
        # results = self.model(image, conf=self.confidence_threshold)
        # detections = []
        # for detection in results[0].boxes:
        #     x1, y1, x2, y2 = detection.xyxy[0].tolist()
        #     confidence = detection.conf[0].item()
        #     class_id = int(detection.cls[0].item())
        #     class_name = self.model.names[class_id]
        #     
        #     detections.append({
        #         'source': 'vision',
        #         'type': class_name,
        #         'rect': (int(x1), int(y1), int(x2-x1), int(y2-y1)),
        #         'center': (int((x1+x2)/2), int((y1+y2)/2)),
        #         'confidence': confidence,
        #         'name': f"{class_name} (visual)"
        #     })
        # 
        # return detections
        
        return []
    
    def detect_icons(
        self,
        image: Image.Image,
        icon_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Specifically detect UI icons that often lack accessibility labels.
        
        Args:
            image: PIL Image to analyze.
            icon_types: List of specific icon types to detect (None = all).
        
        Returns:
            List of detected icon elements.
        
        Example:
            >>> detector = VisualDetector()
            >>> icons = detector.detect_icons(screenshot, ['hamburger_menu', 'close_button'])
        """
        # This would use specialized icon detection logic
        # Could be a separate model or filtered results from main detector
        
        all_elements = self.detect_elements(image, detect_icons=True)
        
        if icon_types:
            return [
                elem for elem in all_elements
                if elem.get('icon_type') in icon_types
            ]
        
        return [elem for elem in all_elements if 'icon_type' in elem]


class UIScanner:
    """
    Windows UI tree scanner using Accessibility API.
    
    Scans the active window's UI tree to identify interactive elements
    and provides visualization with bounding boxes and numeric IDs.
    
    This approach is more precise than pure vision, as it uses the OS's
    native accessibility APIs to find exact element positions.
    
    Attributes:
        clickable_types: Set of UI element types considered interactive.
        min_visible_area: Minimum pixel area for element to be considered visible.
    """
    
    # Control types that are typically clickable/interactive
    CLICKABLE_TYPES = {
        auto.ControlType.ButtonControl,
        auto.ControlType.EditControl,
        auto.ControlType.HyperlinkControl,
        auto.ControlType.MenuItemControl,
        auto.ControlType.ListItemControl,
        auto.ControlType.TabItemControl,
        auto.ControlType.ComboBoxControl,
        auto.ControlType.CheckBoxControl,
        auto.ControlType.RadioButtonControl,
        auto.ControlType.SliderControl,
        auto.ControlType.TreeItemControl,
    }
    
    def __init__(
        self,
        min_visible_area: int = 25,
        max_depth: int = 15
    ) -> None:
        """
        Initialize the UI Scanner.
        
        Args:
            min_visible_area: Minimum pixel area to consider element visible.
            max_depth: Maximum depth to traverse in UI tree (prevent deep recursion).
        
        Example:
            >>> scanner = UIScanner()
            >>> elements = scanner.scan_active_window()
        """
        self.min_visible_area = min_visible_area
        self.max_depth = max_depth
        self.clickable_types = self.CLICKABLE_TYPES
        
        # Add source tag for hybrid architecture
        self._element_source = 'api'
    
    def scan_active_window(
        self,
        include_offscreen: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scan the active foreground window for interactive UI elements.
        
        Uses Windows Accessibility API to traverse the UI tree and identify
        clickable elements with their exact positions.
        
        Args:
            include_offscreen: Whether to include elements outside visible area.
        
        Returns:
            List of element dictionaries with structure:
            {
                'id': int,              # Sequential ID for reference
                'name': str,            # Element name/text
                'type': str,            # Control type (Button, Edit, etc.)
                'rect': (x,y,w,h),      # Bounding rectangle
                'center': (x,y),        # Center coordinates
                'automation_id': str,   # AutomationId if available
                'class_name': str       # ClassName if available
            }
        
        Raises:
            UIScannerError: If scanning fails.
        
        Example:
            >>> scanner = UIScanner()
            >>> elements = scanner.scan_active_window()
            >>> for elem in elements:
            ...     print(f"#{elem['id']}: {elem['name']} at {elem['center']}")
        """
        try:
            # Get the active foreground window
            print("🔍 Scanning active window...")
            active_window = auto.GetForegroundControl()
            
            if not active_window:
                raise UIScannerError("No active window found")
            
            window_name = active_window.Name or "Unknown Window"
            window_class = active_window.ClassName or ""
            print(f"   Window: {window_name}")
            
            # Store original state
            target_control = active_window  # Default to main window
            original_max_depth = self.max_depth
            
            # STRICT BROWSER DETECTION (avoid false positives)
            window_lower = window_name.lower()
            is_browser = ("google chrome" in window_lower or 
                         "microsoft edge" in window_lower or
                         ("chrome" in window_lower and "chromium" not in window_lower))
            
            # EXPLICIT ELECTRON APP EXCLUSION
            is_electron_app = any(app in window_lower for app in [
                "visual studio code", "code -", "discord", "slack", 
                "spotify", "teams", "electron"
            ])
            
            # Only attempt deep scan for actual browsers
            if is_browser and not is_electron_app:
                print("   🌐 Likely Browser - attempting optimized web scan...")
                
                try:
                    # CRITICAL: Set 1-second timeout to prevent blocking
                    auto.SetGlobalSearchTimeout(1)
                    
                    # Try to find the web content container
                    render_widget = active_window.Control(
                        searchDepth=8, 
                        ClassName="Chrome_RenderWidgetHostHWND"
                    )
                    
                    if render_widget:
                        print("   ✅ Web content container found!")
                        target_control = render_widget
                        # Increase depth for DOM elements
                        self.max_depth = 20
                    else:
                        print("   ⚠️  Web container not found (timeout) - scanning window frame only")
                        
                except Exception as e:
                    print(f"   ⚠️  Web scan error: {type(e).__name__} - falling back to window frame")
                    
                finally:
                    # GUARANTEED RESTORATION of timeout (even if error occurred)
                    auto.SetGlobalSearchTimeout(10)
            
            elif is_electron_app:
                print(f"   🚫 Electron app detected - skipping deep scan")
            
            # Get window bounds for filtering
            window_rect = target_control.BoundingRectangle
            
            # Collect all interactive elements
            elements = []
            element_id = 1
            
            # Traverse UI tree with safe target
            self._traverse_ui_tree(
                control=target_control,
                elements=elements,
                element_id_ref=[element_id],  # Use list for mutable reference
                window_rect=window_rect,
                include_offscreen=include_offscreen,
                depth=0
            )
            
            # Restore original max_depth
            self.max_depth = original_max_depth
            
            print(f"   Found {len(elements)} interactive elements")
            
            # Provide helpful context
            if is_browser and len(elements) > 0:
                if target_control != active_window:
                    print("   💡 Tip: Chrome DOM elements detected - clickable by ID")
                else:
                    print("   💡 Tip: Browser frame detected - use address bar/back button")
            
            return elements
        
        except Exception as e:
            raise UIScannerError(f"Failed to scan active window: {e}")
    
    def _traverse_ui_tree(
        self,
        control: auto.Control,
        elements: List[Dict[str, Any]],
        element_id_ref: List[int],
        window_rect: auto.Rect,
        include_offscreen: bool,
        depth: int
    ) -> None:
        """
        Recursively traverse UI tree to find interactive elements.
        
        Args:
            control: Current UI control to examine.
            elements: List to append found elements to.
            element_id_ref: Mutable reference to current element ID.
            window_rect: Bounding rectangle of parent window.
            include_offscreen: Whether to include offscreen elements.
            depth: Current recursion depth.
        """
        # Prevent excessive recursion
        if depth > self.max_depth:
            return
        
        try:
            # Check if this is an interactive element
            if self._is_interactive(control):
                element_info = self._extract_element_info(
                    control,
                    element_id_ref[0],
                    window_rect,
                    include_offscreen
                )
                
                if element_info:
                    elements.append(element_info)
                    element_id_ref[0] += 1
            
            # Traverse children with timeout protection
            try:
                # Reduce timeout for child enumeration to prevent freezing
                children = control.GetChildren()
                for child in children:
                    try:
                        self._traverse_ui_tree(
                            control=child,
                            elements=elements,
                            element_id_ref=element_id_ref,
                            window_rect=window_rect,
                            include_offscreen=include_offscreen,
                            depth=depth + 1
                        )
                    except Exception:
                        # Skip problematic child but continue with siblings
                        continue
            except Exception:
                # Some controls don't support GetChildren or may timeout
                # Continue processing other elements
                pass
        
        except Exception:
            # Skip problematic controls entirely
            pass
    
    def _is_interactive(self, control: auto.Control) -> bool:
        """
        Check if a control is interactive/clickable.
        
        Args:
            control: UI control to check.
        
        Returns:
            True if control is interactive.
        """
        try:
            # Check control type
            if control.ControlType not in self.clickable_types:
                return False
            
            # Must be enabled
            if not control.IsEnabled:
                return False
            
            # Should have a valid bounding rectangle
            rect = control.BoundingRectangle
            if not rect or rect.width() <= 0 or rect.height() <= 0:
                return False
            
            return True
        
        except Exception:
            return False
    
    def _extract_element_info(
        self,
        control: auto.Control,
        element_id: int,
        window_rect: auto.Rect,
        include_offscreen: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Extract information from a UI control.
        
        Args:
            control: UI control to extract info from.
            element_id: Sequential ID for this element.
            window_rect: Window bounding rectangle.
            include_offscreen: Whether to include offscreen elements.
        
        Returns:
            Dictionary with element info, or None if element should be filtered.
        """
        try:
            rect = control.BoundingRectangle
            
            # Calculate dimensions
            x = rect.left
            y = rect.top
            w = rect.width()
            h = rect.height()
            
            # Filter by visible area
            area = w * h
            if area < self.min_visible_area:
                return None
            
            # Filter offscreen elements (unless requested)
            if not include_offscreen:
                # Check if element is within window bounds
                if (x + w < window_rect.left or 
                    x > window_rect.right or
                    y + h < window_rect.top or 
                    y > window_rect.bottom):
                    return None
            
            # Calculate center point
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Get element properties
            name = control.Name or ""
            control_type_name = control.ControlTypeName or "Unknown"
            automation_id = control.AutomationId or ""
            class_name = control.ClassName or ""
            
            return {
                'id': element_id,
                'source': 'api',  # Mark as API-detected element
                'name': name,
                'type': control_type_name,
                'rect': (x, y, w, h),
                'center': (center_x, center_y),
                'automation_id': automation_id,
                'class_name': class_name
            }
        
        except Exception:
            return None
    
    def draw_ui_overlay(
        self,
        image: Image.Image,
        elements: List[Dict[str, Any]],
        api_color: Tuple[int, int, int] = (0, 255, 0),  # Neon green for API
        vision_color: Tuple[int, int, int] = (255, 165, 0),  # Orange for Vision
        text_color: Tuple[int, int, int] = (255, 255, 255),
        box_width: int = 2,
        show_labels: bool = True
    ) -> Image.Image:
        """
        Draw bounding boxes with numeric IDs over UI elements.
        
        This creates a "Set-of-Marks" visualization where each interactive
        element is highlighted with a colored box and numbered ID.
        Supports different colors for API-based vs Vision-based elements.
        
        Args:
            image: PIL Image to draw on.
            elements: List of elements from scan_active_window() or hybrid scan.
            api_color: RGB color for API-detected elements. Default is neon green.
            vision_color: RGB color for vision-detected elements. Default is orange.
            text_color: RGB color for ID labels. Default is white.
            box_width: Width of bounding box lines. Default is 2.
            show_labels: Whether to show element names. Default is True.
        
        Returns:
            New PIL Image with UI overlay.
        
        Raises:
            UIScannerError: If overlay creation fails.
        
        Example:
            >>> scanner = UIScanner()
            >>> elements = scanner.scan_active_window()
            >>> screenshot = Image.open("screen.png")
            >>> annotated = scanner.draw_ui_overlay(screenshot, elements)
            >>> annotated.save("screen_with_ui_marks.png")
        """
        try:
            # Create a copy to avoid modifying original
            img_copy = image.copy()
            draw = ImageDraw.Draw(img_copy)
            
            # Try to load a font
            try:
                font_id = ImageFont.truetype("arial.ttf", 16)
                font_label = ImageFont.truetype("arial.ttf", 12)
            except Exception:
                font_id = ImageFont.load_default()
                font_label = ImageFont.load_default()
            
            # Draw each element
            for element in elements:
                elem_id = element['id']
                x, y, w, h = element['rect']
                name = element.get('name', '')
                elem_type = element.get('type', 'Unknown')
                source = element.get('source', 'api')
                
                # Choose color based on element source
                box_color = api_color if source == 'api' else vision_color
                
                # Draw bounding box
                draw.rectangle(
                    [(x, y), (x + w, y + h)],
                    outline=box_color,
                    width=box_width
                )
                
                # Draw ID badge at top-left corner
                id_text = str(elem_id)
                id_bbox = draw.textbbox((0, 0), id_text, font=font_id)
                id_width = id_bbox[2] - id_bbox[0]
                id_height = id_bbox[3] - id_bbox[1]
                
                # Draw background for ID
                badge_padding = 4
                badge_x = x
                badge_y = y - id_height - badge_padding * 2
                
                # Adjust if badge would be off-screen
                if badge_y < 0:
                    badge_y = y
                
                draw.rectangle(
                    [
                        (badge_x, badge_y),
                        (badge_x + id_width + badge_padding * 2, 
                         badge_y + id_height + badge_padding * 2)
                    ],
                    fill=box_color
                )
                
                # Draw ID number
                draw.text(
                    (badge_x + badge_padding, badge_y + badge_padding),
                    id_text,
                    fill=text_color,
                    font=font_id
                )
                
                # Draw label if requested and name exists
                if show_labels and name:
                    label = f"{name[:30]}"  # Truncate long names
                    label_bbox = draw.textbbox((0, 0), label, font=font_label)
                    label_height = label_bbox[3] - label_bbox[1]
                    
                    # Draw label below the box
                    label_y = y + h + 2
                    
                    # Background for label
                    draw.rectangle(
                        [
                            (x, label_y),
                            (x + label_bbox[2] - label_bbox[0] + 4, 
                             label_y + label_height + 4)
                        ],
                        fill=(0, 0, 0, 200)
                    )
                    
                    # Draw label text
                    draw.text(
                        (x + 2, label_y + 2),
                        label,
                        fill=text_color,
                        font=font_label
                    )
            
            return img_copy
        
        except Exception as e:
            raise UIScannerError(f"Failed to draw UI overlay: {e}")
    
    def get_element_by_id(
        self,
        elements: List[Dict[str, Any]],
        element_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get element information by its ID.
        
        Args:
            elements: List of elements from scan_active_window().
            element_id: The numeric ID to search for.
        
        Returns:
            Element dictionary if found, None otherwise.
        
        Example:
            >>> scanner = UIScanner()
            >>> elements = scanner.scan_active_window()
            >>> element = scanner.get_element_by_id(elements, 5)
            >>> if element:
            ...     print(f"Element 5: {element['name']}")
        """
        for element in elements:
            if element['id'] == element_id:
                return element
        return None
    
    def filter_by_type(
        self,
        elements: List[Dict[str, Any]],
        control_type: str
    ) -> List[Dict[str, Any]]:
        """
        Filter elements by control type.
        
        Args:
            elements: List of elements from scan_active_window().
            control_type: Type to filter by (e.g., "Button", "Edit").
        
        Returns:
            Filtered list of elements.
        
        Example:
            >>> scanner = UIScanner()
            >>> elements = scanner.scan_active_window()
            >>> buttons = scanner.filter_by_type(elements, "Button")
            >>> print(f"Found {len(buttons)} buttons")
        """
        return [elem for elem in elements if elem['type'] == control_type]
    
    def print_elements(self, elements: List[Dict[str, Any]]) -> None:
        """
        Print element list in a readable format.
        
        Args:
            elements: List of elements to print.
        
        Example:
            >>> scanner = UIScanner()
            >>> elements = scanner.scan_active_window()
            >>> scanner.print_elements(elements)
        """
        print(f"\n{'ID':<4} {'Source':<8} {'Type':<15} {'Name':<30} {'Center':<15}")
        print("-" * 80)
        
        for elem in elements:
            elem_id = elem.get('id', '?')
            source = elem.get('source', 'unknown')
            elem_type = elem.get('type', 'Unknown')
            name = elem.get('name', '(no name)')[:30]
            center = f"({elem['center'][0]}, {elem['center'][1]})"
            
            print(f"{elem_id:<4} {source:<8} {elem_type:<15} {name:<30} {center:<15}")


class HybridScanner:
    """
    Hybrid vision scanner combining Accessibility API and visual detection.
    
    This scanner merges elements from both Windows UI Automation and computer
    vision models to provide comprehensive UI element detection, including
    elements that lack accessibility labels (icons, images, etc.).
    
    Attributes:
        ui_scanner: UIScanner instance for API-based detection.
        visual_detector: VisualDetector instance for vision-based detection.
        iou_threshold: Intersection over Union threshold for deduplication.
    """
    
    def __init__(
        self,
        enable_visual: bool = False,
        model_path: Optional[str] = None,
        iou_threshold: float = 0.5,
        **scanner_kwargs
    ) -> None:
        """
        Initialize the Hybrid Scanner.
        
        Args:
            enable_visual: Whether to enable visual detection (requires model).
            model_path: Path to visual detection model weights.
            iou_threshold: IoU threshold for merging duplicate elements (0.0-1.0).
            **scanner_kwargs: Additional arguments passed to UIScanner.
        
        Example:
            >>> # API-only mode (default)
            >>> scanner = HybridScanner()
            >>> 
            >>> # Hybrid mode with visual detection
            >>> scanner = HybridScanner(enable_visual=True, model_path="models/ui.pt")
        """
        self.ui_scanner = UIScanner(**scanner_kwargs)
        self.visual_detector = VisualDetector(model_path) if enable_visual else None
        self.iou_threshold = iou_threshold
        self.enable_visual = enable_visual
    
    def scan(
        self,
        screenshot: Optional[Image.Image] = None,
        detect_icons: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid scan combining API and visual detection.
        
        Args:
            screenshot: PIL Image for visual detection (required if enable_visual=True).
            detect_icons: Whether to specifically detect UI icons.
        
        Returns:
            Merged list of UI elements from both sources.
        
        Example:
            >>> scanner = HybridScanner(enable_visual=True)
            >>> from PIL import Image
            >>> screenshot = Image.open("screen.png")
            >>> elements = scanner.scan(screenshot)
            >>> print(f"Found {len(elements)} total elements")
        """
        # Get API-based elements
        api_elements = self.ui_scanner.scan_active_window()
        
        # Get vision-based elements if enabled
        vision_elements = []
        if self.enable_visual and self.visual_detector and screenshot:
            vision_elements = self.visual_detector.detect_elements(
                screenshot,
                detect_icons=detect_icons
            )
        
        # Merge elements and assign IDs
        merged = self._merge_elements(api_elements, vision_elements)
        
        # Reassign sequential IDs
        for idx, elem in enumerate(merged, start=1):
            elem['id'] = idx
        
        return merged
    
    def _merge_elements(
        self,
        api_elements: List[Dict[str, Any]],
        vision_elements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge API and vision elements, removing duplicates using IoU.
        
        Strategy:
        1. Keep all API elements (they're most reliable)
        2. Add vision elements that don't overlap with API elements
        3. Use IoU to determine overlaps
        
        Args:
            api_elements: Elements from UI Automation API.
            vision_elements: Elements from visual detection.
        
        Returns:
            Merged list without duplicates.
        """
        merged = list(api_elements)  # Start with all API elements
        
        for vision_elem in vision_elements:
            # Check if this vision element overlaps with any API element
            is_duplicate = False
            
            for api_elem in api_elements:
                iou = self._calculate_iou(
                    vision_elem['rect'],
                    api_elem['rect']
                )
                
                if iou >= self.iou_threshold:
                    # This vision element overlaps with an API element
                    # API elements are more reliable, so skip this vision element
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # This vision element is unique, add it
                merged.append(vision_elem)
        
        return merged
    
    def _calculate_iou(
        self,
        rect1: Tuple[int, int, int, int],
        rect2: Tuple[int, int, int, int]
    ) -> float:
        """
        Calculate Intersection over Union (IoU) between two rectangles.
        
        Args:
            rect1: (x, y, width, height) of first rectangle.
            rect2: (x, y, width, height) of second rectangle.
        
        Returns:
            IoU score (0.0 to 1.0).
        
        Example:
            >>> scanner = HybridScanner()
            >>> iou = scanner._calculate_iou((10, 10, 50, 50), (30, 30, 50, 50))
            >>> print(f"Overlap: {iou:.2f}")
        """
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        
        # Convert to (x1, y1, x2, y2) format
        box1 = [x1, y1, x1 + w1, y1 + h1]
        box2 = [x2, y2, x2 + w2, y2 + h2]
        
        # Calculate intersection area
        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])
        
        if x_right < x_left or y_bottom < y_top:
            # No intersection
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union area
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - intersection_area
        
        if union_area == 0:
            return 0.0
        
        # Calculate IoU
        iou = intersection_area / union_area
        return iou
    
    def detect_unlabeled_icons(
        self,
        screenshot: Image.Image,
        icon_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Specifically detect UI icons that lack accessibility labels.
        
        This is particularly useful for:
        - Hamburger menus without text
        - Icon-only buttons
        - Social media icons
        - Action icons (share, like, comment)
        
        Args:
            screenshot: PIL Image to analyze.
            icon_types: Specific icon types to detect (None = all).
        
        Returns:
            List of detected icon elements.
        
        Example:
            >>> scanner = HybridScanner(enable_visual=True)
            >>> screenshot = Image.open("screen.png")
            >>> icons = scanner.detect_unlabeled_icons(screenshot)
            >>> print(f"Found {len(icons)} unlabeled icons")
        """
        if not self.visual_detector:
            print("⚠️  Visual detection not enabled. Initialize with enable_visual=True")
            return []
        
        return self.visual_detector.detect_icons(screenshot, icon_types)
