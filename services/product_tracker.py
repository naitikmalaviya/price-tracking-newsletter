import logging
import asyncio
from typing import List, Dict, Any, Optional
import os

from browser_use import Agent, Controller
from browser_use.llm import ChatGoogle

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

        task_description = f"""Extract product information from this e-commerce page and determine availability for my preferred size.

**Product Information to Extract:**
1. Product name (full title as displayed)
2. **Main product image URL - CRITICAL REQUIREMENTS:**
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
   - **VALIDATION STEPS:**
     * Verify the URL is complete and accessible
     * Ensure it's not a data: URL or placeholder
     * If multiple images exist, choose the main/hero image (usually first or largest)
     * If no valid image found, set to empty string ""
3. Product type classification (shoe, top, bottom, or other)

**Size Selection Process:**
For products requiring size selection (shoes, tops, bottoms):
- Shoe: Select size {PREFERRED_SHOE_SIZE} or closest equivalent
- Top: Select size {PREFERRED_TOP_SIZE} or closest equivalent
- Bottom: Select size {PREFERRED_BOTTOM_SIZE} or closest equivalent

**Availability & Pricing Logic:**
If preferred size is unavailable, disabled, or missing: Set price to -1.0
If size is available OR product doesn't require size selection:
- Extract current price as numerical value (e.g., 49.99)
- Look for availability indicators: "Add to Cart", "In Stock", "Available"
- Avoid out-of-stock indicators: "Out of Stock", "Unavailable", "Notify Me"

**Discount Calculation:**
For available products (price > 0):
- Find discount indicators: "% off", "Save $X", crossed-out original price
- Calculate percentage: ((Original Price - Sale Price) / Original Price) × 100
- If no discount found, set to 0.0

**Output Requirements:**
- price: Numerical value or -1.0 if unavailable
- discount: Percentage as number (e.g., 25.0 for 25% off) or 0.0
- name: Exact product title
- image_url: Valid, complete image URL or empty string ""
- url: Current page URL

Focus on accuracy and handle edge cases gracefully. Pay special attention to finding the correct main product image URL."""

        initial_actions = [
            {'go_to_url': {'url': url}}
        ]
        
        # Initialize LLM with latest Gemini model from browser-use
        os.environ['GOOGLE_API_KEY'] = str(GEMINI_API_KEY)
        llm = ChatGoogle(model='gemini-2.0-flash-exp')
        
        agent = Agent(
            task=task_description,
            llm=llm,
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
