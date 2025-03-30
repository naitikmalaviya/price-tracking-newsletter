import logging
import asyncio
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from browser_use import Agent, Controller
from models.WishListItem import WishlistItem
from config import GEMINI_API_KEY, MAX_CONCURRENT_REQUESTS

logger = logging.getLogger(__name__)

async def process_product(url: str) -> WishlistItem:
    """Process a single product URL and return WishlistItem data."""
    try:
        controller = Controller(output_model=WishlistItem)

        initial_actions = [
            {'go_to_url': {'url': url}}
        ]
        
        agent = Agent(
            task='Extract information about the product on the current page. If it is a shoe, select size UK 9. Capture the product image URL, current price, and full product name.',
            llm=ChatGoogleGenerativeAI(model='gemini-2.0-flash-lite', api_key=SecretStr(str(GEMINI_API_KEY))),
            controller=controller,
            initial_actions=initial_actions
        )
        
        history = await agent.run()
        result = history.final_result()
        
        if result:
            parsed = WishlistItem.model_validate_json(result)
            return parsed
        return None
    except Exception as e:
        logger.error(f"Error processing product URL {url}: {str(e)}")
        return None

async def process_products(urls: List[str], max_concurrent: int = MAX_CONCURRENT_REQUESTS) -> List[WishlistItem]:
    """Process multiple product URLs in parallel with a concurrency limit."""
    # Create batches of URLs to process concurrently
    results = []
    
    for i in range(0, len(urls), max_concurrent):
        batch = urls[i:i + max_concurrent]
        batch_tasks = [process_product(url) for url in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Error processing product: {result}")
            elif result:
                results.append(result)
    
    return results
