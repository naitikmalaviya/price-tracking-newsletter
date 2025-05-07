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

# Email configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com") # Default to Gmail
SMTP_PORT = int(os.getenv("SMTP_PORT", 587)) # Default to Gmail TLS port

# Application settings
MAX_CONCURRENT_REQUESTS =1
NOTION_URL_PROPERTY_NAME = "Urls"
NOTION_API_VERSION = "2022-06-28"
PREFERRED_SHOE_SIZE = "UK 9"
PREFERRED_TOP_SIZE = "S"
PREFERRED_BOTTOM_SIZE = "30"
LOWEST_PRICE_PROPERTY_NAME = "Lowest Price"
LOWEST_PRICE_DATE_PROPERTY_NAME = "Lowest Price Date"

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
