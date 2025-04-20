import asyncio
import logging
from datetime import date

from config import MAX_CONCURRENT_REQUESTS
from services.notion_loader import NotionLoader
from services.product_tracker import process_products
from services.email_sender import EmailSender

logger = logging.getLogger(__name__)

async def main():
    """
    Main function to control the price tracking workflow.
    """
    logger.info("Starting price tracking workflow")
    today = date.today()
    
    # Step 1: Load product items (including IDs and lowest price history) from Notion
    logger.info("Loading items from Notion database")
    notion_loader = NotionLoader()
    items_to_track = notion_loader.load_items() 
    
    if not items_to_track:
        logger.warning("No items loaded from Notion database. Exiting.")
        return
    
    # Step 2: Process products to get current prices
    logger.info(f"Processing {len(items_to_track)} items...")
    processed_items = await process_products(items_to_track, max_concurrent=MAX_CONCURRENT_REQUESTS)
    
    if not processed_items:
        logger.warning("No products were successfully processed")
        return

    # Step 3: Compare prices, update Notion if new lowest found
    logger.info("Comparing current prices with historical lows and updating Notion if necessary.")
    items_for_email = []
    for item in processed_items:
        if item.price < 0:
            logger.info(f"Skipping price comparison for unavailable/error item: {item.name} ({item.url})")
            items_for_email.append(item)
            continue

        if item.lowest_price_so_far is None or item.price < item.lowest_price_so_far:
            logger.info(f"New lowest price found for {item.name}: {item.price} (was {item.lowest_price_so_far})")
            if item.lowest_price_so_far is not None:
                item.lowest_price_so_far = item.price
                item.lowest_price_date = today
            notion_loader.update_lowest_price(item.page_id, item.price, today)
        else:
             logger.info(f"Current price {item.price} for {item.name} is not lower than recorded lowest {item.lowest_price_so_far} on {item.lowest_price_date}")

        items_for_email.append(item)

    # Step 4: Send email notification
    logger.info("Preparing to send email notification")
    try:
        email_sender = EmailSender()
        today_date_str = today.strftime("%Y-%m-%d")
        subject = f"Price Tracking Update - {today_date_str}"
        email_sender.send_email(subject, items_for_email) 
        logger.info("Email sending process initiated.")
    except ValueError as e:
        logger.error(f"Email configuration error: {e}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    asyncio.run(main())
