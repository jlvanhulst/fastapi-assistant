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
    
    DEBUG: bool = (os.getenv("DEBUG", "FALSE") == "TRUE")
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')


    logger.info(f"DEBUG: {DEBUG}")
    env = ".env.development" if DEBUG else ".env.production"
    env_found = load_dotenv(env)
    if not env_found:
        env = ".env"
        env_found = load_dotenv(env)
    if not env_found:
        logger.warning('No enviroment settings file used/found')
    else:
        logger.info(f"Enviroment settings file used: {env} ")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

config = Config()

if config.OPENAI_API_KEY is None:
    # the app does not run without it - so no point in continuing
    raise ValueError("OPENAI_API_KEY is not set - cannot run without it! Set it either in you OS or in .env or config.py")
