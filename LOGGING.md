# 🔍 Comprehensive Logging System

## Overview

A complete observability and debugging system that traces every step of the Autonomous AI Agent's execution.

## 📁 Structure

```
src/
└── utils/
    ├── __init__.py
    └── logger.py          # TaskLogger class

logs/
├── README.md              # Logging documentation
└── execution_*.log        # Generated log files (timestamped)
```

## 🎯 What Gets Logged

### 1. **System Initialization**
```
[10:30:15.123] System Initialization
Starting Autonomous AI Agent
...
```

### 2. **UI Element Detection** (Critical)
```
[10:30:16.456] UI ELEMENTS DETECTED - Set-of-Marks Mode
================================================================================
[
  {
    "id": 1,
    "type": "ButtonControl",
    "name": "Save",
    "center": [140, 215],
    "rect": [100, 200, 80, 30]
  },
  ...
]
```

### 3. **Prompts Sent to Gemini** (Critical for Reproduction)
```
[10:30:17.789] PROMPT SENT TO GEMINI (FULL_CONTEXT)
================================================================================
DETECTED UI ELEMENTS (Set-of-Marks):
Use `click_element_by_id(id)` for these elements.
[1] ButtonControl 'Save'
[2] EditControl 'Email address'
...

HISTORY OF PREVIOUS ACTIONS:
- Action: press_key args={'key': 'win'}
  Result: Pressed 'win' key 1 time(s)
...

USER REQUEST: Open Notepad and type Hello World
================================================================================
```

### 4. **AI Responses**
```
[10:30:20.123] AI RESPONSE (RAW)
================================================================================
{
  "text_response": "I see element #3 is the 'Save' button. I'll click it.",
  "function_calls": [
    {
      "name": "click_element_by_id",
      "args": {
        "element_id": 3
      }
    }
  ],
  "finish_reason": "STOP"
}
```

### 5. **Function Execution**
```
[10:30:20.456] EXECUTION RESULT: Left-clicked element #3 ('Save') at (520, 340)
```

### 6. **Errors**
```
[10:30:21.789] ❌ ERROR - DesktopControllerError
Element ID 99 not found in current scan
```

### 7. **Task Completion**
```
[10:30:25.000] TASK COMPLETION: SUCCESS
Total iterations: 3
```

## 💡 Usage

### Automatic Logging
Logging is automatic - just run the agent:

```powershell
python main.py
```

The log file location is displayed at startup:
```
   📝 Log file: D:\IA AUTONOMA\logs\execution_2026-01-18_15-30-45.log
```

### Log File Features

- **UTF-8 Encoding**: Supports Portuguese and special characters
- **Timestamps**: Microsecond precision for every event
- **Structured Format**: Easy to parse and search
- **No API Keys**: Sensitive data is never logged

## 🐛 Debugging Workflow

### Problem: AI makes wrong decisions

**Solution:**
1. Open the log file
2. Find the `PROMPT SENT TO GEMINI (FULL_CONTEXT)` section
3. Copy the entire prompt
4. Paste into [Google AI Studio](https://aistudio.google.com/)
5. Compare results
6. Adjust system instruction or prompt if needed

### Problem: AI can't find an element

**Solution:**
1. Find the `UI ELEMENTS DETECTED` section
2. Check if the element is in the list
3. Verify the element ID matches the screenshot
4. If missing, check UI Scanner configuration

### Problem: Function execution fails

**Solution:**
1. Look for `EXECUTION RESULT` lines
2. Check for error messages
3. Verify coordinates are within screen bounds
4. Check if element still exists

## 🔧 TaskLogger API

### Core Methods

```python
from src.utils.logger import TaskLogger

# Initialize
logger = TaskLogger()  # Creates logs/execution_YYYY-MM-DD_HH-MM-SS.log

# Log a step
logger.log_step("Step Name", "Optional details")

# Log structured data
logger.log_data("Title", data_dict, format_json=True)

# Log iterations
logger.log_iteration(1, 15)

# Log UI elements
logger.log_ui_elements(elements, "Set-of-Marks")

# Log prompts (CRITICAL)
logger.log_prompt(prompt_text, "FULL_CONTEXT")

# Log AI responses
logger.log_ai_response(response_dict)

# Log function calls
logger.log_function_calls(function_calls_list)

# Log execution results
logger.log_execution_result("Clicked at (100, 200)")

# Log errors
logger.log_error("ErrorType", "Error message")

# Log task completion
logger.log_task_completion(success=True, iterations=5)

# Get log file path
path = logger.get_log_path()
```

## 📊 Log Analysis Tips

### Search for Specific Events

```powershell
# Find all function calls
Select-String -Path "logs\execution_*.log" -Pattern "FUNCTION CALLS"

# Find errors
Select-String -Path "logs\execution_*.log" -Pattern "ERROR"

# Find a specific element
Select-String -Path "logs\execution_*.log" -Pattern "element #5"
```

### Count Actions

```powershell
# Count iterations
(Select-String -Path "logs\execution_2026-01-18_15-30-45.log" -Pattern "ITERATION").Count

# Count function calls
(Select-String -Path "logs\execution_2026-01-18_15-30-45.log" -Pattern "EXECUTION RESULT").Count
```

## 🗂️ Log Maintenance

### Keep Logs Clean

```powershell
# Delete logs older than 7 days
Get-ChildItem -Path "logs" -Filter "execution_*.log" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
  Remove-Item

# Keep only last 10 logs
Get-ChildItem -Path "logs" -Filter "execution_*.log" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -Skip 10 |
  Remove-Item
```

## 🎯 Key Benefits

1. **Full Reproducibility**: Copy-paste prompts to AI Studio
2. **Element Traceability**: See exactly what the scanner found
3. **Execution Transparency**: Track every action and result
4. **Error Diagnosis**: Pinpoint failures with detailed context
5. **Performance Analysis**: Review iteration counts and timing
6. **Clean Console**: Verbose logging without cluttering terminal

## ⚠️ Privacy & Security

✅ **Safe to Log:**
- UI element names and types
- Coordinates and screen resolution
- Function calls and results
- AI responses and reasoning

❌ **Never Logged:**
- API keys
- Passwords or credentials
- Personal/sensitive data from screenshots
- File contents

## 🚀 Advanced Usage

### Custom Log Directory

```python
logger = TaskLogger(log_dir="custom_logs")
```

### Integration with External Tools

The logs are in plain text format, making them easy to:
- Parse with Python scripts
- Import into monitoring tools
- Analyze with log aggregation platforms
- Search with grep/PowerShell

## 📈 Performance Impact

- **Minimal**: File I/O is asynchronous
- **No blocking**: Doesn't slow down agent execution
- **Efficient**: Logs are written incrementally
- **Small files**: Typical log size: 50-200 KB per session

---

**Result**: Complete visibility into agent execution with zero configuration! 🎉
