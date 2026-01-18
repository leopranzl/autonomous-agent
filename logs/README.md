# Execution Logs

This directory contains detailed execution logs from the Autonomous AI Agent.

## Log Files

Each session creates a unique log file:
- Format: `execution_YYYY-MM-DD_HH-MM-SS.log`
- Encoding: UTF-8 (supports Portuguese and special characters)

## What's Logged

### 1. **System Initialization**
- Component initialization
- Screen resolution
- Model selection

### 2. **UI Element Detection** (Critical)
- Every element found by UIScanner
- Element IDs, types, names, and coordinates
- Mode selection (Set-of-Marks vs Grid)

### 3. **Prompts Sent to AI** (Critical for Reproduction)
- Complete prompt with context
- History of previous actions
- Detected elements list
- User request

### 4. **AI Responses**
- Raw response from Gemini
- Text explanations
- Function calls requested
- Finish reasons

### 5. **Function Execution**
- Each function call with arguments
- Execution results
- Error messages if any

### 6. **Task Completion**
- Success/failure status
- Total iterations
- Final state

## Debugging Workflow

1. **Reproduce AI Decisions:**
   - Copy prompt from log file
   - Paste into [Google AI Studio](https://aistudio.google.com/)
   - Compare results

2. **Trace Element Detection:**
   - Check "UI ELEMENTS DETECTED" sections
   - Verify element IDs match screenshot tags

3. **Analyze Failures:**
   - Look for ERROR sections
   - Check execution results for failures
   - Review AI's reasoning in responses

## Privacy

- ✅ Logs DO include: Prompts, responses, UI element names
- ❌ Logs DO NOT include: API keys, passwords, sensitive data
- ⚠️ Be careful when sharing logs publicly

## Clean Up

To clean old logs:
```powershell
# Keep only last 10 logs
Get-ChildItem -Path "logs" -Filter "execution_*.log" | 
  Sort-Object LastWriteTime -Descending | 
  Select-Object -Skip 10 | 
  Remove-Item
```
