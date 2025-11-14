"""
Configuration management for Preceptor Feedback Bot.
Loads settings from environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # GCP Settings
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "meded-gcp-sandbox")
    GCP_REGION = os.getenv("GCP_REGION", "us-central1")
    GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", None)
    
    # Model Settings
    MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash-exp")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
    
    # Conversation Settings
    MAX_TURNS = int(os.getenv("MAX_TURNS", "10"))
    MIN_COMPETENCY_COVERAGE = int(os.getenv("MIN_COMPETENCY_COVERAGE", "3"))
    
    # Logging Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "./logs")
    
    # System Prompt Path
    SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "./prompts/system_prompt.txt")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GCP_PROJECT_ID:
            raise ValueError("GCP_PROJECT_ID must be set")
        if not cls.GCP_REGION:
            raise ValueError("GCP_REGION must be set")
        return True
    
    @classmethod
    def get_model_display_name(cls):
        """Get human-readable model name"""
        model_map = {
            "gemini-2.0-flash-001": "Gemini 2.0 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro",
            "claude-3-5-sonnet-v2@20241022": "Claude 3.5 Sonnet",
            "claude-sonnet-4-5@20250514": "Claude Sonnet 4.5"
        }
        return model_map.get(cls.MODEL_NAME, cls.MODEL_NAME)