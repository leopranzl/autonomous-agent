"""
AI Agent Brain Module
Google Gemini-powered autonomous agent with function calling.
"""

from typing import Optional, Dict, List, Any
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()


class GeminiAgentError(Exception):
    """Exception raised when Gemini agent encounters an error."""
    pass


class GeminiAgent:
    """
    Autonomous AI agent using Google Gemini with function calling.
    
    This agent analyzes screenshots with coordinate grids and determines
    which actions to take by calling appropriate tools (functions).
    
    Attributes:
        client: Google GenAI client instance.
        model_name: Name of the Gemini model to use.
        tools: List of function declarations for tool calling.
    """
    
    # System instruction that defines the agent's behavior
    SYSTEM_INSTRUCTION = """You are an expert computer operator AI agent with visual understanding capabilities.

Your Mission:
- Analyze screenshots with coordinate grid overlays to understand the user interface
- Identify UI elements (buttons, links, text fields, etc.) based on user requests
- Determine precise X,Y coordinates using the visible grid labels (e.g., "100,200")
- Call appropriate tools/functions to interact with the screen

Coordinate Guidelines:
- The screenshot has a RED GRID OVERLAY with coordinate labels at intersections
- Read these labels carefully to estimate exact positions
- Grid spacing is typically 100 pixels
- Use the grid to calculate positions between labeled points
- ALWAYS provide coordinates in the AI image space (the image you see)

Action Strategy:
1. Carefully observe the screenshot and locate the target element
2. Use the grid overlay to determine coordinates
3. Choose the appropriate tool (click_element, type_text, scroll, etc.)
4. Provide accurate parameters for the tool

Safety Rules:
- Double-check coordinates before calling click_element
- Be precise with text input for type_text
- Explain your reasoning briefly when selecting coordinates
- If unsure about location, ask for clarification instead of guessing

Response Format:
- When you identify an element, explain WHERE you see it (e.g., "I see the login button at approximately 520,340 based on the grid")
- Then call the appropriate tool with exact coordinates
- Be concise but clear in your explanations"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        api_key: Optional[str] = None
    ) -> None:
        """
        Initialize the Gemini agent with function calling capabilities.
        
        Args:
            model_name: Gemini model to use. Default is "gemini-2.0-flash-exp".
            api_key: Google API key. If None, loads from GOOGLE_API_KEY env var.
        
        Raises:
            GeminiAgentError: If API key is missing or client initialization fails.
        
        Example:
            >>> agent = GeminiAgent()
            >>> # Or with specific model
            >>> agent = GeminiAgent(model_name="gemini-1.5-pro")
        """
        # Get API key
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise GeminiAgentError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable."
            )
        
        try:
            # Initialize Google GenAI client
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = model_name
            
            # Define tools for function calling
            self.tools = self._define_tools()
            
        except Exception as e:
            raise GeminiAgentError(f"Failed to initialize Gemini client: {e}")
    
    def _define_tools(self) -> List[types.Tool]:
        """
        Define function calling tools for the agent.
        
        These tools map to the DesktopController methods and allow
        the AI to interact with the desktop.
        
        Returns:
            List of Tool objects with function declarations.
        """
        # Define function schemas for tool calling
        move_mouse_declaration = types.FunctionDeclaration(
            name="move_mouse",
            description="Move the mouse cursor to specific coordinates on the screen. Use this to hover over elements without clicking.",
            parameters={
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate to move the mouse to (use grid overlay to determine)"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate to move the mouse to (use grid overlay to determine)"
                    },
                    "duration": {
                        "type": "number",
                        "description": "Duration of movement in seconds (default: 0.5)"
                    }
                },
                "required": ["x", "y"]
            }
        )
        
        click_element_declaration = types.FunctionDeclaration(
            name="click_element",
            description="Move mouse to coordinates and perform a click action. Use this to click buttons, links, or any clickable UI element.",
            parameters={
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate of the element to click (use grid overlay)"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate of the element to click (use grid overlay)"
                    },
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "description": "Mouse button to click (default: left)"
                    },
                    "clicks": {
                        "type": "integer",
                        "description": "Number of clicks - 1 for single click, 2 for double click (default: 1)"
                    }
                },
                "required": ["x", "y"]
            }
        )
        
        type_text_declaration = types.FunctionDeclaration(
            name="type_text",
            description="Type text using keyboard input. Use this to fill text fields, search boxes, or any text input. Make sure a text field is focused first.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to type"
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Whether to press Enter key after typing (default: false)"
                    }
                },
                "required": ["text"]
            }
        )
        
        scroll_declaration = types.FunctionDeclaration(
            name="scroll",
            description="Scroll the mouse wheel up or down. Use positive values to scroll up, negative to scroll down.",
            parameters={
                "type": "object",
                "properties": {
                    "clicks": {
                        "type": "integer",
                        "description": "Number of scroll clicks. Positive = scroll up, Negative = scroll down (e.g., -5 scrolls down)"
                    },
                    "x": {
                        "type": "integer",
                        "description": "Optional X coordinate where to scroll"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Optional Y coordinate where to scroll"
                    }
                },
                "required": ["clicks"]
            }
        )
        
        press_key_declaration = types.FunctionDeclaration(
            name="press_key",
            description="Press a specific keyboard key. Use this for special keys like Enter, Tab, Escape, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key name (e.g., 'enter', 'tab', 'esc', 'backspace', 'delete', 'up', 'down', 'left', 'right')"
                    },
                    "presses": {
                        "type": "integer",
                        "description": "Number of times to press the key (default: 1)"
                    }
                },
                "required": ["key"]
            }
        )
        
        hotkey_declaration = types.FunctionDeclaration(
            name="hotkey",
            description="Press a keyboard shortcut (combination of keys). Use this for operations like copy (Ctrl+C), paste (Ctrl+V), etc.",
            parameters={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keys to press together (e.g., ['ctrl', 'c'] for copy, ['ctrl', 'v'] for paste)"
                    }
                },
                "required": ["keys"]
            }
        )
        
        # Create Tool object with all function declarations
        tool = types.Tool(
            function_declarations=[
                move_mouse_declaration,
                click_element_declaration,
                type_text_declaration,
                scroll_declaration,
                press_key_declaration,
                hotkey_declaration
            ]
        )
        
        return [tool]
    
    def analyze_and_act(
        self,
        user_request: str,
        screenshot_path: str,
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze screenshot and determine actions based on user request.
        
        This is the main method that sends the screenshot to Gemini,
        gets function calls, and returns the actions to take.
        
        Args:
            user_request: User's instruction (e.g., "Click the login button").
            screenshot_path: Path to screenshot image with grid overlay.
            chat_history: Optional conversation history for context.
        
        Returns:
            Dictionary containing:
                - 'text_response': AI's text explanation
                - 'function_calls': List of function calls to execute
                - 'finish_reason': Reason generation stopped
        
        Raises:
            GeminiAgentError: If analysis fails.
        
        Example:
            >>> agent = GeminiAgent()
            >>> result = agent.analyze_and_act(
            ...     "Click the submit button",
            ...     "screenshot_with_grid.png"
            ... )
            >>> print(result['text_response'])
            >>> for call in result['function_calls']:
            ...     print(f"Call {call['name']} with {call['args']}")
        """
        try:
            # Upload the image
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            
            # Create the prompt with image
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=image_data,
                            mime_type="image/png"
                        ),
                        types.Part.from_text(text=user_request)
                    ]
                )
            ]
            
            # Generate response with function calling
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    tools=self.tools,
                    temperature=0.1,  # Low temperature for precise actions
                )
            )
            
            # Parse response
            result = {
                "text_response": "",
                "function_calls": [],
                "finish_reason": response.candidates[0].finish_reason
            }
            
            # Extract text and function calls
            for part in response.candidates[0].content.parts:
                if part.text:
                    result["text_response"] += part.text
                elif part.function_call:
                    result["function_calls"].append({
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args)
                    })
            
            return result
        
        except Exception as e:
            raise GeminiAgentError(f"Failed to analyze screenshot: {e}")
    
    def chat(
        self,
        message: str,
        screenshot_path: Optional[str] = None
    ) -> str:
        """
        Have a conversation with the agent (without function calling).
        
        Use this for questions or explanations without performing actions.
        
        Args:
            message: Message to send to the agent.
            screenshot_path: Optional screenshot for visual context.
        
        Returns:
            Agent's text response.
        
        Raises:
            GeminiAgentError: If chat fails.
        
        Example:
            >>> agent = GeminiAgent()
            >>> response = agent.chat(
            ...     "What do you see in this image?",
            ...     "screenshot.png"
            ... )
        """
        try:
            parts = [types.Part.from_text(text=message)]
            
            # Add image if provided
            if screenshot_path:
                with open(screenshot_path, "rb") as f:
                    image_data = f.read()
                parts.insert(0, types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/png"
                ))
            
            contents = [types.Content(role="user", parts=parts)]
            
            # Generate response without tools
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=0.7
                )
            )
            
            return response.text
        
        except Exception as e:
            raise GeminiAgentError(f"Chat failed: {e}")
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Gemini models.
        
        Returns:
            List of model names.
        
        Example:
            >>> agent = GeminiAgent()
            >>> models = agent.get_available_models()
            >>> print(models)
        """
        try:
            models = self.client.models.list()
            return [model.name for model in models]
        except Exception as e:
            raise GeminiAgentError(f"Failed to list models: {e}")
