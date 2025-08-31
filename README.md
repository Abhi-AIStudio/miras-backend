# Miras Backend - Document Intelligence System

A Python-based document intelligence system that processes PDFs, stores them in Contextual AI, and provides intelligent query responses with fact-checking validation using Google Gemini.

## Features

- **PDF Processing**: Extract structured content from PDFs using Gemini 2.5 Flash with thinking mode
- **Document Storage**: Store processed documents in Contextual AI for retrieval
- **Streaming Queries**: Real-time streaming responses from Contextual AI
- **Fact-Checking Validation**: Validate responses using Gemini with visible thinking process
- **Citation Support**: Automatic source citations with page references

## Architecture

```
PDF Document → Gemini Extraction (XML) → Contextual AI Storage
                                              ↓
User Query → Contextual AI → Streaming Response → Gemini Validation
                                                      ↓
                                              Fact-Checked Results
```

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd miras-backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```
GEMINI_API_KEY=your_gemini_api_key
CONTEXTUAL_API_KEY=your_contextual_api_key
CONTEXTUAL_AGENT_ID=your_agent_id
```

## Usage

### 1. Ingest a PDF Document

Process and store a PDF in Contextual AI:

```bash
python ingest_document.py path/to/document.pdf
```

This will:
- Extract content using Gemini with visible thinking process
- Save extracted XML to `extracted_texts/`
- Upload to Contextual AI

### 2. Query Documents

**Simple CLI (without validation):**
```bash
python simple_cli.py
```

**Streaming CLI with validation:**
```bash
python stream_cli.py
```

Commands in CLI:
- Type your query and press Enter
- `exit` - quit the application
- `reset` - start a new conversation
- `validate off` - disable fact-checking
- `validate on` - enable fact-checking

## Project Structure

```
miras-backend/
├── config/                 # Configuration and settings
│   ├── settings.py        # API keys and endpoints
│   ├── prompts.py         # System prompts
│   └── constants.py       # Constants
├── ingestion/             # PDF processing module
│   ├── processor.py       # Gemini PDF extraction
│   └── uploader.py        # Contextual AI upload
├── extracted_texts/       # Stored XML documents
├── stream_cli.py          # Main streaming CLI with validation
├── simple_cli.py          # Simple CLI without validation
├── validation.py          # Gemini fact-checking module
└── ingest_document.py     # PDF ingestion script
```

## Key Components

### PDF Processing
- Uses Gemini 2.5 Flash with thinking mode for intelligent extraction
- Outputs structured XML format with sections and metadata
- Displays Gemini's thinking process during extraction

### Streaming Responses
- Real-time streaming from Contextual AI
- Progressive display using Rich library
- Automatic conversation context management

### Fact-Checking Validation
- Streams Gemini's thinking process during validation
- Fact-by-fact verification against source documents
- Visual indicators (✅/❌) for each fact
- Accuracy scoring with confidence levels

## API Documentation

The system integrates with:
- **Google Gemini API** - For PDF extraction and validation
- **Contextual AI** - For document storage and retrieval

## Requirements

- Python 3.8+
- Google Gemini API access
- Contextual AI account with agent configured

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.