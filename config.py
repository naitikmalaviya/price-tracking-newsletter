"""
Configuration settings for the price tracking newsletter application.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Application settings
MAX_CONCURRENT_REQUESTS = 5
NOTION_URL_PROPERTY_NAME = "Urls"
NOTION_API_VERSION = "2022-06-28"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
