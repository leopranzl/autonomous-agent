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
    SYSTEM_INSTRUCTION = r"""You are an expert AI Agent capable of controlling a Windows PC.

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
     2. `type_text('chrome --force-renderer-accessibility --remote-debugging-port=9222')`
     3. `press_key('enter')`
     4. **`wait(seconds=3)`** <- MANDATORY. Chrome needs time to load.
   - **WHY?** The `--force-renderer-accessibility` flag forces Chrome to expose HTML elements (buttons, links, forms) to the UI Scanner. Without this, you cannot see or click webpage elements by ID.
   - **WHY remote-debugging-port?** Enables Playwright to connect for precise web automation via CSS selectors.
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

   **C. FILE PICKER / UPLOAD DIALOGS (MANDATORY):**
   - **Scenario:** You see a Windows File Explorer dialog (titles like "Open", "Abrir", "Save As", "Salvar como").
   - **Goal:** Select a specific file for upload or opening.
   - **STRATEGY:** DO NOT click folders to navigate. DO NOT search for file icons visually.
     1. Identify the `EditControl` labeled "File name:", "Nome do arquivo:", "Nome:", or just a text box near the bottom of the dialog.
     2. **Action 1:** `click_element_by_id(id)` on this file name text box to focus it.
     3. **Action 2:** `type_text("C:\\Full\\Path\\To\\File.ext", press_enter=True)` with the COMPLETE absolute path.
   - **Reasoning:** Typing the absolute path is 100% reliable, instant, and skips all navigation steps. No need to traverse Desktop → Pictures → Subfolder.
   - **Example:** Instead of clicking through folders, just type: `C:\Users\Username\Pictures\photo.jpg`

   **D. WEB APP SEARCHING (KEYBOARD SHORTCUTS - PRIORITY):**
   - **Scenario:** User wants to search INSIDE a website like LinkedIn, YouTube, Gmail, Twitter/X, GitHub, Reddit.
   - **Problem:** Clicking search bars visually is fragile (coordinates shift, IDs change, click misses target).
   - **SOLUTION:** Use the universal `/` (forward slash) keyboard shortcut.
   - **STRATEGY:**
     1. **DO NOT** try to click the search bar element visually.
     2. **Action 1:** `type_text("/")` - This instantly focuses the search bar on most modern web apps.
     3. **Action 2:** `wait(1)` - Brief pause for focus animation to complete.
     4. **Action 3:** `type_text("your search query", press_enter=True)` - Type and submit.
   - **Why this works:** The `/` shortcut is hardcoded into these sites' JavaScript and is 100% reliable regardless of page layout changes.
   - **Supported sites:** LinkedIn, YouTube, Gmail, Twitter/X, GitHub, Reddit, Facebook, Instagram (when logged in).
   - **Example:** To search LinkedIn for "AI Engineer jobs":
     ```
     type_text("/")
     wait(1)
     type_text("AI Engineer jobs", press_enter=True)
     ```

   **E. PLAYWRIGHT WEB AUTOMATION (HIGHEST PRECISION - USE WHEN AVAILABLE):**
   - **When to use:** If Chrome is running AND you're interacting with a WEB PAGE (not Windows UI).
   - **Advantages:** CSS selectors are more reliable than visual clicking. Works even when page layout changes.
   - **Priority Order:**
     1. **FIRST CHOICE:** Use `web_click(selector)` and `web_type(selector, text)` for web interactions.
     2. **FALLBACK:** If web tools fail or element has no good selector, use `click_element_by_id`.
     3. **LAST RESORT:** Use coordinate clicking only if both above fail.
   - **How to get selectors:**
     - Call `web_get_elements()` to see available interactive elements with their selectors.
     - Or construct selectors manually: `button:has-text("Login")`, `input[name="email"]`, `#submit-btn`.
   - **Example workflow:**
     ```
     web_click('button:has-text("Sign In")')
     web_type('input[name="email"]', 'user@example.com')
     web_type('input[type="password"]', 'mypassword', press_enter=True)
     ```
   - **Important:** These tools ONLY work when Chrome is launched with `--remote-debugging-port=9222`.

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

7. **REASONING BEFORE ACTING (ReAct Pattern - MANDATORY):**
   - **CRITICAL:** You MUST output your reasoning/thought process BEFORE calling functions.
   - First, provide a `thought` text block explaining:
     1. What you observe in the screenshot.
     2. What the current state is.
     3. Why you're choosing specific actions.
     4. What you expect to happen.
   - Then, call the appropriate functions.
   - **Self-Correction:** If you notice HISTORY shows repeated failures or no state change, you MUST try a different approach:
     - If `click_element_by_id` failed → try coordinate clicking
     - If clicking failed → try keyboard shortcuts
     - If typing had no effect → explicitly click to focus first
     - If stuck → try scrolling or pressing Escape to reset

8. **HIERARCHICAL PLANNING (FOR COMPLEX TASKS):**
   - **When you receive a PLAN:** You will see "CURRENT PLAN" and "CURRENT SUB-GOAL" in the context.
   - **Your responsibility:** Focus ONLY on completing the current sub-goal. Ignore other sub-goals for now.
   - **Plan awareness:**
     - Understand where you are in the overall task (e.g., "Step 2 of 5").
     - Check if the current sub-goal is achievable given the current screen state.
     - If the sub-goal is complete, state "SUB-GOAL COMPLETE" in your response.
   - **Re-planning trigger:**
     - If the current sub-goal is IMPOSSIBLE (e.g., "Click button X" but button X doesn't exist), state "SUB-GOAL IMPOSSIBLE: [reason]".
     - The system will re-plan automatically.
   - **Example:**
     - Plan: ["1. Open Chrome", "2. Navigate to Gmail", "3. Click Compose", "4. Write email"]
     - Current Sub-goal: "2. Navigate to Gmail"
     - Your focus: Only work on navigating to Gmail. Once URL bar shows gmail.com, say "SUB-GOAL COMPLETE".

RESPONSE FORMAT:
- Start with a clear thought/reasoning statement.
- If working on a sub-goal, mention your progress.
- Follow with a list of function calls.
- Example: "I can see Chrome is open with the address bar visible (element #5). I will click it to focus, then type the URL."
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
        
        # Playwright Web Automation Tools
        web_click_declaration = types.FunctionDeclaration(
            name="web_click",
            description="PRECISE WEB CLICK: Click a web element using CSS selector (Playwright). PREFERRED over coordinate clicking for web pages. Works only when Chrome is running with --remote-debugging-port=9222. More reliable than visual clicking for dynamic web content.",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector of the element to click (e.g., 'button.submit', '#login-btn', 'a[href=\"/home\"]')"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum wait time in milliseconds (default: 5000)"
                    }
                },
                "required": ["selector"]
            }
        )
        
        web_type_declaration = types.FunctionDeclaration(
            name="web_type",
            description="PRECISE WEB TYPING: Type text into a web input field using CSS selector (Playwright). PREFERRED over regular typing for web forms. Works only when Chrome is running with --remote-debugging-port=9222.",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector of the input element (e.g., 'input[name=\"email\"]', '#search-box', 'textarea.message')"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type into the field"
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Whether to press Enter after typing (default: false)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum wait time in milliseconds (default: 5000)"
                    }
                },
                "required": ["selector", "text"]
            }
        )
        
        web_get_elements_declaration = types.FunctionDeclaration(
            name="web_get_elements",
            description="GET WEB ELEMENTS: Retrieve interactive web elements from current page using Playwright accessibility tree. Returns list of clickable/typeable elements with their selectors. Use this to discover available actions on a web page.",
            parameters={
                "type": "object",
                "properties": {
                    "max_elements": {
                        "type": "integer",
                        "description": "Maximum number of elements to return (default: 50)"
                    }
                },
                "required": []
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
                wait_declaration,
                web_click_declaration,
                web_type_declaration,
                web_get_elements_declaration
            ]
        )
        
        return [tool]
    
    def generate_plan(
        self,
        user_request: str,
        screenshot_path: Optional[str] = None
    ) -> List[str]:
        """
        Generate a hierarchical plan (list of sub-goals) for a complex task.
        
        Args:
            user_request: High-level task description.
            screenshot_path: Optional screenshot for context.
        
        Returns:
            List of sub-goal strings (e.g., ["Open Chrome", "Navigate to site", ...]).
        
        Example:
            >>> agent = GeminiAgent()
            >>> plan = agent.generate_plan("Send an email to John about the meeting")
            >>> # Returns: ["1. Open Chrome", "2. Navigate to Gmail", "3. Click Compose", ...]
        """
        try:
            planning_prompt = f"""You are a task planning AI. Given a high-level task, break it down into a sequential list of concrete sub-goals.

RULES:
1. Each sub-goal should be a single, achievable action.
2. Number each sub-goal (1., 2., 3., ...).
3. Be specific (e.g., "Open Chrome" not "Open browser").
4. Keep it under 10 steps if possible.
5. Focus on USER-FACING actions, not implementation details.

TASK: {user_request}

Generate the plan as a numbered list. Output ONLY the numbered list, nothing else.
"""
            
            parts = [types.Part.from_text(text=planning_prompt)]
            
            # Add screenshot if provided for context
            if screenshot_path:
                with open(screenshot_path, "rb") as f:
                    image_data = f.read()
                parts.insert(0, types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/png"
                ))
            
            contents = [types.Content(role="user", parts=parts)]
            
            # Generate plan without function calling
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.3  # Lower temperature for more consistent planning
                )
            )
            
            # Parse the response into a list of sub-goals
            plan_text = response.text
            lines = [line.strip() for line in plan_text.split('\n') if line.strip()]
            
            # Extract numbered items
            plan = []
            for line in lines:
                # Match patterns like "1.", "1)", "Step 1:", etc.
                if any(line.startswith(f"{i}.") or line.startswith(f"{i})") or line.startswith(f"Step {i}") for i in range(1, 20)):
                    # Clean up the numbering
                    clean_line = line
                    for prefix in ["Step ", "step "]:
                        if prefix in clean_line:
                            clean_line = clean_line.split(prefix, 1)[1]
                    # Remove leading numbers and punctuation
                    for i in range(20):
                        for sep in [f"{i}. ", f"{i}) ", f"{i}: "]:
                            if clean_line.startswith(sep):
                                clean_line = clean_line[len(sep):]
                    plan.append(clean_line)
            
            # Log the generated plan
            if self.logger:
                self.logger.log_data(
                    "GENERATED PLAN",
                    {"task": user_request, "plan": plan},
                    format_json=True
                )
            
            return plan if plan else [user_request]  # Fallback to original task if parsing fails
            
        except Exception as e:
            # If planning fails, return the original task as a single-step plan
            if self.logger:
                self.logger.log_error("PlanGenerationError", str(e))
            return [user_request]
    
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
