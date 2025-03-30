import asyncio
import logging

from config import MAX_CONCURRENT_REQUESTS
from services.notion_loader import NotionLoader
from services.product_tracker import process_products

logger = logging.getLogger(__name__)

async def main():
    """
    Main function to control the price tracking workflow.
    """
    logger.info("Starting price tracking workflow")
    
    # Step 1: Load product URLs from Notion
    logger.info("Loading URLs from Notion database")
    notion_loader = NotionLoader()
    product_urls = notion_loader.load_urls()
    
    if not product_urls:
        logger.warning("No URLs loaded from Notion database. Exiting.")
        return
    
    # Step 2: Process products and track prices
    logger.info(f"Processing {len(product_urls)} products...")
    results = await process_products(product_urls, max_concurrent=MAX_CONCURRENT_REQUESTS)
    
    if not results:
        logger.warning("No products were successfully processed")
        return
    
    # Step 3: Output results
    logger.info(f"Successfully processed {len(results)} products")
    print("\n" + "="*50)
    print("PRICE TRACKING RESULTS")
    print("="*50)
    
    for item in results:
        print(f"\nProduct: {item.name}")
        print(f"URL: {item.url}")
        print(f"Price: {item.price}")
        print(f"Image URL: {item.image_url}")
        print("-"*50)
    
    #TODO: Implement newsletter sending functionality and price history saving

if __name__ == "__main__":
    asyncio.run(main())
