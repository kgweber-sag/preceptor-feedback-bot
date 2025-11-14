"""
Application logging for Preceptor Feedback Bot.
Separate from conversation logs - tracks application events, errors, and debugging info.
"""

import logging
import os
from datetime import datetime

from config import Config


class AppLogger:
    """Application logger for tracking system events"""

    _instance = None
    _logger = None

    def __new__(cls):
        """Singleton pattern to ensure one logger instance"""
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        """Set up the application logger"""
        # Create logger
        self._logger = logging.getLogger("preceptor_feedback_bot")

        # Use configured log level from Config (default to INFO if invalid)
        level_name = getattr(Config, "LOG_LEVEL", "INFO") or "INFO"
        try:
            level = getattr(logging, level_name.upper())
        except Exception:
            level = logging.INFO

        self._logger.setLevel(level)

        # Prevent duplicate handlers if reinitialized
        if self._logger.handlers:
            return

        # Create logs directory if needed
        os.makedirs(Config.LOG_DIRECTORY, exist_ok=True)

        # File handler - write logs to file
        log_filename = (
            f"{Config.LOG_DIRECTORY}/app_{datetime.now().strftime('%Y%m%d')}.log"
        )
        try:
            file_handler = logging.FileHandler(log_filename)
        except Exception:
            # If file handler fails (permissions, path), fall back to console-only
            file_handler = None

        # Handler levels follow configured level by default
        handler_level = level

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(handler_level)

        if file_handler:
            file_handler.setLevel(handler_level)

        # Format with timestamp, level, and message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        if file_handler:
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    def info(self, message: str, **kwargs):
        """Log info message with optional context"""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context"""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional context"""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context"""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with additional context fields"""
        if kwargs:
            context_str = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            full_message = f"{message} | {context_str}"
        else:
            full_message = message

        self._logger.log(level, full_message)  # type: ignore

    def conversation_started(self, student_name: str = "unknown", model: str = None):
        """Log conversation start event"""
        self.info(
            "Conversation started",
            student=student_name,
            model=model or Config.MODEL_NAME,
        )

    def conversation_completed(
        self,
        student_name: str = "unknown",
        turn_count: int = 0,
        conversation_log_path: str = None,
    ):
        """Log conversation completion event"""
        self.info(
            "Conversation completed",
            student=student_name,
            turns=turn_count,
            log_file=conversation_log_path,
        )

    def feedback_generated(
        self, student_name: str = "unknown", premature: bool = False
    ):
        """Log feedback generation event"""
        if premature:
            self.warning(
                "Feedback generated prematurely by model", student=student_name
            )
        else:
            self.info("Feedback generated", student=student_name)

    def feedback_refined(self, student_name: str = "unknown", refinement: str = ""):
        """Log feedback refinement event"""
        self.info(
            "Feedback refined",
            student=student_name,
            request=refinement[:50],  # Truncate long refinement requests
        )

    def model_error(self, error_message: str, student_name: str = "unknown"):
        """Log model/API errors"""
        self.error(f"Model error: {error_message}", student=student_name)

    def app_started(self):
        """Log application startup"""
        self.info(
            "Application started",
            project=Config.GCP_PROJECT_ID,
            region=Config.GCP_REGION,
            model=Config.MODEL_NAME,
        )

    def config_validation_failed(self, error: str):
        """Log configuration validation failure"""
        self.error(f"Configuration validation failed: {error}")


# Global logger instance
logger = AppLogger()
