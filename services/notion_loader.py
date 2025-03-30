import logging
from typing import List
import requests

from config import NOTION_API_KEY, NOTION_DATABASE_ID, NOTION_URL_PROPERTY_NAME, NOTION_API_VERSION

logger = logging.getLogger(__name__)

class NotionLoader:
    """
    A class to load product URLs from a Notion database.
    
    The Notion database should have a column for product URLs.
    """
    
    def __init__(self, url_property_name: str = NOTION_URL_PROPERTY_NAME):
        """
        Initialize the Notion loader.
        
        Args:
            url_property_name: The name of the property in Notion that contains the product URLs.
        """
        self.notion_api_key = NOTION_API_KEY
        self.notion_database_id = NOTION_DATABASE_ID
        self.url_property_name = url_property_name
        
        if not self.notion_api_key:
            raise ValueError("NOTION_API_KEY environment variable is not set")
        if not self.notion_database_id:
            raise ValueError("NOTION_DATABASE_ID environment variable is not set")
    
    def load_urls(self) -> List[str]:
        """
        Load product URLs from the Notion database.
        
        Returns:
            A list of product URLs.
        """
        headers = {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json"
        }
        
        url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"
        
        try:
            logger.info(f"Querying Notion database: {self.notion_database_id}")
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            urls = []
            for result in data.get("results", []):
                properties = result.get("properties", {})
                url_property = properties.get(self.url_property_name, {})
                
                # Handle different types of URL properties
                url = None
                if url_property.get("type") == "title":
                    rich_text = url_property.get("title", [])
                    if rich_text and rich_text[0].get("text", {}).get("content"):
                        url = rich_text[0]["text"]["content"]
                
                if url:
                    urls.append(url)
            
            logger.info(f"Loaded {len(urls)} URLs from Notion")
            return urls
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from Notion: {e}")
            return []
