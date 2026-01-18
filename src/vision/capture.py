"""
Screen Capture Module
Ultra-fast screen capture with coordinate grid overlay for AI vision.
"""

from typing import Optional, Tuple
import mss
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


class ScreenCaptureError(Exception):
    """Exception raised when screen capture fails."""
    pass


class ScreenCapture:
    """
    High-performance screen capture with coordinate grid overlay.
    
    This class provides ultra-fast screen capture using mss library and adds
    a coordinate grid overlay to help AI models understand X,Y positions.
    
    Attributes:
        sct: MSS screen capture instance.
        monitor: Monitor configuration dictionary.
        grid_spacing: Spacing between grid lines in pixels.
        grid_color: RGB tuple for grid line color.
        grid_alpha: Transparency level for grid (0-255).
    """
    
    def __init__(
        self,
        grid_spacing: int = 100,
        grid_color: Tuple[int, int, int] = (255, 0, 0),
        grid_alpha: int = 180
    ) -> None:
        """
        Initialize the ScreenCapture instance.
        
        Args:
            grid_spacing: Distance between grid lines in pixels. Default is 100.
            grid_color: RGB color tuple for grid lines. Default is red (255, 0, 0).
            grid_alpha: Transparency level for grid overlay (0-255). Default is 180.
        
        Raises:
            ScreenCaptureError: If screen capture initialization fails.
        """
        try:
            self.sct = mss.mss()
            self.monitor = self.sct.monitors[1]  # Primary monitor (index 0 is all monitors)
            self.grid_spacing = grid_spacing
            self.grid_color = grid_color
            self.grid_alpha = grid_alpha
        except Exception as e:
            raise ScreenCaptureError(f"Failed to initialize screen capture: {e}")
    
    def capture(self) -> Image.Image:
        """
        Capture the primary monitor screen.
        
        Returns:
            PIL Image object of the captured screen.
        
        Raises:
            ScreenCaptureError: If screen capture fails.
        
        Example:
            >>> capture = ScreenCapture()
            >>> image = capture.capture()
            >>> image.save("screenshot.png")
        """
        try:
            # Capture screen using mss (ultra-fast)
            screenshot = self.sct.grab(self.monitor)
            
            # Convert to PIL Image
            img = Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.rgb
            )
            
            return img
        
        except Exception as e:
            raise ScreenCaptureError(f"Failed to capture screen: {e}")
    
    def capture_with_grid(self) -> Image.Image:
        """
        Capture screen and add coordinate grid overlay.
        
        Returns:
            PIL Image with coordinate grid overlay.
        
        Raises:
            ScreenCaptureError: If capture or grid overlay fails.
        
        Example:
            >>> capture = ScreenCapture()
            >>> image = capture.capture_with_grid()
            >>> image.save("screenshot_with_grid.png")
        """
        try:
            image = self.capture()
            return self.add_grid_overlay(image)
        except Exception as e:
            raise ScreenCaptureError(f"Failed to capture screen with grid: {e}")
    
    def add_grid_overlay(self, image: Image.Image) -> Image.Image:
        """
        Add semi-transparent coordinate grid overlay to image.
        
        Draws a grid with labeled coordinates to help AI models understand
        X,Y positions on the screen. Each grid intersection is labeled with
        its coordinates (e.g., "100,200").
        
        Args:
            image: PIL Image to add grid overlay to.
        
        Returns:
            New PIL Image with grid overlay applied.
        
        Raises:
            ScreenCaptureError: If grid overlay creation fails.
        
        Example:
            >>> capture = ScreenCapture(grid_spacing=150)
            >>> img = Image.open("screenshot.png")
            >>> img_with_grid = capture.add_grid_overlay(img)
        """
        try:
            # Create a copy to avoid modifying original
            img_copy = image.copy()
            width, height = img_copy.size
            
            # Create transparent overlay
            overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Try to load a font, fallback to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except Exception:
                font = ImageFont.load_default()
            
            # Draw vertical grid lines
            for x in range(0, width, self.grid_spacing):
                draw.line(
                    [(x, 0), (x, height)],
                    fill=(*self.grid_color, self.grid_alpha),
                    width=1
                )
            
            # Draw horizontal grid lines
            for y in range(0, height, self.grid_spacing):
                draw.line(
                    [(0, y), (width, y)],
                    fill=(*self.grid_color, self.grid_alpha),
                    width=1
                )
            
            # Add coordinate labels at intersections
            for x in range(0, width, self.grid_spacing):
                for y in range(0, height, self.grid_spacing):
                    # Skip origin to avoid clutter
                    if x == 0 and y == 0:
                        continue
                    
                    # Format coordinate label
                    label = f"{x},{y}"
                    
                    # Get text bounding box for background
                    bbox = draw.textbbox((x + 2, y + 2), label, font=font)
                    
                    # Draw semi-transparent background for text readability
                    draw.rectangle(
                        bbox,
                        fill=(0, 0, 0, 150)
                    )
                    
                    # Draw coordinate text
                    draw.text(
                        (x + 2, y + 2),
                        label,
                        fill=(255, 255, 255, 255),
                        font=font
                    )
            
            # Convert base image to RGBA for compositing
            if img_copy.mode != "RGBA":
                img_copy = img_copy.convert("RGBA")
            
            # Composite overlay onto image
            result = Image.alpha_composite(img_copy, overlay)
            
            # Convert back to RGB
            return result.convert("RGB")
        
        except Exception as e:
            raise ScreenCaptureError(f"Failed to add grid overlay: {e}")
    
    def get_monitor_info(self) -> dict:
        """
        Get information about the primary monitor.
        
        Returns:
            Dictionary containing monitor dimensions and position.
        
        Example:
            >>> capture = ScreenCapture()
            >>> info = capture.get_monitor_info()
            >>> print(f"Resolution: {info['width']}x{info['height']}")
        """
        return {
            "width": self.monitor["width"],
            "height": self.monitor["height"],
            "top": self.monitor["top"],
            "left": self.monitor["left"]
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        if hasattr(self, 'sct'):
            self.sct.close()
    
    def close(self) -> None:
        """
        Close the screen capture instance and free resources.
        
        Example:
            >>> capture = ScreenCapture()
            >>> # ... use capture ...
            >>> capture.close()
        """
        if hasattr(self, 'sct'):
            self.sct.close()
