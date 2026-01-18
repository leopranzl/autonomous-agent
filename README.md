# Autonomous AI Agent using Google Gemini

An AI-powered agent that uses Google Gemini 2.0 to autonomously interact with your computer through screen capture and automated controls.

## Project Structure

```
IA AUTONOMA/
├── src/
│   ├── vision/          # Screen capture and processing
│   ├── action/          # Mouse and keyboard control
│   └── agent/           # Gemini API interaction
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template
```

## Setup Instructions

### 1. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you encounter execution policy errors, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure API Key

```powershell
# Copy the example environment file
copy .env.example .env

# Edit .env and add your Google Gemini API key
```

### 4. Run the Application

```powershell
python main.py
```

## Dependencies

- **google-genai**: Google Gemini 2.0 API client
- **pyautogui**: Mouse and keyboard automation
- **mss**: Ultra-fast screen capture
- **pillow**: Image processing
- **python-dotenv**: Environment variable management

## Development Status

🚧 Project structure initialized - Implementation pending

