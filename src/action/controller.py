"""
Action Controller Module
Safe desktop automation with coordinate scaling for AI-driven control.
"""

from typing import Optional, Tuple
import pyautogui
import time


class DesktopControllerError(Exception):
    """Exception raised when desktop control action fails."""
    pass


class CoordinateOutOfBoundsError(DesktopControllerError):
    """Exception raised when coordinates are outside screen bounds."""
    pass


class DesktopController:
    """
    Safe desktop automation controller with coordinate scaling.
    
    This class provides a safe wrapper around pyautogui with built-in
    coordinate translation from AI-analyzed images to real screen coordinates.
    
    Attributes:
        screen_width: Real screen width in pixels.
        screen_height: Real screen height in pixels.
        ai_image_width: Width of image analyzed by AI (for scaling).
        ai_image_height: Height of image analyzed by AI (for scaling).
        action_delay: Delay between actions in seconds.
    """
    
    def __init__(
        self,
        ai_image_width: Optional[int] = None,
        ai_image_height: Optional[int] = None,
        action_delay: float = 0.5,
        failsafe: bool = True
    ) -> None:
        """
        Initialize the DesktopController with safety settings.
        
        Args:
            ai_image_width: Width of image sent to AI (None = no scaling).
            ai_image_height: Height of image sent to AI (None = no scaling).
            action_delay: Delay between actions in seconds. Default is 0.5.
            failsafe: Enable PyAutoGUI failsafe (move to corner to abort).
        
        Example:
            >>> # AI analyzes 1024x768 image, but screen is 1920x1080
            >>> controller = DesktopController(
            ...     ai_image_width=1024,
            ...     ai_image_height=768
            ... )
        """
        # Enable PyAutoGUI failsafe - move mouse to corner to abort
        pyautogui.FAILSAFE = failsafe
        
        # Set action delay for safety
        pyautogui.PAUSE = action_delay
        self.action_delay = action_delay
        
        # Get real screen dimensions
        screen_size = pyautogui.size()
        self.screen_width = screen_size.width
        self.screen_height = screen_size.height
        
        # AI image dimensions (for coordinate scaling)
        self.ai_image_width = ai_image_width or self.screen_width
        self.ai_image_height = ai_image_height or self.screen_height
        
        # Calculate scaling factors
        self.scale_x = self.screen_width / self.ai_image_width
        self.scale_y = self.screen_height / self.ai_image_height
    
    def scale_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """
        Scale AI coordinates to real screen coordinates.
        
        Translates coordinates from AI-analyzed image space to actual
        screen space, accounting for resolution differences.
        
        Args:
            x: X coordinate from AI analysis.
            y: Y coordinate from AI analysis.
        
        Returns:
            Tuple of (scaled_x, scaled_y) in screen coordinates.
        
        Example:
            >>> controller = DesktopController(
            ...     ai_image_width=1024,
            ...     ai_image_height=768
            ... )
            >>> # AI says click at (512, 384) on 1024x768 image
            >>> real_x, real_y = controller.scale_coordinates(512, 384)
            >>> # Returns (960, 540) for 1920x1080 screen
        """
        scaled_x = int(x * self.scale_x)
        scaled_y = int(y * self.scale_y)
        return scaled_x, scaled_y
    
    def validate_coordinates(self, x: int, y: int) -> bool:
        """
        Check if coordinates are within screen bounds.
        
        Args:
            x: X coordinate to validate.
            y: Y coordinate to validate.
        
        Returns:
            True if coordinates are valid, False otherwise.
        
        Raises:
            CoordinateOutOfBoundsError: If coordinates are outside screen.
        """
        if not (0 <= x < self.screen_width):
            raise CoordinateOutOfBoundsError(
                f"X coordinate {x} is outside screen width (0-{self.screen_width})"
            )
        
        if not (0 <= y < self.screen_height):
            raise CoordinateOutOfBoundsError(
                f"Y coordinate {y} is outside screen height (0-{self.screen_height})"
            )
        
        return True
    
    def move_mouse(
        self,
        x: int,
        y: int,
        duration: float = 0.5,
        scale: bool = True
    ) -> None:
        """
        Smoothly move mouse cursor to specified coordinates.
        
        Args:
            x: X coordinate (AI space if scale=True, screen space if False).
            y: Y coordinate (AI space if scale=True, screen space if False).
            duration: Time to complete movement in seconds. Default is 0.5.
            scale: Whether to scale from AI coordinates. Default is True.
        
        Raises:
            CoordinateOutOfBoundsError: If coordinates are outside screen.
            DesktopControllerError: If mouse movement fails.
        
        Example:
            >>> controller = DesktopController()
            >>> controller.move_mouse(100, 200, duration=0.3)
        """
        try:
            # Scale coordinates if needed
            if scale:
                x, y = self.scale_coordinates(x, y)
            
            # Validate coordinates
            self.validate_coordinates(x, y)
            
            # Move mouse smoothly
            pyautogui.moveTo(x, y, duration=duration)
            
        except (CoordinateOutOfBoundsError, pyautogui.FailSafeException):
            raise
        except Exception as e:
            raise DesktopControllerError(f"Failed to move mouse to ({x}, {y}): {e}")
    
    def click_element(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        duration: float = 0.3,
        scale: bool = True
    ) -> None:
        """
        Move to coordinates and perform mouse click.
        
        Args:
            x: X coordinate (AI space if scale=True, screen space if False).
            y: Y coordinate (AI space if scale=True, screen space if False).
            button: Mouse button ("left", "right", "middle"). Default is "left".
            clicks: Number of clicks. Default is 1 (2 for double-click).
            duration: Time to move mouse in seconds. Default is 0.3.
            scale: Whether to scale from AI coordinates. Default is True.
        
        Raises:
            CoordinateOutOfBoundsError: If coordinates are outside screen.
            DesktopControllerError: If click action fails.
        
        Example:
            >>> controller = DesktopController()
            >>> # Single left click
            >>> controller.click_element(512, 384)
            >>> # Double click
            >>> controller.click_element(512, 384, clicks=2)
            >>> # Right click
            >>> controller.click_element(512, 384, button="right")
        """
        try:
            # Scale coordinates if needed
            if scale:
                x, y = self.scale_coordinates(x, y)
            
            # Validate coordinates
            self.validate_coordinates(x, y)
            
            # Move to position
            pyautogui.moveTo(x, y, duration=duration)
            
            # Small delay before clicking
            time.sleep(0.1)
            
            # Perform click
            pyautogui.click(button=button, clicks=clicks)
            
        except (CoordinateOutOfBoundsError, pyautogui.FailSafeException):
            raise
        except Exception as e:
            raise DesktopControllerError(
                f"Failed to click at ({x}, {y}) with {button} button: {e}"
            )
    
    def type_text(
        self,
        text: str,
        interval: float = 0.05,
        press_enter: bool = False
    ) -> None:
        """
        Type text using simulated keystrokes.
        
        Args:
            text: Text to type.
            interval: Delay between keystrokes in seconds. Default is 0.05.
            press_enter: Whether to press Enter after typing. Default is False.
        
        Raises:
            DesktopControllerError: If typing fails.
        
        Example:
            >>> controller = DesktopController()
            >>> controller.type_text("Hello, World!")
            >>> # Type and press Enter
            >>> controller.type_text("search query", press_enter=True)
        """
        try:
            # Type the text with specified interval
            pyautogui.write(text, interval=interval)
            
            # Press Enter if requested
            if press_enter:
                time.sleep(0.1)
                pyautogui.press("enter")
        
        except pyautogui.FailSafeException:
            raise
        except Exception as e:
            raise DesktopControllerError(f"Failed to type text '{text}': {e}")
    
    def scroll(
        self,
        clicks: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
        scale: bool = True
    ) -> None:
        """
        Scroll mouse wheel at current or specified position.
        
        Args:
            clicks: Number of scroll clicks (positive=up, negative=down).
            x: Optional X coordinate to scroll at (AI space if scale=True).
            y: Optional Y coordinate to scroll at (AI space if scale=True).
            scale: Whether to scale from AI coordinates. Default is True.
        
        Raises:
            CoordinateOutOfBoundsError: If coordinates are outside screen.
            DesktopControllerError: If scroll action fails.
        
        Example:
            >>> controller = DesktopController()
            >>> # Scroll down 5 clicks at current position
            >>> controller.scroll(-5)
            >>> # Scroll up 3 clicks at specific position
            >>> controller.scroll(3, x=512, y=384)
        """
        try:
            # Move to position if specified
            if x is not None and y is not None:
                if scale:
                    x, y = self.scale_coordinates(x, y)
                self.validate_coordinates(x, y)
                pyautogui.moveTo(x, y, duration=0.2)
            
            # Perform scroll
            pyautogui.scroll(clicks)
        
        except (CoordinateOutOfBoundsError, pyautogui.FailSafeException):
            raise
        except Exception as e:
            raise DesktopControllerError(f"Failed to scroll: {e}")
    
    def press_key(self, key: str, presses: int = 1) -> None:
        """
        Press a keyboard key one or more times.
        
        Args:
            key: Key name (e.g., "enter", "esc", "tab", "ctrl", "alt").
            presses: Number of times to press the key. Default is 1.
        
        Raises:
            DesktopControllerError: If key press fails.
        
        Example:
            >>> controller = DesktopController()
            >>> controller.press_key("enter")
            >>> controller.press_key("tab", presses=3)
        """
        try:
            pyautogui.press(key, presses=presses)
        except pyautogui.FailSafeException:
            raise
        except Exception as e:
            raise DesktopControllerError(f"Failed to press key '{key}': {e}")
    
    def hotkey(self, *keys: str) -> None:
        """
        Press a combination of keys (hotkey/shortcut).
        
        Args:
            *keys: Variable number of key names to press together.
        
        Raises:
            DesktopControllerError: If hotkey press fails.
        
        Example:
            >>> controller = DesktopController()
            >>> # Ctrl+C (copy)
            >>> controller.hotkey("ctrl", "c")
            >>> # Ctrl+Shift+T (reopen tab)
            >>> controller.hotkey("ctrl", "shift", "t")
        """
        try:
            pyautogui.hotkey(*keys)
        except pyautogui.FailSafeException:
            raise
        except Exception as e:
            raise DesktopControllerError(f"Failed to press hotkey {keys}: {e}")
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Get current mouse cursor position.
        
        Returns:
            Tuple of (x, y) screen coordinates.
        
        Example:
            >>> controller = DesktopController()
            >>> x, y = controller.get_mouse_position()
            >>> print(f"Mouse at ({x}, {y})")
        """
        position = pyautogui.position()
        return position.x, position.y
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get screen dimensions.
        
        Returns:
            Tuple of (width, height) in pixels.
        
        Example:
            >>> controller = DesktopController()
            >>> width, height = controller.get_screen_size()
            >>> print(f"Screen: {width}x{height}")
        """
        return self.screen_width, self.screen_height
    
    def set_ai_image_size(self, width: int, height: int) -> None:
        """
        Update AI image dimensions for coordinate scaling.
        
        Use this when the AI analyzes images of different sizes.
        
        Args:
            width: New AI image width.
            height: New AI image height.
        
        Example:
            >>> controller = DesktopController()
            >>> # AI now analyzes 800x600 images
            >>> controller.set_ai_image_size(800, 600)
        """
        self.ai_image_width = width
        self.ai_image_height = height
        self.scale_x = self.screen_width / self.ai_image_width
        self.scale_y = self.screen_height / self.ai_image_height
