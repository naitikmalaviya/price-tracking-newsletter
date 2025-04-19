import asyncio
import logging
from datetime import datetime

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

    
    # Step 3: Send email notification
    logger.info("Preparing to send email notification")
    try:
        email_sender = EmailSender()
        today_date = datetime.now().strftime("%Y-%m-%d")
        subject = f"Price Tracking Update - {today_date}"
        email_sender.send_email(subject, results)
        logger.info("Email sending process initiated.")
    except ValueError as e:
        logger.error(f"Email configuration error: {e}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

    # TODO: Implement price history saving

if __name__ == "__main__":
    asyncio.run(main())
