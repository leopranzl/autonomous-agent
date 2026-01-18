"""
Action Controller Module
Safe desktop automation with coordinate scaling for AI-driven control.
Includes Playwright integration for precise web interaction.
"""

from typing import Optional, Tuple, List, Dict, Any
import pyautogui
import time


class DesktopControllerError(Exception):
    """Exception raised when desktop control action fails."""
    pass


class CoordinateOutOfBoundsError(DesktopControllerError):
    """Exception raised when coordinates are outside screen bounds."""
    pass


class WebAutomationError(DesktopControllerError):
    """Exception raised when web automation (Playwright) fails."""
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
        failsafe: bool = True,
        enable_playwright: bool = True
    ) -> None:
        """
        Initialize the DesktopController with safety settings.
        
        Args:
            ai_image_width: Width of image sent to AI (None = no scaling).
            ai_image_height: Height of image sent to AI (None = no scaling).
            action_delay: Delay between actions in seconds. Default is 0.5.
            failsafe: Enable PyAutoGUI failsafe (move to corner to abort).
            enable_playwright: Enable Playwright for web automation. Default is True.
        
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
        
        # Playwright integration (optional)
        self.enable_playwright = enable_playwright
        self.playwright_context = None
        self.browser = None
        self.page = None
        self._connection_attempted = False
        
        if enable_playwright:
            try:
                from playwright.sync_api import sync_playwright
                self.playwright_available = True
                print("   ✅ Playwright available for web automation")
            except ImportError:
                self.playwright_available = False
                print("   ⚠️  Playwright not installed (web automation disabled)")
                print("      Install with: pip install playwright && playwright install chromium")
            except Exception as e:
                self.playwright_available = False
                print(f"   ⚠️  Playwright error: {e}")
    
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
    
    def wait(self, seconds: int) -> None:
        """
        Pause execution for a specified number of seconds.
        
        Use this after launching applications to allow them to load and render.
        This prevents race conditions where the agent tries to interact with
        UI elements before the application is ready.
        
        Args:
            seconds: Number of seconds to wait.
        
        Example:
            >>> controller = DesktopController()
            >>> # Launch Chrome
            >>> controller.hotkey('win', 'r')
            >>> controller.type_text('chrome')
            >>> controller.press_key('enter')
            >>> # Wait for Chrome to fully load
            >>> controller.wait(5)
        """
        time.sleep(seconds)
    
    # ========== PLAYWRIGHT WEB AUTOMATION METHODS ==========
    
    def _ensure_browser_connection(self) -> bool:
        """
        Ensure Playwright is connected to Chrome browser via CDP.
        
        Dynamically connects to Chrome when needed. Implements retry logic
        to handle cases where Chrome is still initializing.
        
        Returns:
            True if browser is connected, False otherwise.
        """
        if not self.enable_playwright or not hasattr(self, 'playwright_available') or not self.playwright_available:
            return False
        
        # If already connected and page is valid, return True
        if self.page is not None:
            try:
                # Verify the page is still valid
                _ = self.page.url
                return True
            except Exception:
                # Page became invalid, need to reconnect
                self.page = None
                self.browser = None
        
        # Attempt to connect to Chrome's CDP port
        try:
            from playwright.sync_api import sync_playwright
            import time
            import socket
            
            # Check if CDP port is accessible
            def is_port_open(host: str = 'localhost', port: int = 9222, timeout: float = 1.0) -> bool:
                """Check if Chrome's CDP port is accessible."""
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    return result == 0
                except Exception:
                    return False
            
            # Retry logic: Check if port is open (Chrome might still be starting)
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                if is_port_open():
                    break
                if attempt < max_retries - 1:
                    print(f"   ⏳ Chrome CDP port not ready, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
            else:
                # Port never became available
                print("   ⚠️  Chrome CDP port (9222) not accessible. Ensure Chrome is launched with --remote-debugging-port=9222")
                return False
            
            # Initialize Playwright context if not already done
            if not hasattr(self, 'playwright_context') or self.playwright_context is None:
                self.playwright_context = sync_playwright().start()
                print("   🎭 Playwright context started")
            
            # Connect to Chrome via CDP
            try:
                self.browser = self.playwright_context.chromium.connect_over_cdp("http://localhost:9222")
                print("   🔗 Connected to Chrome via CDP")
                
                # Get the first available page (or create one if none exist)
                contexts = self.browser.contexts
                if contexts and len(contexts) > 0:
                    context = contexts[0]
                    pages = context.pages
                    if pages and len(pages) > 0:
                        self.page = pages[0]
                        print(f"   📄 Using existing page: {self.page.url}")
                    else:
                        self.page = context.new_page()
                        print("   📄 Created new page")
                else:
                    # No context available, this shouldn't happen with CDP connection
                    print("   ⚠️  No browser context found")
                    return False
                
                self._connection_attempted = True
                return True
                
            except Exception as e:
                print(f"   ❌ Failed to connect via CDP: {e}")
                return False
        
        except ImportError:
            print("   ⚠️  Playwright not available")
            return False
        except Exception as e:
            print(f"   ❌ Browser connection error: {e}")
            return False
    
    def web_click(self, selector: str, timeout: int = 5000) -> None:
        """
        Click a web element using CSS selector (Playwright).
        
        More precise than coordinate-based clicking for web elements.
        
        Args:
            selector: CSS selector (e.g., 'button.submit', '#login-btn').
            timeout: Maximum wait time in milliseconds. Default is 5000.
        
        Raises:
            WebAutomationError: If element not found or click fails.
        
        Example:
            >>> controller = DesktopController()
            >>> controller.web_click('button[type="submit"]')
            >>> controller.web_click('#search-button')
        """
        if not self._ensure_browser_connection():
            raise WebAutomationError(
                "Cannot connect to Chrome. Ensure Chrome is running with: "
                "chrome --force-renderer-accessibility --remote-debugging-port=9222"
            )
        
        try:
            self.page.click(selector, timeout=timeout)
        except Exception as e:
            raise WebAutomationError(f"Failed to click element '{selector}': {e}")
    
    def web_type(self, selector: str, text: str, timeout: int = 5000, press_enter: bool = False) -> None:
        """
        Type text into a web element using CSS selector (Playwright).
        
        Args:
            selector: CSS selector of input field.
            text: Text to type.
            timeout: Maximum wait time in milliseconds. Default is 5000.
            press_enter: Whether to press Enter after typing. Default is False.
        
        Raises:
            WebAutomationError: If element not found or typing fails.
        
        Example:
            >>> controller = DesktopController()
            >>> controller.web_type('input[name="search"]', 'Python tutorials')
            >>> controller.web_type('#email', 'user@example.com', press_enter=True)
        """
        if not self._ensure_browser_connection():
            raise WebAutomationError(
                "Cannot connect to Chrome. Ensure Chrome is running with: "
                "chrome --force-renderer-accessibility --remote-debugging-port=9222"
            )
        
        try:
            self.page.fill(selector, text, timeout=timeout)
            if press_enter:
                self.page.press(selector, "Enter")
        except Exception as e:
            raise WebAutomationError(f"Failed to type into element '{selector}': {e}")
    
    def web_get_elements(self, max_elements: int = 50) -> List[Dict[str, Any]]:
        """
        Get interactive web elements from current page (Playwright).
        
        Returns a simplified list of clickable/typeable elements with their
        selectors and text content.
        
        Args:
            max_elements: Maximum number of elements to return. Default is 50.
        
        Returns:
            List of element dictionaries with 'selector', 'type', 'text', 'role'.
        
        Raises:
            WebAutomationError: If unable to get elements.
        
        Example:
            >>> controller = DesktopController()
            >>> elements = controller.web_get_elements()
            >>> for elem in elements:
            ...     print(f"{elem['type']}: {elem['text'][:30]}")
        """
        if not self._ensure_browser_connection():
            raise WebAutomationError(
                "Cannot connect to Chrome. Ensure Chrome is running with: "
                "chrome --force-renderer-accessibility --remote-debugging-port=9222"
            )
        
        try:
            elements = []
            
            # Get interactive elements using accessibility tree
            # This is more reliable than parsing full DOM
            snapshot = self.page.accessibility.snapshot()
            
            def extract_elements(node: Dict[str, Any], depth: int = 0, max_depth: int = 10):
                if depth > max_depth or len(elements) >= max_elements:
                    return
                
                role = node.get('role', '')
                name = node.get('name', '')
                
                # Only include interactive elements
                if role in ['button', 'link', 'textbox', 'searchbox', 'combobox', 'menuitem']:
                    # Generate a selector (simplified, may need refinement)
                    selector = None
                    if name:
                        # Try to create a selector based on text content
                        if role == 'button':
                            selector = f'button:has-text("{name[:30]}")'
                        elif role == 'link':
                            selector = f'a:has-text("{name[:30]}")'
                        elif role in ['textbox', 'searchbox']:
                            selector = f'input[type="text"]'
                    
                    if selector or name:
                        elements.append({
                            'selector': selector or f'[role="{role}"]',
                            'type': role,
                            'text': name[:100] if name else '',
                            'role': role
                        })
                
                # Recurse into children
                for child in node.get('children', []):
                    extract_elements(child, depth + 1, max_depth)
            
            if snapshot:
                extract_elements(snapshot)
            
            return elements[:max_elements]
            
        except Exception as e:
            raise WebAutomationError(f"Failed to get web elements: {e}")
    
    def web_get_url(self) -> Optional[str]:
        """
        Get current page URL (Playwright).
        
        Returns:
            Current URL or None if not connected.
        """
        if not self._ensure_browser_connection():
            return None
        
        try:
            return self.page.url
        except Exception:
            return None
    
    def close_playwright(self) -> None:
        """
        Close Playwright connection and cleanup.
        
        Call this when shutting down the controller.
        """
        try:
            if self.page:
                self.page = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright_context') and self.playwright_context:
                self.playwright_context.stop()
                self.playwright_context = None
            print("   🧹 Playwright connection closed")
        except Exception as e:
            print(f"   ⚠️  Error closing Playwright: {e}")
