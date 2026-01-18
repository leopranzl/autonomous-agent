"""
UI Tree Scanner Module
Windows Accessibility API-based element detection and visualization.
"""

from typing import List, Dict, Tuple, Optional, Any
import uiautomation as auto
from PIL import Image, ImageDraw, ImageFont
import time


class UIScannerError(Exception):
    """Exception raised when UI scanning fails."""
    pass


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
        box_color: Tuple[int, int, int] = (0, 255, 0),  # Neon green
        text_color: Tuple[int, int, int] = (255, 255, 255),
        box_width: int = 2,
        show_labels: bool = True
    ) -> Image.Image:
        """
        Draw bounding boxes with numeric IDs over UI elements.
        
        This creates a "Set-of-Marks" visualization where each interactive
        element is highlighted with a colored box and numbered ID.
        
        Args:
            image: PIL Image to draw on.
            elements: List of elements from scan_active_window().
            box_color: RGB color for bounding boxes. Default is neon green.
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
                name = element['name']
                elem_type = element['type']
                
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
        print(f"\n{'ID':<4} {'Type':<15} {'Name':<30} {'Center':<15}")
        print("-" * 70)
        
        for elem in elements:
            elem_id = elem['id']
            elem_type = elem['type']
            name = elem['name'][:30] if elem['name'] else "(no name)"
            center = f"({elem['center'][0]}, {elem['center'][1]})"
            
            print(f"{elem_id:<4} {elem_type:<15} {name:<30} {center:<15}")
