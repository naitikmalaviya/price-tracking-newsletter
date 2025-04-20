import logging
from typing import List, Dict, Any
import requests
from datetime import date, datetime

from config import NOTION_API_KEY, NOTION_DATABASE_ID, NOTION_URL_PROPERTY_NAME, NOTION_API_VERSION, LOWEST_PRICE_PROPERTY_NAME, LOWEST_PRICE_DATE_PROPERTY_NAME
from models.WishListItem import WishlistItem # Import the model

logger = logging.getLogger(__name__)

class NotionLoader:
    """
    A class to load product data from a Notion database and update properties.
    
    The Notion database should have columns for product URLs, lowest price, and lowest price date.
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
        self.lowest_price_prop = LOWEST_PRICE_PROPERTY_NAME
        self.lowest_price_date_prop = LOWEST_PRICE_DATE_PROPERTY_NAME
        self.headers = {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json"
        }
        
        if not self.notion_api_key:
            raise ValueError("NOTION_API_KEY environment variable is not set")
        if not self.notion_database_id:
            raise ValueError("NOTION_DATABASE_ID environment variable is not set")

    def _parse_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to parse different property types from Notion API response."""
        parsed = {}
        # URL
        url_prop = properties.get(self.url_property_name, {})
        if url_prop.get("type") == "title":
            rich_text = url_prop.get("title", [])
            if rich_text and rich_text[0].get("text", {}).get("content"):
                parsed['url'] = rich_text[0]["text"]["content"]

        # Lowest Price (Number property)
        lowest_price_prop_data = properties.get(self.lowest_price_prop, {})
        if lowest_price_prop_data.get("type") == "number":
            parsed['lowest_price_so_far'] = lowest_price_prop_data.get("number")

        # Lowest Price Date (Date property)
        lowest_price_date_prop_data = properties.get(self.lowest_price_date_prop, {})
        if lowest_price_date_prop_data.get("type") == "date":
            date_info = lowest_price_date_prop_data.get("date")
            if date_info and date_info.get("start"):
                try:
                    # Notion date format is YYYY-MM-DD
                    parsed['lowest_price_date'] = datetime.strptime(date_info["start"], "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Could not parse date: {date_info['start']}")
                    parsed['lowest_price_date'] = None

        return parsed

    def load_items(self) -> List[Dict[str, Any]]:
        """
        Load product data (URL, page ID, lowest price info) from the Notion database.
        
        Returns:
            A list of dictionaries, each containing 'page_id', 'url',
            'lowest_price_so_far', and 'lowest_price_date'.
        """
        
        query_url = f"https://api.notion.com/v1/databases/{self.notion_database_id}/query"
        items_data = []
        has_more = True
        next_cursor = None

        while has_more:
            payload = {}
            if next_cursor:
                payload['start_cursor'] = next_cursor

            try:
                logger.info(f"Querying Notion database: {self.notion_database_id} (Cursor: {next_cursor})")
                response = requests.post(query_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    logger.info("No results found in this Notion page batch.")
                    break # Exit if no results

                for result in results:
                    page_id = result.get("id")
                    properties = result.get("properties", {})
                    parsed_props = self._parse_properties(properties)
                    
                    if page_id and parsed_props.get('url'):
                        item_info = {
                            'page_id': page_id,
                            'url': parsed_props['url'],
                            'lowest_price_so_far': parsed_props.get('lowest_price_so_far'),
                            'lowest_price_date': parsed_props.get('lowest_price_date')
                        }
                        items_data.append(item_info)
                    else:
                        logger.warning(f"Skipping entry: Missing page_id or URL. Data: {result}")
                
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor")
                if not has_more:
                    logger.info("No more pages to fetch from Notion.")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching data from Notion: {e}")
                has_more = False
            except Exception as e:
                 logger.error(f"An unexpected error occurred during Notion fetch: {e}")
                 has_more = False

        logger.info(f"Loaded data for {len(items_data)} items from Notion")
        return items_data

    def update_lowest_price(self, page_id: str, lowest_price: float, price_date: date):
        """
        Update the 'Lowest Price' and 'Lowest Price Date' properties for a specific page in Notion.

        Args:
            page_id: The ID of the Notion page to update.
            lowest_price: The new lowest price to set.
            price_date: The date the lowest price was observed.
        """
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        properties_payload = {
            self.lowest_price_prop: {
                "number": lowest_price
            },
            self.lowest_price_date_prop: {
                "date":
                {
                    "start": price_date.isoformat()
                }
            }
        }
        
        payload = {"properties": properties_payload}
        
        try:
            logger.info(f"Updating Notion page {page_id} with lowest price {lowest_price} on {price_date}")
            response = requests.patch(update_url, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully updated Notion page {page_id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating Notion page {page_id}: {e}. Response: {response.text}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Notion update for page {page_id}: {e}")
