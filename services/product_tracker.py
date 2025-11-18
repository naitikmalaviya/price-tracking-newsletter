import logging
import asyncio
from typing import List, Dict, Any, Optional
import json
import os

from browser_use import CodeAgent
from models.WishListItem import WishlistItem
from models.ScrapedProductData import ScrapedProductData
from config import GEMINI_API_KEY, MAX_CONCURRENT_REQUESTS, PREFERRED_BOTTOM_SIZE, PREFERRED_SHOE_SIZE, PREFERRED_TOP_SIZE

logger = logging.getLogger(__name__)

async def process_product(item_data: Dict[str, Any]) -> Optional[WishlistItem]:
    """Process a single product URL and return WishlistItem data, including original lowest price info."""
    url = item_data.get('url')
    page_id = item_data.get('page_id')
    lowest_price_so_far = item_data.get('lowest_price_so_far')
    lowest_price_date = item_data.get('lowest_price_date')
    output_filename = f"{page_id}.json"

    if not url or not page_id:
        logger.warning(f"Skipping item due to missing URL or page_id: {item_data}")
        return None

    try:
        os.environ['GOOGLE_API_KEY'] = str(GEMINI_API_KEY)
        
        task_description = f"""
        Go to {url} and extract the following product information:
        - Product name (full title as displayed)
        - Main product image URL:
            - Find the PRIMARY/HERO product image (usually the largest, most prominent image)
            - Look for images in these common locations:
                * Main product gallery (first/default image)
                * Hero image section
                * Primary product showcase area
            - Extract the FULL, DIRECT image URL that:
                * Ends with image extensions: .jpg, .jpeg, .png, .webp, .avif
                * Is a complete URL starting with http:// or https://
                * Points directly to the image file (not a thumbnail or placeholder)
            - Common image selectors to check:
                * img[data-main-image], img[data-hero], img.product-image
                * Images inside .product-gallery, .hero-image, .main-image containers
                * The largest img element in the product area
            - VALIDATION STEPS:
                * Verify the URL is complete and accessible
                * Ensure it's not a data: URL or placeholder
                * If multiple images exist, choose the main/hero image (usually first or largest)
                * If no valid image found, set to empty string ""
        - Current price (as a numerical value)
        - Discount percentage (if any, otherwise 0.0)
        - Product type classification (shoe, top, bottom, or other)

        For products requiring size selection, please select the preferred size:
        - Shoe: {PREFERRED_SHOE_SIZE}
        - Top: {PREFERRED_TOP_SIZE}
        - Bottom: {PREFERRED_BOTTOM_SIZE}

        If the preferred size is unavailable, disabled, or missing, set the price to -1.0.
        
        Save the extracted data to a JSON file named '{output_filename}'. The JSON object should have the following keys: "name", "image_url", "price", "discount", "product_type".
        """

        agent = CodeAgent(task=task_description)
        await agent.run()
        
        if os.path.exists(output_filename):
            with open(output_filename, 'r') as f:
                result_data = json.load(f)

            os.remove(output_filename) # Clean up the file

            scraped_data = ScrapedProductData(**result_data)
            
            final_item = WishlistItem(
                page_id=page_id,
                **scraped_data.model_dump(),
                lowest_price_so_far=lowest_price_so_far,
                lowest_price_date=lowest_price_date
            )
            return final_item
        else:
            logger.error(f"Output file '{output_filename}' not found after agent run.")
            return None
    except Exception as e:
        logger.error(f"Error processing product URL {url} (Page ID: {page_id}): {str(e)}")

        return WishlistItem(
            page_id=page_id,
            name="Processing Error",
            url=url,
            price=-1.0, # Indicate error/unavailability
            discount=0.0,
            image_url="",
            lowest_price_so_far=lowest_price_so_far,
            lowest_price_date=lowest_price_date
        )

async def process_products(items_data: List[Dict[str, Any]], max_concurrent: int = MAX_CONCURRENT_REQUESTS) -> List[WishlistItem]:
    """Process multiple product items (dict from Notion) in parallel with a concurrency limit."""
    results = []
    
    for i in range(0, len(items_data), max_concurrent):
        batch = items_data[i:i + max_concurrent]
        batch_tasks = [process_product(item_data) for item_data in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Caught exception during batch processing: {result}")
            elif result is not None:
                results.append(result)
    
    return results
