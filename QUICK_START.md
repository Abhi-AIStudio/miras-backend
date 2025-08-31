# Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Python 3.8+
- Gemini API Key (get from [Google AI Studio](https://aistudio.google.com/app/apikey))
- Contextual AI API Key & Agent ID (from your Contextual account)

### 1. Clone & Setup (1 minute)
```bash
git clone <repository-url>
cd miras-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys (1 minute)
```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_key_here
CONTEXTUAL_API_KEY=your_key_here
CONTEXTUAL_AGENT_ID=your_agent_id_here
```

### 3. Run Demo (3 minutes)

#### Option A: Quick Test
```bash
# Start the streaming CLI
python stream_cli.py

# Try these queries:
# - "What is the company's AUM?"
# - "Who are the founders?"
# - "What is their investment strategy?"
```

#### Option B: Full Demo Flow
```bash
# Step 1: Ingest a PDF
python ingest_document.py your_document.pdf

# Step 2: Query with validation
python stream_cli.py
```

## Features to Show

1. **Real-time Streaming** - Watch responses stream in character by character
2. **Gemini Thinking** - See AI's reasoning process during validation
3. **Fact Checking** - Each fact marked with ✅ or ❌
4. **Citations** - Automatic page references for sources

## CLI Commands

- Type any question and press Enter
- `validate off` - Disable fact-checking for faster responses
- `validate on` - Re-enable fact-checking
- `reset` - Start new conversation
- `exit` - Quit

## Troubleshooting

- **No Contextual Agent**: Make sure your agent is created and active in Contextual
- **Gemini API errors**: Check your API key has access to Gemini 2.5 Flash
- **No validation results**: Ensure you have ingested at least one document

## Demo Tips

- Start with simple factual questions
- Show the thinking process by letting validation run
- Demonstrate accuracy by asking for specific numbers or dates
- Toggle validation on/off to show speed difference