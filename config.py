"""
    This file contains all project configs read from env file.
"""

import os
import logging
from dotenv import load_dotenv

class Config():
    """
    Main configuration class. Contains all the configurations for the project.
    """
    env = os.getenv("ENVIRONMENT")
    load_dotenv(f".env.{env}")
    DEBUG: bool = (env == "development")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    logging.basicConfig(level=logging.INFO)
config = Config()
