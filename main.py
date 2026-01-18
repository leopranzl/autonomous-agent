"""
Autonomous AI Agent using Google Gemini
Entry point for the application - orchestrates vision, action, and AI components
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

from src.vision.capture import ScreenCapture, ScreenCaptureError
from src.vision.scanner import UIScanner, UIScannerError
from src.action.controller import DesktopController, DesktopControllerError
from src.agent.brain import GeminiAgent, GeminiAgentError
from src.utils.logger import TaskLogger
import ctypes

# Forçar o Windows a reportar a resolução real para o Python
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()


# Configuration
MAX_ITERATIONS = 15  # Prevent infinite loops and cost overruns
SCREENSHOT_PATH = "temp_screenshot.png"


class AutonomousAgent:
    """
    Autonomous AI Agent orchestrator.
    
    Coordinates screen capture, AI analysis, and desktop control
    in a continuous loop until task completion.
    """
    
    def __init__(self):
        """Initialize all agent components."""
        print("🤖 Autonomous AI Agent - Initializing...")
        print("=" * 60)
        
        # Load environment variables
        load_dotenv()
        
        # Initialize logger (CRITICAL for debugging)
        self.logger = TaskLogger()
        print(f"   📝 Log file: {self.logger.get_log_path()}")
        self.logger.log_step("System Initialization", "Starting Autonomous AI Agent")
        
        # Verify API key
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError(
                "❌ GOOGLE_API_KEY not found!\n"
                "Please set it in your .env file:\n"
                "1. Copy .env.example to .env\n"
                "2. Add your Google Gemini API key"
            )
        
        # Initialize screen capture
        print("📸 Initializing screen capture...")
        self.screen_capture = ScreenCapture(
            grid_spacing=50,  # ALTA PRECISÃO: Mudado de 100 para 50
            grid_color=(255, 0, 0),
            grid_alpha=180
        )
        
        # Get screen info
        monitor_info = self.screen_capture.get_monitor_info()
        screen_width = monitor_info["width"]
        screen_height = monitor_info["height"]
        print(f"   Screen resolution: {screen_width}x{screen_height}")
        
        # Initialize desktop controller with coordinate scaling
        # AI will analyze full-res images (no downscaling for now)
        print("🖱️  Initializing desktop controller...")
        self.controller = DesktopController(
            ai_image_width=screen_width,
            ai_image_height=screen_height,
            action_delay=0.5,
            failsafe=True
        )
        print("   ⚠️  Failsafe enabled: Move mouse to corner to abort!")
        
        # Initialize Gemini agent
        print("🧠 Initializing Google Gemini agent...")
        try:
            self.agent = GeminiAgent(
                model_name="gemini-2.5-flash",
                logger=self.logger
            )
            print(f"   Model: gemini-2.5-flash")
            self.logger.log_step("Gemini Agent", "Initialized with gemini-2.5-flash")
        except GeminiAgentError:
            print("   Fallback to: gemini-1.5-pro")
            self.agent = GeminiAgent(
                model_name="gemini-1.5-pro",
                logger=self.logger
            )
            self.logger.log_step("Gemini Agent", "Fallback to gemini-1.5-pro")
        
        # Initialize UI Scanner for element detection
        print("🔍 Initializing UI Scanner...")
        self.ui_scanner = UIScanner(
            min_visible_area=25,
            max_depth=15
        )
        print("   Set-of-Marks mode available")
        
        # Conversation history
        self.history: List[Dict[str, Any]] = []
        
        # Current detected elements (for ID-to-coordinate mapping)
        self.current_elements: List[Dict[str, Any]] = []
        
        # State tracking for self-correction (ReAct pattern)
        self.previous_screenshot_path: Optional[str] = None
        self.stuck_count: int = 0  # Count consecutive iterations with no state change
        self.last_action_signature: Optional[str] = None  # Track repeated actions
        
        # Hierarchical planning state
        self.plan: Optional[List[str]] = None  # Current plan (list of sub-goals)
        self.current_subgoal_index: int = 0  # Index of current sub-goal
        self.subgoal_attempts: int = 0  # Number of attempts on current sub-goal
        self.max_subgoal_attempts: int = 5  # Max attempts before re-planning
        
        print("=" * 60)
        print("✅ Initialization complete!\n")
    
    def capture_screen(self) -> tuple[str, List[Dict[str, Any]]]:
        """
        Hybrid screen capture: Try UI Automation first, fallback to Grid.
        
        Returns:
            Tuple of (screenshot_path, detected_elements_list)
        """
        try:
            # Step 1: Capture raw screenshot
            print("📸 Capturing screen...")
            raw_image = self.screen_capture.capture()
            
            # Step 2: Try UI Automation (Set-of-Marks mode)
            detected_elements = []
            try:
                print("🔍 Scanning UI elements...")
                detected_elements = self.ui_scanner.scan_active_window()
                
                if detected_elements:
                    # MODE A: Set-of-Marks - Draw numbered boxes
                    print(f"   ✅ Found {len(detected_elements)} elements - Using Set-of-Marks mode")
                    
                    # LOG: What the agent "sees"
                    self.logger.log_ui_elements(detected_elements, "Set-of-Marks")
                    
                    annotated_image = self.ui_scanner.draw_ui_overlay(
                        raw_image,
                        detected_elements,
                        api_color=(0, 255, 0),  # Corrigido
                        show_labels=True
)
                    annotated_image.save(SCREENSHOT_PATH)
                    
                    # Print element summary
                    print("   Detected elements:")
                    for elem in detected_elements[:5]:  # Show first 5
                        print(f"     #{elem['id']}: {elem['type']} - '{elem['name'][:30]}'")
                    if len(detected_elements) > 5:
                        print(f"     ... and {len(detected_elements) - 5} more")
                    
                    return SCREENSHOT_PATH, detected_elements
                    
            except UIScannerError as e:
                print(f"   ⚠️  UI Scanner failed: {e}")
            except Exception as e:
                print(f"   ⚠️  UI Scanner error: {e}")
            
            # Step 3: Fallback to Grid Mode (no elements found or scan failed)
            if not detected_elements:
                print("   ℹ️  No UI elements detected - Using Grid mode (fallback)")
                
                # LOG: Mode decision
                self.logger.log_step(
                    "Mode Decision", 
                    "Falling back to Grid mode (no UI elements detected or scan failed)"
                )
                
                grid_image = self.screen_capture.add_grid_overlay(raw_image)
                grid_image.save(SCREENSHOT_PATH)
            
            print(f"   Saved to: {SCREENSHOT_PATH}")
            return SCREENSHOT_PATH, detected_elements
            
        except ScreenCaptureError as e:
            print(f"❌ Screen capture failed: {e}")
            raise
    
    def _compare_screenshots(self, current_path: str, previous_path: Optional[str]) -> bool:
        """
        Compare two screenshots to detect if UI state has changed.
        
        Args:
            current_path: Path to current screenshot.
            previous_path: Path to previous screenshot (or None for first iteration).
        
        Returns:
            True if screenshots are significantly different, False if nearly identical.
        """
        if not previous_path or not os.path.exists(previous_path):
            return True  # First iteration or no previous screenshot
        
        try:
            from PIL import Image
            import numpy as np
            
            # Load images
            current_img = Image.open(current_path).convert('RGB')
            previous_img = Image.open(previous_path).convert('RGB')
            
            # Resize to same size if needed
            if current_img.size != previous_img.size:
                previous_img = previous_img.resize(current_img.size)
            
            # Convert to numpy arrays
            current_array = np.array(current_img)
            previous_array = np.array(previous_img)
            
            # Calculate pixel difference
            diff = np.abs(current_array.astype(float) - previous_array.astype(float))
            diff_percentage = (np.sum(diff) / diff.size) / 255.0 * 100
            
            # Threshold: If less than 2% change, consider it "stuck"
            CHANGE_THRESHOLD = 2.0
            has_changed = diff_percentage > CHANGE_THRESHOLD
            
            if not has_changed:
                print(f"   ⚠️  State comparison: Only {diff_percentage:.2f}% change detected (threshold: {CHANGE_THRESHOLD}%)")
            
            return has_changed
            
        except Exception as e:
            print(f"   ⚠️  Screenshot comparison failed: {e}")
            return True  # Assume change if comparison fails
    
    def execute_function_call(self, function_call: Dict[str, Any]) -> str:
        """
        Execute a function call from the AI agent.
        
        Args:
            function_call: Dictionary with 'name' and 'args' keys.
        
        Returns:
            Result message describing what was executed.
        """
        name = function_call["name"]
        args = function_call["args"]
        
        print(f"🔧 Executing: {name}({args})")
        
        try:
            if name == "move_mouse":
                x = args["x"]
                y = args["y"]
                duration = args.get("duration", 0.5)
                self.controller.move_mouse(x, y, duration=duration)
                return f"Moved mouse to ({x}, {y})"
            
            elif name == "click_element":
                x = args["x"]
                y = args["y"]
                button = args.get("button", "left")
                clicks = args.get("clicks", 1)
                self.controller.click_element(x, y, button=button, clicks=clicks)
                click_type = "double-clicked" if clicks == 2 else f"{button}-clicked"
                return f"{click_type.capitalize()} at ({x}, {y})"
            
            elif name == "type_text":
                text = args["text"]
                press_enter = args.get("press_enter", False)
                self.controller.type_text(text, press_enter=press_enter)
                enter_msg = " and pressed Enter" if press_enter else ""
                return f"Typed: '{text}'{enter_msg}"
            
            elif name == "scroll":
                clicks = args["clicks"]
                x = args.get("x")
                y = args.get("y")
                self.controller.scroll(clicks, x=x, y=y)
                direction = "up" if clicks > 0 else "down"
                return f"Scrolled {direction} {abs(clicks)} clicks"
            
            elif name == "press_key":
                key = args["key"]
                presses = args.get("presses", 1)
                self.controller.press_key(key, presses=presses)
                return f"Pressed '{key}' key {presses} time(s)"
            
            elif name == "hotkey":
                keys = args["keys"]
                self.controller.hotkey(*keys)
                hotkey_str = "+".join(keys)
                return f"Pressed hotkey: {hotkey_str}"
            
            elif name == "wait":
                seconds = args["seconds"]
                print(f"   ⏳ Waiting {seconds} seconds for app to load...")
                self.controller.wait(seconds)
                return f"Waited for {seconds} seconds"
            
            elif name == "click_element_by_id":
                # Validate element_id is integer
                element_id = args.get("element_id")
                
                # Handle string to int conversion if needed
                if isinstance(element_id, str):
                    try:
                        element_id = int(element_id)
                        print(f"   ⚠️  Converted element_id from string '{args['element_id']}' to integer {element_id}")
                        self.logger.log_step(
                            "Type Conversion Warning",
                            f"element_id was a string, converted to integer: {element_id}"
                        )
                    except ValueError:
                        error_msg = f"Invalid element_id: '{element_id}' is not a valid integer"
                        print(f"   ❌ {error_msg}")
                        self.logger.log_error("InvalidElementID", error_msg)
                        return error_msg
                
                if not isinstance(element_id, int):
                    error_msg = f"Invalid element_id type: {type(element_id).__name__}. Must be integer."
                    print(f"   ❌ {error_msg}")
                    self.logger.log_error("InvalidElementIDType", error_msg)
                    return error_msg
                
                button = args.get("button", "left")
                clicks = args.get("clicks", 1)
                
                # Validate we have elements to search
                if not self.current_elements:
                    error_msg = "No UI elements were detected in the current scan. Cannot use click_element_by_id."
                    print(f"   ❌ {error_msg}")
                    print(f"   💡 Hint: Switch to Grid mode or rescan the window.")
                    self.logger.log_error("NoElementsDetected", error_msg)
                    return error_msg
                
                # Look up element by ID
                element = None
                for elem in self.current_elements:
                    if elem['id'] == element_id:
                        element = elem
                        break
                
                if not element:
                    error_msg = f"Element ID {element_id} not found in current scan"
                    print(f"   ❌ {error_msg}")
                    print(f"   📋 Available elements: {[e['id'] for e in self.current_elements[:10]]}")
                    self.logger.log_error(
                        "ElementNotFound",
                        f"{error_msg}. Available IDs: {[e['id'] for e in self.current_elements]}"
                    )
                    return error_msg
                
                # Get center coordinates
                x, y = element['center']
                elem_name = element['name'] or '(no name)'
                elem_type = element['type']
                
                print(f"   🎯 Target: Element #{element_id} - {elem_type} '{elem_name}' at ({x}, {y})")
                
                # Click using the coordinates (scale=False because these are already screen coords)
                self.controller.click_element(x, y, button=button, clicks=clicks, scale=False)
                click_type = "double-clicked" if clicks == 2 else f"{button}-clicked"
                return f"{click_type.capitalize()} element #{element_id} ('{elem_name}') at ({x}, {y})"
            
            elif name == "web_click":
                selector = args["selector"]
                timeout = args.get("timeout", 5000)
                try:
                    self.controller.web_click(selector, timeout=timeout)
                    return f"Web clicked element: {selector}"
                except Exception as e:
                    error_msg = f"Web click failed: {e}"
                    print(f"   ❌ {error_msg}")
                    return error_msg
            
            elif name == "web_type":
                selector = args["selector"]
                text = args["text"]
                press_enter = args.get("press_enter", False)
                timeout = args.get("timeout", 5000)
                try:
                    self.controller.web_type(selector, text, timeout=timeout, press_enter=press_enter)
                    enter_msg = " and pressed Enter" if press_enter else ""
                    return f"Web typed '{text}' into {selector}{enter_msg}"
                except Exception as e:
                    error_msg = f"Web type failed: {e}"
                    print(f"   ❌ {error_msg}")
                    return error_msg
            
            elif name == "web_get_elements":
                max_elements = args.get("max_elements", 50)
                try:
                    elements = self.controller.web_get_elements(max_elements=max_elements)
                    # Format for logging
                    element_list = [f"{e['type']}: {e['text'][:50]} (selector: {e['selector']})" for e in elements[:10]]
                    return f"Found {len(elements)} web elements. First 10: {', '.join(element_list)}"
                except Exception as e:
                    error_msg = f"Web get elements failed: {e}"
                    print(f"   ❌ {error_msg}")
                    return error_msg
            
            else:
                return f"Unknown function: {name}"
        
        except DesktopControllerError as e:
            error_msg = f"Failed to execute {name}: {e}"
            print(f"   ❌ {error_msg}")
            return error_msg
    
    def run_task(self, user_task: str) -> bool:
        """
        Execute a user task through autonomous operation.
        
        Args:
            user_task: User's high-level goal/instruction.
        
        Returns:
            True if task completed successfully, False otherwise.
        """
        print("\n" + "=" * 60)
        print(f"🎯 Task: {user_task}")
        print("=" * 60)
        print()
        
        # Step 0: Generate a plan for complex tasks (optional)
        # Check if task seems complex (multiple steps implied)
        complex_indicators = ["and", "then", "after", "first", "next", "finally", ","]
        is_complex_task = any(indicator in user_task.lower() for indicator in complex_indicators) or len(user_task.split()) > 8
        
        if is_complex_task:
            print("🧩 Task appears complex - generating hierarchical plan...")
            try:
                self.plan = self.agent.generate_plan(user_task)
                self.current_subgoal_index = 0
                self.subgoal_attempts = 0
                
                if self.plan and len(self.plan) > 1:
                    print(f"\n📋 Generated Plan ({len(self.plan)} steps):")
                    for i, subgoal in enumerate(self.plan, 1):
                        status_icon = "▶️" if i == 1 else "⏸️"
                        print(f"   {status_icon} {i}. {subgoal}")
                    print()
                    
                    self.logger.log_plan(self.plan, "INITIAL")
                else:
                    # Planning failed or returned single step
                    self.plan = None
                    print("   ℹ️  Plan generation returned single step - proceeding without hierarchical planning\n")
            except Exception as e:
                print(f"   ⚠️  Plan generation failed: {e}")
                print("   Proceeding without hierarchical planning\n")
                self.plan = None
        else:
            print("ℹ️  Task appears simple - proceeding without hierarchical planning\n")
            self.plan = None
        
        iteration = 0
        task_complete = False
        
        while iteration < MAX_ITERATIONS and not task_complete:
            iteration += 1
            print(f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")
            
            # LOG: Start of iteration
            self.logger.log_iteration(iteration, MAX_ITERATIONS)
            
            try:
                # Step A: Hybrid capture (UI Automation or Grid)
                screenshot_path, detected_elements = self.capture_screen()
                
                # Store current elements for ID-to-coordinate mapping
                self.current_elements = detected_elements
                
                # Small delay for stability
                time.sleep(1.0)
                
                # Step B: Send to Gemini for analysis
                print("🧠 Analyzing with Gemini...")
                
                # Determine mode for logging
                mode = "Set-of-Marks" if detected_elements else "Grid"
                print(f"   Mode: {mode}")
                
                # Check if state has changed from previous iteration
                state_changed = self._compare_screenshots(screenshot_path, self.previous_screenshot_path)
                
                # Generate correction hint if stuck
                correction_hint = ""
                if not state_changed and iteration > 1:
                    self.stuck_count += 1
                    print(f"   ⚠️  Stuck state detected ({self.stuck_count} consecutive iterations)")
                    
                    if self.stuck_count >= 2:
                        correction_hint = "\n\n🔄 CORRECTION REQUIRED:\n"
                        correction_hint += "The UI state has NOT changed after your last action(s). Your previous approach failed.\n"
                        correction_hint += "You MUST try a completely different strategy:\n"
                        correction_hint += "- If you used click_element_by_id, try coordinate clicking instead\n"
                        correction_hint += "- If you clicked, try keyboard shortcuts (/, Ctrl+F, etc.)\n"
                        correction_hint += "- If you typed, explicitly click the target field first\n"
                        correction_hint += "- Consider scrolling or pressing Escape to reset the state\n"
                        correction_hint += "Analyze what went wrong and choose a DIFFERENT approach.\n"
                        
                        self.logger.log_step(
                            "Self-Correction Triggered",
                            f"Stuck for {self.stuck_count} iterations. Injecting correction hint."
                        )
                else:
                    self.stuck_count = 0  # Reset counter if state changed
                
                # Build plan context if we have an active plan
                plan_context = ""
                if self.plan and self.current_subgoal_index < len(self.plan):
                    plan_context = "\n\n" + "=" * 40 + "\n"
                    plan_context += "📋 HIERARCHICAL PLAN:\n"
                    for i, subgoal in enumerate(self.plan):
                        if i < self.current_subgoal_index:
                            plan_context += f"   ✅ {i+1}. {subgoal} (COMPLETED)\n"
                        elif i == self.current_subgoal_index:
                            plan_context += f"   ▶️ {i+1}. {subgoal} (CURRENT - Attempt {self.subgoal_attempts + 1}/{self.max_subgoal_attempts})\n"
                        else:
                            plan_context += f"   ⏸️ {i+1}. {subgoal} (PENDING)\n"
                    plan_context += "=" * 40 + "\n"
                    plan_context += f"\n🎯 CURRENT SUB-GOAL: {self.plan[self.current_subgoal_index]}\n"
                    plan_context += "Focus ONLY on this sub-goal. When complete, state 'SUB-GOAL COMPLETE'.\n"
                    plan_context += "If impossible, state 'SUB-GOAL IMPOSSIBLE: [reason]'.\n"
                
                # Update previous screenshot
                self.previous_screenshot_path = screenshot_path
                
                result = self.agent.analyze_and_act(
                    user_request=user_task + plan_context + correction_hint,
                    screenshot_path=screenshot_path,
                    chat_history=self.history,
                    detected_elements=detected_elements if detected_elements else None
                )
                
                # Step C: Parse response
                text_response = result.get("text_response", "")
                function_calls = result.get("function_calls", [])
                
                # Log agent's thought process (ReAct pattern)
                if text_response:
                    print(f"💭 AI Thought: {text_response}")
                    self.logger.log_thought(text_response)
                    
                    # Check for sub-goal completion signals
                    if self.plan and self.current_subgoal_index < len(self.plan):
                        response_lower = text_response.lower()
                        
                        # Sub-goal completed
                        if "sub-goal complete" in response_lower or "subgoal complete" in response_lower:
                            print(f"\n   ✅ Sub-goal completed: {self.plan[self.current_subgoal_index]}")
                            self.logger.log_subgoal_progress(
                                self.current_subgoal_index,
                                len(self.plan),
                                self.plan[self.current_subgoal_index],
                                "COMPLETED"
                            )
                            
                            # Move to next sub-goal
                            self.current_subgoal_index += 1
                            self.subgoal_attempts = 0
                            self.stuck_count = 0  # Reset stuck counter
                            
                            # Check if all sub-goals are complete
                            if self.current_subgoal_index >= len(self.plan):
                                print("\n🎉 All sub-goals completed!")
                                task_complete = True
                            else:
                                print(f"\n▶️  Moving to next sub-goal: {self.plan[self.current_subgoal_index]}")
                        
                        # Sub-goal impossible - trigger re-planning
                        elif "sub-goal impossible" in response_lower or "subgoal impossible" in response_lower:
                            print(f"\n   ⚠️  Sub-goal deemed impossible: {self.plan[self.current_subgoal_index]}")
                            print("   🔄 Triggering re-planning...")
                            
                            self.logger.log_subgoal_progress(
                                self.current_subgoal_index,
                                len(self.plan),
                                self.plan[self.current_subgoal_index],
                                "IMPOSSIBLE"
                            )
                            
                            # Re-generate plan from current state
                            try:
                                # Create updated task description
                                completed_goals = self.plan[:self.current_subgoal_index]
                                remaining_task = f"Continue from: {', '.join(completed_goals)}. Original task: {user_task}"
                                
                                new_plan = self.agent.generate_plan(remaining_task, screenshot_path)
                                
                                if new_plan:
                                    print(f"\n📋 Updated Plan ({len(new_plan)} steps):")
                                    for i, subgoal in enumerate(new_plan, 1):
                                        print(f"   {i}. {subgoal}")
                                    
                                    # Update plan state
                                    self.plan = new_plan
                                    self.current_subgoal_index = 0
                                    self.subgoal_attempts = 0
                                    self.stuck_count = 0
                                    
                                    self.logger.log_plan(new_plan, "RE-PLANNED")
                                else:
                                    print("   ❌ Re-planning failed - continuing with original plan")
                            except Exception as e:
                                print(f"   ❌ Re-planning error: {e}")
                        
                        # Track sub-goal attempts
                        else:
                            self.subgoal_attempts += 1
                            if self.subgoal_attempts >= self.max_subgoal_attempts:
                                print(f"\n   ⚠️  Max attempts ({self.max_subgoal_attempts}) reached for current sub-goal")
                                print("   🔄 Triggering re-planning...")
                                
                                # Force re-planning
                                try:
                                    completed_goals = self.plan[:self.current_subgoal_index]
                                    remaining_task = f"Continue from: {', '.join(completed_goals)}. Original task: {user_task}"
                                    new_plan = self.agent.generate_plan(remaining_task, screenshot_path)
                                    
                                    if new_plan:
                                        self.plan = new_plan
                                        self.current_subgoal_index = 0
                                        self.subgoal_attempts = 0
                                        print(f"   ✅ Re-planned with {len(new_plan)} steps")
                                except Exception:
                                    # Skip to next sub-goal if re-planning fails
                                    self.current_subgoal_index += 1
                                    self.subgoal_attempts = 0
                                    print(f"   ⏭️  Skipping to next sub-goal")
                
                # Step D: Execute function calls and track results
                if function_calls:
                    # LOG: Function calls to execute
                    self.logger.log_function_calls(function_calls)
                    
                    # Create action signature to detect repetition
                    action_signature = json.dumps(function_calls, sort_keys=True)
                    if action_signature == self.last_action_signature and iteration > 1:
                        print("   ⚠️  Repeated action detected - same function calls as previous iteration")
                        self.stuck_count += 1
                    else:
                        self.last_action_signature = action_signature
                    
                    execution_results = []
                    
                    for func_call in function_calls:
                        result_msg = self.execute_function_call(func_call)
                        execution_results.append(result_msg)
                        print(f"   ✅ {result_msg}")
                        
                        # LOG: Execution result
                        self.logger.log_execution_result(result_msg)
                        
                        # Small delay between actions
                        time.sleep(2)
                    
                    # Add to conversation history
                    self.history.append({
                        "iteration": iteration,
                        "screenshot": screenshot_path,
                        "ai_response": text_response,
                        "function_calls": function_calls,
                        "execution_results": execution_results
                    })
                else:
                    print("   ℹ️  No actions to execute")
                    
                    # Check if AI indicates completion
                    completion_phrases = [
                        "task complete", "finished", "done",
                        "successfully completed", "accomplished"
                    ]
                    if any(phrase in text_response.lower() for phrase in completion_phrases):
                        print("\n✅ AI indicates task is complete!")
                        task_complete = True
                        break
                    
                    # If no function calls and no completion signal, might be stuck
                    if iteration > 3:
                        print("   ⚠️  No actions for multiple iterations")
                        user_continue = input("   Continue? (y/n): ").strip().lower()
                        if user_continue != 'y':
                            break
                
            except ScreenCaptureError as e:
                print(f"\n❌ Screen capture error: {e}")
                self.logger.log_error("ScreenCaptureError", str(e))
                return False
            
            except GeminiAgentError as e:
                print(f"\n❌ Gemini API error: {e}")
                self.logger.log_error("GeminiAgentError", str(e))
                print("   Possible causes:")
                print("   - Invalid API key")
                print("   - Rate limit exceeded")
                print("   - Network connection issue")
                return False
            
            except KeyboardInterrupt:
                print("\n\n⚠️  Task interrupted by user")
                return False
            
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Check completion status
        if task_complete:
            print("\n" + "=" * 60)
            print("🎉 Task completed successfully!")
            print("=" * 60)
            self.logger.log_task_completion(True, iteration)
            return True
        elif iteration >= MAX_ITERATIONS:
            print("\n" + "=" * 60)
            print(f"⚠️  Reached maximum iterations ({MAX_ITERATIONS})")
            print("   Task may not be fully complete")
            print("=" * 60)
            self.logger.log_task_completion(False, iteration)
            return False
        else:
            self.logger.log_task_completion(False, iteration)
            return False
    
    def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        
        # Close Playwright connection
        if hasattr(self, 'controller'):
            try:
                self.controller.close_playwright()
                print("   Closed Playwright connection")
            except Exception:
                pass
        
        # Close screen capture
        if hasattr(self, 'screen_capture'):
            self.screen_capture.close()
        
        # Remove temporary screenshot
        if os.path.exists(SCREENSHOT_PATH):
            try:
                os.remove(SCREENSHOT_PATH)
                print(f"   Removed: {SCREENSHOT_PATH}")
            except Exception:
                pass
        
        print("✅ Cleanup complete")


def main():
    """Main entry point for the Autonomous AI Agent."""
    try:
        # Initialize agent
        agent = AutonomousAgent()
        
        print("\n" + "=" * 60)
        print("🚀 Autonomous AI Agent - Ready!")
        print("=" * 60)
        print("\nExamples of tasks you can request:")
        print("  • Open Chrome and search for Python tutorials")
        print("  • Open Notepad and type Hello World")
        print("  • Open File Explorer and navigate to Documents")
        print("  • Open Calculator and calculate 15 * 23")
        print("\n⚠️  SAFETY: Move your mouse to any corner to abort!")
        print("=" * 60)
        
        # Main interaction loop
        while True:
            print("\n")
            user_task = input("🎯 Enter your task (or 'quit' to exit): ").strip()
            
            if not user_task:
                print("   Please enter a valid task")
                continue
            
            if user_task.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Run the task
            success = agent.run_task(user_task)
            
            if not success:
                retry = input("\n🔄 Would you like to try another task? (y/n): ").strip().lower()
                if retry != 'y':
                    break
        
        # Cleanup
        agent.cleanup()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Application interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
