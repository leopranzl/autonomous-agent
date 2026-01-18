"""
Task Logger Module
Comprehensive logging system for debugging autonomous agent execution.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class TaskLogger:
    """
    Comprehensive logger for tracing agent execution.
    
    Creates detailed log files with all execution steps, prompts sent to AI,
    detected UI elements, and function calls.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the task logger.
        
        Args:
            log_dir: Directory to store log files. Default is "logs".
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Generate unique log filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"execution_{timestamp}.log"
        
        # Initialize log file
        self._write_header()
    
    def _write_header(self):
        """Write log file header."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("AUTONOMOUS AI AGENT - EXECUTION LOG\n")
            f.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
    
    def log_step(self, step_name: str, details: str = ""):
        """
        Log a named execution step.
        
        Args:
            step_name: Name/title of the step.
            details: Optional details about the step.
        
        Example:
            >>> logger.log_step("Initialization", "Starting agent components")
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] {step_name}\n")
            if details:
                f.write(f"{details}\n")
            f.write("-" * 80 + "\n")
    
    def log_data(self, title: str, data: Any, format_json: bool = False):
        """
        Log large data blocks with clear formatting.
        
        Args:
            title: Title/description of the data.
            data: Data to log (string, dict, list, etc.).
            format_json: Whether to format as JSON. Default is False.
        
        Example:
            >>> logger.log_data("Detected Elements", elements, format_json=True)
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] {title}\n")
            f.write("=" * 80 + "\n")
            
            if format_json and isinstance(data, (dict, list)):
                try:
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    f.write(formatted + "\n")
                except Exception:
                    f.write(str(data) + "\n")
            else:
                f.write(str(data) + "\n")
            
            f.write("=" * 80 + "\n")
    
    def log_iteration(self, iteration: int, max_iterations: int):
        """
        Log the start of a new iteration.
        
        Args:
            iteration: Current iteration number.
            max_iterations: Maximum number of iterations.
        """
        self.log_step(
            f"ITERATION {iteration}/{max_iterations}",
            f"Starting iteration {iteration}"
        )
    
    def log_ui_elements(self, elements: List[Dict[str, Any]], mode: str):
        """
        Log detected UI elements.
        
        Args:
            elements: List of detected UI elements.
            mode: Detection mode ("Set-of-Marks" or "Grid").
        """
        if elements:
            element_list = []
            for elem in elements:
                element_list.append({
                    "id": elem.get("id"),
                    "type": elem.get("type"),
                    "name": elem.get("name"),
                    "center": elem.get("center"),
                    "rect": elem.get("rect")
                })
            
            self.log_data(
                f"UI ELEMENTS DETECTED - {mode} Mode",
                element_list,
                format_json=True
            )
        else:
            self.log_step(
                f"UI ELEMENTS DETECTED - {mode} Mode",
                "No UI elements detected - Fallback to Grid mode"
            )
    
    def log_prompt(self, prompt: str, context_type: str = "FULL"):
        """
        Log the complete prompt sent to AI.
        
        This is CRITICAL for debugging - allows reproduction in AI Studio.
        
        Args:
            prompt: The complete prompt text.
            context_type: Type of context (e.g., "FULL", "USER_ONLY").
        """
        self.log_data(
            f"PROMPT SENT TO GEMINI ({context_type})",
            prompt
        )
    
    def log_ai_response(self, response: Dict[str, Any]):
        """
        Log the raw AI response.
        
        Args:
            response: Response dictionary from agent.
        """
        self.log_data(
            "AI RESPONSE (RAW)",
            response,
            format_json=True
        )
    
    def log_thought(self, thought: str):
        """
        Log the agent's reasoning/thought process (ReAct pattern).
        
        Args:
            thought: The agent's reasoning before taking action.
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] 💭 AGENT THOUGHT (ReAct)\n")
            f.write(f"{thought}\n")
            f.write("-" * 80 + "\n")
    
    def log_plan(self, plan: List[str], plan_type: str = "INITIAL"):
        """
        Log a hierarchical plan.
        
        Args:
            plan: List of sub-goal strings.
            plan_type: Type of plan (e.g., "INITIAL", "UPDATED", "RE-PLANNED").
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] 📋 {plan_type} PLAN\n")
            for i, subgoal in enumerate(plan, 1):
                f.write(f"   {i}. {subgoal}\n")
            f.write("-" * 80 + "\n")
    
    def log_subgoal_progress(self, current_index: int, total: int, subgoal: str, status: str):
        """
        Log sub-goal progress.
        
        Args:
            current_index: Current sub-goal index (0-based).
            total: Total number of sub-goals.
            subgoal: Current sub-goal description.
            status: Status (e.g., "IN_PROGRESS", "COMPLETED", "IMPOSSIBLE").
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] 🎯 SUB-GOAL {status} [{current_index + 1}/{total}]\n")
            f.write(f"   {subgoal}\n")
            f.write("-" * 80 + "\n")
    
    def log_function_calls(self, function_calls: List[Dict[str, Any]]):
        """
        Log function calls to be executed.
        
        Args:
            function_calls: List of function call dictionaries.
        """
        self.log_data(
            "FUNCTION CALLS TO EXECUTE",
            function_calls,
            format_json=True
        )
    
    def log_execution_result(self, result: str):
        """
        Log the result of a function execution.
        
        Args:
            result: Execution result message.
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] EXECUTION RESULT: {result}\n")
    
    def log_error(self, error_type: str, error_message: str):
        """
        Log an error.
        
        Args:
            error_type: Type/category of error.
            error_message: Error message.
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] ❌ ERROR - {error_type}\n")
            f.write(f"{error_message}\n")
            f.write("-" * 80 + "\n")
    
    def log_task_completion(self, success: bool, iterations: int):
        """
        Log task completion status.
        
        Args:
            success: Whether task completed successfully.
            iterations: Number of iterations executed.
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        status = "SUCCESS" if success else "INCOMPLETE"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] TASK COMPLETION: {status}\n")
            f.write(f"Total iterations: {iterations}\n")
            f.write("=" * 80 + "\n")
    
    def get_log_path(self) -> str:
        """
        Get the path to the current log file.
        
        Returns:
            Absolute path to log file.
        """
        return str(self.log_file.absolute())
