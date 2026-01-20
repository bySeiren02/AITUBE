import os
import logging
from typing import Dict, Any

class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}

    AI_DETECTION_THRESHOLD = 0.6
    ANALYSIS_TIMEOUT = 2.0  # seconds
    USE_REAL_AI_MODEL = os.getenv("USE_REAL_AI_MODEL", "False").lower() == "true"

    LOG_LEVEL = logging.INFO if not DEBUG else logging.DEBUG

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return {
            "debug": cls.DEBUG,
            "host": cls.HOST,
            "port": cls.PORT,
            "max_file_size": cls.MAX_FILE_SIZE,
            "ai_threshold": cls.AI_DETECTION_THRESHOLD,
            "timeout": cls.ANALYSIS_TIMEOUT,
            "use_real_ai_model": cls.USE_REAL_AI_MODEL,
        }
