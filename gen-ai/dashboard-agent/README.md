# Dashboard Agent

A comprehensive dashboard agent that processes Google Drive spreadsheet data, generates reports, and continuously improves prompts based on Slack feedback.

## Installation

### 1. Install uv (if not present)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```

### 2. Create and activate virtual environment

```bash
cd
uv venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
uv pip install -e .
```

## Running the Application

Launch the Streamlit app:

```bash
uv run streamlit run src/dashboard_agent/app.py
```

The app will be available at `http://localhost:8501`

## Features

- Read data from Google Drive spreadsheets
- Process data through extraction → analysis → report pipeline
- Collect feedback from Slack channels
- Automatically improve prompts based on feedback using semantic versioning
