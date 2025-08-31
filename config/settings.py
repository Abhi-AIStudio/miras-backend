import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.5-flash"
    GEMINI_THINKING_BUDGET = -1  # Dynamic thinking
    
    # Contextual AI Configuration
    CONTEXTUAL_API_KEY = os.getenv("CONTEXTUAL_API_KEY")
    CONTEXTUAL_AGENT_ID = os.getenv("CONTEXTUAL_AGENT_ID")
    CONTEXTUAL_DATASTORE_ID = os.getenv("CONTEXTUAL_DATASTORE_ID")
    CONTEXTUAL_BASE_URL = "https://api.contextual.ai/v1"
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # File Processing Settings
    MAX_PDF_SIZE_MB = 50
    MAX_PAGES = 1000
    
    # Streaming Settings
    STREAM_CHUNK_SIZE = 1024
    STREAM_TIMEOUT = 30  # seconds

settings = Settings()