"""
Autonomous AI Agent using Google Gemini
Entry point for the application - orchestrates vision, action, and AI components
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from src.vision.capture import ScreenCapture, ScreenCaptureError
from src.action.controller import DesktopController, DesktopControllerError
from src.agent.brain import GeminiAgent, GeminiAgentError


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
            grid_spacing=100,
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
            self.agent = GeminiAgent(model_name="gemini-2.0-flash-exp")
            print(f"   Model: gemini-2.0-flash-exp")
        except GeminiAgentError:
            print("   Fallback to: gemini-1.5-pro")
            self.agent = GeminiAgent(model_name="gemini-1.5-pro")
        
        # Conversation history
        self.history: List[Dict[str, Any]] = []
        
        print("=" * 60)
        print("✅ Initialization complete!\n")
    
    def capture_screen_with_grid(self) -> str:
        """
        Capture screen with coordinate grid overlay.
        
        Returns:
            Path to saved screenshot.
        """
        try:
            print("📸 Capturing screen with grid overlay...")
            image = self.screen_capture.capture_with_grid()
            image.save(SCREENSHOT_PATH)
            print(f"   Saved to: {SCREENSHOT_PATH}")
            return SCREENSHOT_PATH
        except ScreenCaptureError as e:
            print(f"❌ Screen capture failed: {e}")
            raise
    
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
        
        iteration = 0
        task_complete = False
        
        while iteration < MAX_ITERATIONS and not task_complete:
            iteration += 1
            print(f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")
            
            try:
                # Step A: Capture screen with grid overlay
                screenshot_path = self.capture_screen_with_grid()
                
                # Small delay for stability
                time.sleep(0.5)
                
                # Step B: Send to Gemini for analysis
                print("🧠 Analyzing with Gemini...")
                result = self.agent.analyze_and_act(
                    user_request=user_task,
                    screenshot_path=screenshot_path,
                    chat_history=self.history
                )
                
                # Step C: Parse response
                text_response = result.get("text_response", "")
                function_calls = result.get("function_calls", [])
                
                # Display AI's thought process
                if text_response:
                    print(f"💭 AI: {text_response}")
                
                # Step D: Execute function calls and track results
                if function_calls:
                    execution_results = []
                    
                    for func_call in function_calls:
                        result_msg = self.execute_function_call(func_call)
                        execution_results.append(result_msg)
                        print(f"   ✅ {result_msg}")
                        
                        # Small delay between actions
                        time.sleep(0.3)
                    
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
                return False
            
            except GeminiAgentError as e:
                print(f"\n❌ Gemini API error: {e}")
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
            return True
        elif iteration >= MAX_ITERATIONS:
            print("\n" + "=" * 60)
            print(f"⚠️  Reached maximum iterations ({MAX_ITERATIONS})")
            print("   Task may not be fully complete")
            print("=" * 60)
            return False
        else:
            return False
    
    def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        
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
