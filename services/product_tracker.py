import logging
import asyncio
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from browser_use import Agent, Browser, BrowserConfig, Controller
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

    if not url or not page_id:
        logger.warning(f"Skipping item due to missing URL or page_id: {item_data}")
        return None

    try:
        controller = Controller(output_model=ScrapedProductData)

        task_description = f"""Objective: Extract product details, determine availability for a specific size (if applicable), and find the price and discount.

1.  **Initial Page Load & Basic Info:**
    - Extract the full product name.
    - Extract the main product image URL. **Validate this URL.** It should be a direct link to an image file (e.g., ending in .jpg, .png, .webp) or a usable image source URL. If an invalid or non-image URL is extracted, try to find the correct main image URL again. If a valid URL cannot be found, set the image URL field to null or an empty string.
    - Determine the product type (e.g., shoe, top, bottom, other).

2.  **Size Selection (Conditional):**
    - If the product type requires size selection (shoe, top, bottom):
        - Attempt to select the preferred size:
            - Shoe: {PREFERRED_SHOE_SIZE} or equivalent.
            - Top: {PREFERRED_TOP_SIZE} or equivalent.
            - Bottom: {PREFERRED_BOTTOM_SIZE} or equivalent.
        - Note whether the preferred size could be successfully selected/activated. If not (e.g., size option is disabled, greyed out, or not present), consider the preferred size unavailable.

3.  **Availability Check (Post Size Selection or General):**
    - **If size selection was attempted (Step 2):**
        - If the preferred size was *unavailable* or *could not be selected*, set 'price' to -1.0.
        - If the preferred size *was* selected, check *specifically* for availability indicators related to that size. Look for:
            - An active 'Add to Cart', 'Add to Bag', or 'Buy Now' button.
            - Explicit messages like 'In Stock', 'Available'.
            - Conversely, look for 'Out of Stock', 'Unavailable', 'Notify me' messages *after* size selection, or a disabled 'Add to Cart' button.
        - If the selected size is indicated as unavailable, set 'price' to -1.0.
    - **If size selection was NOT applicable (product type 'other' or no size options):**
        - Check the general availability of the product. Look for an active 'Add to Cart'/'Buy Now' button or explicit 'In Stock' messages. Check for general 'Out of Stock' messages.
        - If the product is indicated as unavailable, set 'price' to -1.0.

4.  **Price Extraction:**
    - If the 'price' has NOT been set to -1.0 in the previous steps (meaning the product/size is considered available):
        - Extract the current price. If a size was selected, ensure it's the price for *that specific size*. If no size was selected, get the general product price.
        - Set the extracted price in the 'price' field. Ensure it is a numerical value (e.g., 49.99).
    - If at any point availability cannot be confirmed or a price cannot be extracted despite the item seeming available, set 'price' to -1.0 as a fallback.

5.  **Discount Calculation:**
    - If the 'price' field is greater than 0.0:
        - Check for any indicated discounts (e.g., '% off', 'Save $X', original price vs. sale price).
        - Calculate or extract the discount percentage (e.g., 25.0 for 25% off). If calculating from a saved amount, use the formula: (Amount Saved / (Current Price + Amount Saved)) * 100. If calculating from original and sale price: ((Original Price - Sale Price) / Original Price) * 100.
        - Set the calculated percentage in the 'discount' field. Ensure it's a number.
    - If no discount is found or the price is -1.0, set the 'discount' field to 0.0.
"""

        initial_actions = [
            {'go_to_url': {'url': url}}
        ]
        
        agent = Agent(
            browser= Browser(config=BrowserConfig(headless=True, timeout=60_000)),
            task=task_description,
            llm=ChatGoogleGenerativeAI(model='gemini-2.5-flash', api_key=SecretStr(str(GEMINI_API_KEY))),
            
            controller=controller,
            initial_actions=initial_actions
        )
        
        history = await agent.run()
        result = history.final_result()
        
        if result:
            scraped_data = ScrapedProductData.model_validate_json(result)
            
            final_item = WishlistItem(
                page_id=page_id,
                **scraped_data.model_dump(),
                lowest_price_so_far=lowest_price_so_far,
                lowest_price_date=lowest_price_date
            )
            return final_item
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
