"""
AI Agent Brain Module
Google Gemini-powered autonomous agent with function calling.
"""

from typing import Optional, Dict, List, Any
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.utils.logger import TaskLogger

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
    SYSTEM_INSTRUCTION = """You are an expert AI Agent capable of controlling a Windows PC.

**ZERO STATE RULE (HIGHEST PRIORITY):**
- If the user asks for a website (Instagram, YouTube, Google, etc.) AND you clearly see the Desktop (wallpaper, icons, empty screen):
  **IMMEDIATELY** execute the 'Open Chrome' sequence.
- If you see the Desktop but the task requires an app (e.g., "open notepad"), launch it via Win+R or Start Menu.
- **NEVER** return an empty response. If confused, default to opening the required application.

CORE OPERATING RULES:
1. **CHAINING COMMANDS (MANDATORY):**
   - EFFICIENCY IS KEY. Never perform a single action if you can chain them.
   - Example: Multiple actions in ONE response.

2. **OPENING CHROME WITH ACCESSIBILITY (CRITICAL):**
   - **NEVER** open Chrome via Start Menu search.
   - **ALWAYS** use this exact sequence (ALL IN ONE RESPONSE):
     1. `hotkey(['win', 'r'])` to open Run dialog
     2. `type_text('chrome --force-renderer-accessibility')`
     3. `press_key('enter')`
     4. **`wait(seconds=6)`** <- MANDATORY. Chrome needs time to load.
   - **WHY?** The `--force-renderer-accessibility` flag forces Chrome to expose HTML elements (buttons, links, forms) to the UI Scanner. Without this, you cannot see or click webpage elements by ID.
   - **WHY wait?** If you scan the screen immediately after launching, Chrome is still loading (blank window). The wait prevents scanning a blank screen and losing focus.
   - This applies to ALL Chrome-related tasks (browsing websites, Instagram, YouTube, etc.).

3. **APP-SPECIFIC STRATEGIES (PRIORITY):**

   **A. FILE EXPLORER (SEARCHING):**
   - If the user wants to SEARCH for a file/folder:
     1. Look for an `EditControl` named "Search...", "Pesquisar...", or "Search box".
     2. **CRITICAL:** You MUST call `click_element_by_id(id)` on that search box FIRST.
     3. THEN chain `type_text("query", press_enter=True)`.
   - Do NOT just type blindly. It will not search.

   **B. WEB BROWSERS (CHROME/EDGE):**
   - **Profile Picker:** If you see "Person 1"/"Guest", click the profile ID. Do NOT type URL.
   - **Navigation:** If you see the browser is open:
     1. Identify the Address Bar (usually `EditControl` 'Address and search bar' or 'Barra de endereços').
     2. Call `click_element_by_id(id)` on it to focus.
     3. Chain `type_text("url", press_enter=True)`.

4. **INPUT FIELD DISAMBIGUATION (CRITICAL):**
   - **SCENARIO:** You see multiple text boxes (e.g., a website's search bar vs. the Browser's Address Bar).
   - **RULE:** If the user wants to **GO TO A WEBSITE** (e.g., "open instagram", "go to youtube"):
     - You MUST target the **BROWSER CHROME ELEMENTS** (Top of the window).
     - Look for keywords in the Element Name: `'Address'`, `'Barra de endereço'`, `'Search or enter web address'`, `'Address and search bar'`.
     - **NEVER** type a URL into a field named `'Search'`, `'Chat'`, `'Message'`, `'Input'`, `'Ask'`, `'Type here'`, or `'Send a message'` unless it is explicitly the address bar.
   
   - **ANALYTICAL SELECTION:**
     - If you are unsure which ID is the address bar, look for the element with `ControlTypeName: Edit` located at the **very top of the screen** (usually Y coordinate < 100).
     - Browser chrome elements (address bar, tabs) are positioned in the window's header area.
     - Web page content elements (chat boxes, search fields) are positioned in the central/lower area.
   
   - **CORRECTION STRATEGY:**
     - If you typed into the wrong field, in your next turn:
       1. Explicitly identify the correct Address Bar element by analyzing its Name and Position.
       2. Call `click_element_by_id(id)` on the correct address bar.
       3. Clear any wrong input with `hotkey(['ctrl', 'a'])` then `press_key('backspace')`.
       4. Type the correct URL with `type_text("url", press_enter=True)`.

5. **VISUAL NAVIGATION (Set-of-Marks):**
   - You will receive a text list of "DETECTED UI ELEMENTS" with IDs.
   - **ALWAYS PREFER** using `click_element_by_id(element_id)` over coordinate clicks.
   - **Reading the List:** Look for keywords in the element names (e.g., 'Submit', 'Search', 'Pesquisar').
   - If an element seems to be a container (like a list item), clicking it selects it.

6. **ERROR RECOVERY:**
   - Review the `HISTORY`. If you tried typing and nothing happened, assume you lost focus.
   - **Correction:** Click the target input field explicitly in the next turn.

RESPONSE FORMAT:
- Return a list of function calls.
"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        api_key: Optional[str] = None,
        logger: Optional[TaskLogger] = None
    ) -> None:
        """
        Initialize the Gemini agent with function calling capabilities.
        
        Args:
            model_name: Gemini model to use. Default is "gemini-2.0-flash-exp".
            api_key: Google API key. If None, loads from GOOGLE_API_KEY env var.
            logger: Optional TaskLogger instance for execution tracing.
        
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
        
        # Store logger
        self.logger = logger
        
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
        
        click_element_by_id_declaration = types.FunctionDeclaration(
            name="click_element_by_id",
            description="PRECISE CLICK: Click a specific UI element by its numeric ID tag shown in the screenshot. PREFERRED over coordinate clicking when numbered tags are visible. The element ID comes from the Set-of-Marks visualization (green boxes with numbers).",
            parameters={
                "type": "object",
                "properties": {
                    "element_id": {
                        "type": "integer",
                        "description": "The numeric ID of the element to click (e.g., 1, 2, 3... as shown in the screenshot tags)"
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
                "required": ["element_id"]
            }
        )
        
        wait_declaration = types.FunctionDeclaration(
            name="wait",
            description="Pause execution for a specified duration. CRITICAL: MUST be called immediately after launching heavy applications (Chrome, Spotify, Visual Studio, etc.) to allow them to fully load and render before the next action. Prevents race conditions and blank screen scans.",
            parameters={
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "Number of seconds to wait. Use 5-8 seconds for browsers, 3-5 for lightweight apps."
                    }
                },
                "required": ["seconds"]
            }
        )
        
        # Create Tool object with all function declarations
        tool = types.Tool(
            function_declarations=[
                move_mouse_declaration,
                click_element_declaration,
                click_element_by_id_declaration,
                type_text_declaration,
                scroll_declaration,
                press_key_declaration,
                hotkey_declaration,
                wait_declaration
            ]
        )
        
        return [tool]
    
    def analyze_and_act(
        self,
        user_request: str,
        screenshot_path: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        detected_elements: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze screenshot and determine actions based on user request.
        """
        try:
            # Upload the image
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            
            # --- CONSTRUÇÃO DO CONTEXTO (PROMPT) ---
            context_str = ""
            
            # 1. Adiciona Elementos Detectados (Set-of-Marks)
            if detected_elements:
                context_str += "DETECTED UI ELEMENTS (Set-of-Marks):\n"
                context_str += "Use `click_element_by_id(id)` for these elements.\n"
                # Limita a 50 elementos para não estourar o contexto ou confundir o modelo
                for el in detected_elements[:50]: 
                    # Ex: [1] Button 'Aceitar'
                    context_str += f"[{el['id']}] {el['type']} '{el.get('name', 'Unknown')}'\n"
                context_str += "-" * 40 + "\n\n"
            
            # 2. Adiciona Histórico
            if chat_history:
                context_str += "HISTORY OF PREVIOUS ACTIONS:\n"
                for turn in chat_history[-5:]: # Mantém apenas os últimos 5 passos
                    if turn.get('function_calls'):
                        for call in turn['function_calls']:
                            context_str += f"- Action: {call['name']} args={call['args']}\n"
                    if turn.get('execution_results'):
                        for result in turn['execution_results']:
                             context_str += f"  Result: {result}\n"
                context_str += "If the last action failed, try a different approach.\n"
                context_str += "-" * 40 + "\n\n"

            full_prompt = context_str + "USER REQUEST: " + user_request

            # LOG: Capture the complete prompt before sending (CRITICAL for debugging)
            if self.logger:
                self.logger.log_prompt(full_prompt, "FULL_CONTEXT")
                self.logger.log_step(
                    "Sending to Gemini API",
                    f"Model: {self.model_name}\nTemperature: 0.1\nWith screenshot and {len(self.tools)} function tools"
                )

            # Create content
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=image_data,
                            mime_type="image/png"
                        ),
                        types.Part.from_text(text=full_prompt)
                    ]
                )
            ]
            
            # Generate response
            print("   🧠 Sending request to Gemini...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    tools=self.tools,
                    temperature=0.1, 
                )
            )
            
            # --- CORREÇÃO DE ERRO (NoneType) ---
            # Verifica se a resposta foi bloqueada ou veio vazia
            if not response.candidates or not response.candidates[0].content:
                finish_reason = "UNKNOWN"
                if response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                
                print(f"   ⚠️ Gemini returned empty response. Finish Reason: {finish_reason}")
                
                # LOG: Record the empty response error
                if self.logger:
                    self.logger.log_error(
                        "GeminiEmptyResponse",
                        f"Finish Reason: {finish_reason}\nUser Request: {user_request}"
                    )
                
                # Check if user is requesting a website
                website_keywords = ["http", "www", ".com", ".org", "instagram", "youtube", 
                                   "facebook", "google", "twitter", "site", "website"]
                is_website_request = any(keyword in user_request.lower() for keyword in website_keywords)
                
                if is_website_request:
                    # Hardcoded reflex: Open Chrome when website requested but response is empty
                    print("   💡 Detected website request - injecting Chrome launch sequence")
                    return {
                        "text_response": "I see a request for a website but the response was blocked. I will open Chrome now.",
                        "function_calls": [
                            {"name": "hotkey", "args": {"keys": ["win", "r"]}},
                            {"name": "type_text", "args": {"text": "chrome --force-renderer-accessibility"}},
                            {"name": "press_key", "args": {"key": "enter"}},
                            {"name": "wait", "args": {"seconds": 6}}
                        ],
                        "finish_reason": finish_reason
                    }
                
                # Generic fallback for other blocked responses
                return {
                    "text_response": "I couldn't analyze the screen due to safety filters or an error. I will retry.",
                    "function_calls": [],
                    "finish_reason": finish_reason
                }

            # Parse response seguro
            result = {
                "text_response": "",
                "function_calls": [],
                "finish_reason": response.candidates[0].finish_reason
            }
            
            # Garante que 'parts' é iterável
            parts = response.candidates[0].content.parts or []
            
            for part in parts:
                if part.text:
                    result["text_response"] += part.text
                elif part.function_call:
                    result["function_calls"].append({
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args)
                    })
            
            # LOG: Capture the raw response (CRITICAL for debugging)
            if self.logger:
                self.logger.log_ai_response(result)
            
            return result
        
        except Exception as e:
            # Log de erro detalhado
            print(f"   ❌ Error details: {str(e)}")
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
