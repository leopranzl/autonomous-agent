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
     1. `hotkey(['win', 'r'])` to open Run dialog.
     2. `type_text('chrome --force-renderer-accessibility --remote-debugging-port=9222')`.
     3. `press_key('enter')`.
     4. `wait(seconds=6)` <- MANDATORY.
   - **WHY remote-debugging-port?** Enables Playwright to connect for precise web automation via CSS selectors.

3. **APP-SPECIFIC STRATEGIES (PRIORITY):**

   **A. WEB BROWSERS (CHROME/EDGE) - NAVIGATION LOOP PREVENTION:**
   - **RULE:** Only use the Address Bar (EditControl 'Barra de endereço') if the current window title DOES NOT match your target website.
   - **ONCE REACHED:** If the window title contains the site name (e.g., "Instagram"), STOP using the Address Bar IDs (usually ID 7, 8 or any Edit with Y < 100).
   - **MANDATORY EXPLORATION:** As soon as a website loads, you MUST call `web_get_elements()` FIRST to discover CSS selectors. You cannot use web_click or web_type effectively without this.

   **B. PLAYWRIGHT WEB AUTOMATION (HIGHEST PRECISION):**
   - **When to use:** If Chrome is running AND you're interacting with a WEB PAGE.
   - **CRITICAL PRIORITY ORDER:**
     1. **FIRST CHOICE (MANDATORY):** Always use `web_click(selector)` and `web_type(selector, text)` for any interaction inside the website content.
     2. **SECOND CHOICE:** If web tools fail or you are stuck, use `click_element_by_id` from the UI Scanner list.
     3. **LAST RESORT:** Use coordinate clicking.

   **C. FILE EXPLORER (SEARCHING):**
   - Identify the Search box, call `click_element_by_id(id)` on it FIRST, then chain `type_text("query", press_enter=True)`.

   **D. FILE PICKER / UPLOAD DIALOGS:**
   - DO NOT navigate folders. Identify the "File name" Edit box, click it, and type the FULL absolute path (e.g., "C:\Users\Name\file.jpg") then press Enter.

4. **INPUT FIELD DISAMBIGUATION (CRITICAL):**
   - Website content elements (chat boxes, search fields) are positioned in the central/lower area of the screen.
   - Browser UI elements (Address bar, tabs) are at the very top (Y < 100).
   - **NEVER** type a search query into the Address Bar if you are already on the target website.

5. **REASONING BEFORE ACTING (ReAct Pattern - MANDATORY):**
   - **CRITICAL:** You MUST output your reasoning in a `thought` block BEFORE calling functions.
   - Describe: (1) What you see, (2) Current status, (3) Why these specific actions, (4) Expected outcome.
   - **Self-Correction:** If HISTORY shows the same action failed or state didn't change, try a DIFFERENT strategy (e.g., switch from ID to `web_click` or use a keyboard shortcut like `/`).

6. **HIERARCHICAL PLANNING:**
   - Focus ONLY on the "CURRENT SUB-GOAL".
   - **Transition:** If the sub-goal is complete, state 'SUB-GOAL COMPLETE' AND **immediately provide the function call(s) for the next sub-goal** in the same response.
   - NEVER return an empty list of functions if pending sub-goals exist.

RESPONSE FORMAT:
- Start with a clear thought statement.
- Follow with a list of function calls.
- Example: "I have reached Instagram. Sub-goal 2 is complete. Now starting sub-goal 3: searching. I will call web_get_elements to find the search field selector."
"""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        api_key: Optional[str] = None,
        logger: Optional[TaskLogger] = None
    ) -> None:
        """
        Initialize the Gemini agent with function calling capabilities.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise GeminiAgentError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable."
            )
        
        self.logger = logger
        
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = model_name
            self.tools = self._define_tools()
            
        except Exception as e:
            raise GeminiAgentError(f"Failed to initialize Gemini client: {e}")
    
    def _define_tools(self) -> List[types.Tool]:
        """
        Define function calling tools mapping to DesktopController and Playwright methods.
        """
        # --- Standard Desktop Tools ---
        move_mouse_declaration = types.FunctionDeclaration(
            name="move_mouse",
            description="Move the mouse cursor to specific coordinates.",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "duration": {"type": "number"}
                },
                "required": ["x", "y"]
            }
        )
        
        click_element_declaration = types.FunctionDeclaration(
            name="click_element",
            description="Perform a mouse click at coordinates.",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "clicks": {"type": "integer"}
                },
                "required": ["x", "y"]
            }
        )
        
        type_text_declaration = types.FunctionDeclaration(
            name="type_text",
            description="Type text using keyboard simulation.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "press_enter": {"type": "boolean"}
                },
                "required": ["text"]
            }
        )
        
        scroll_declaration = types.FunctionDeclaration(
            name="scroll",
            description="Scroll the mouse wheel.",
            parameters={
                "type": "object",
                "properties": {
                    "clicks": {"type": "integer"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"}
                },
                "required": ["clicks"]
            }
        )
        
        press_key_declaration = types.FunctionDeclaration(
            name="press_key",
            description="Press a specific keyboard key (enter, tab, esc, etc.).",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "presses": {"type": "integer"}
                },
                "required": ["key"]
            }
        )
        
        hotkey_declaration = types.FunctionDeclaration(
            name="hotkey",
            description="Press a combination of keys (e.g., ['ctrl', 'c']).",
            parameters={
                "type": "object",
                "properties": {
                    "keys": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["keys"]
            }
        )
        
        click_element_by_id_declaration = types.FunctionDeclaration(
            name="click_element_by_id",
            description="Click a UI element using its numeric ID from the Set-of-Marks list.",
            parameters={
                "type": "object",
                "properties": {
                    "element_id": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "clicks": {"type": "integer"}
                },
                "required": ["element_id"]
            }
        )
        
        wait_declaration = types.FunctionDeclaration(
            name="wait",
            description="Pause execution. Mandatory after launching browsers.",
            parameters={
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer"}
                },
                "required": ["seconds"]
            }
        )
        
        # --- Playwright Precise Web Tools ---
        web_click_declaration = types.FunctionDeclaration(
            name="web_click",
            description="PRECISE WEB CLICK: Click a web element using a CSS selector via Playwright.",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "timeout": {"type": "integer"}
                },
                "required": ["selector"]
            }
        )
        
        web_type_declaration = types.FunctionDeclaration(
            name="web_type",
            description="PRECISE WEB TYPING: Type text into a web input using a CSS selector via Playwright.",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                    "press_enter": {"type": "boolean"},
                    "timeout": {"type": "integer"}
                },
                "required": ["selector", "text"]
            }
        )
        
        web_get_elements_declaration = types.FunctionDeclaration(
            name="web_get_elements",
            description="MANDATORY DISCOVERY: Retrieve interactive elements and selectors from the current web page.",
            parameters={
                "type": "object",
                "properties": {
                    "max_elements": {"type": "integer"}
                },
                "required": []
            }
        )
        
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

    def generate_plan(self, user_request: str, screenshot_path: Optional[str] = None) -> List[str]:
        """
        Decomposes a complex user request into a numbered list of sub-goals.
        """
        try:
            planning_prompt = f"""Break down the following task into sequential sub-goals.
Output ONLY a numbered list (1., 2., ...).
TASK: {user_request}"""
            
            parts = [types.Part.from_text(text=planning_prompt)]
            if screenshot_path:
                with open(screenshot_path, "rb") as f:
                    image_data = f.read()
                parts.insert(0, types.Part.from_bytes(data=image_data, mime_type="image/png"))
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(temperature=0.3)
            )
            
            plan = []
            for line in response.text.split('\n'):
                line = line.strip()
                if any(line.startswith(f"{i}.") for i in range(1, 20)):
                    clean_line = line.split('.', 1)[1].strip()
                    plan.append(clean_line)
            
            if self.logger:
                self.logger.log_data("GENERATED PLAN", {"plan": plan}, format_json=True)
            return plan if plan else [user_request]
        except Exception:
            return [user_request]

    def analyze_and_act(
        self,
        user_request: str,
        screenshot_path: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        detected_elements: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Sends the screenshot and context to Gemini to determine the next set of actions.
        """
        try:
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            
            context_str = ""
            if detected_elements:
                context_str += "DETECTED UI ELEMENTS (Set-of-Marks):\n"
                for el in detected_elements[:50]: 
                    context_str += f"[{el['id']}] {el['type']} '{el.get('name', 'Unknown')}'\n"
                context_str += "-" * 40 + "\n\n"
            
            if chat_history:
                context_str += "HISTORY OF PREVIOUS ACTIONS:\n"
                for turn in chat_history[-5:]:
                    if turn.get('function_calls'):
                        for call in turn['function_calls']:
                            context_str += f"- Action: {call['name']} args={call['args']}\n"
                    if turn.get('execution_results'):
                        for result in turn['execution_results']:
                             context_str += f"  Result: {result}\n"
                context_str += "-" * 40 + "\n\n"

            full_prompt = context_str + "USER REQUEST: " + user_request

            if self.logger:
                self.logger.log_prompt(full_prompt, "FULL_CONTEXT")

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_data, mime_type="image/png"),
                            types.Part.from_text(text=full_prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    tools=self.tools,
                    temperature=0.1, 
                )
            )
            
            # Safe parsing of tool calls
            result = {"text_response": "", "function_calls": [], "finish_reason": "UNKNOWN"}
            if response.candidates:
                result["finish_reason"] = response.candidates[0].finish_reason
                parts = response.candidates[0].content.parts or []
                for part in parts:
                    if part.text:
                        result["text_response"] += part.text
                    elif part.function_call:
                        result["function_calls"].append({
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args)
                        })
            
            if self.logger:
                self.logger.log_ai_response(result)
            return result
        except Exception as e:
            raise GeminiAgentError(f"Analysis failed: {e}")

    def chat(self, message: str, screenshot_path: Optional[str] = None) -> str:
        """
        Simple text conversation with visual context.
        """
        try:
            parts = [types.Part.from_text(text=message)]
            if screenshot_path:
                with open(screenshot_path, "rb") as f:
                    image_data = f.read()
                parts.insert(0, types.Part.from_bytes(data=image_data, mime_type="image/png"))
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(system_instruction=self.SYSTEM_INSTRUCTION, temperature=0.7)
            )
            return response.text
        except Exception as e:
            raise GeminiAgentError(f"Chat failed: {e}")