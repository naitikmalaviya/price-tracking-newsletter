import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from models.WishListItem import WishlistItem
from config import SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL, SMTP_SERVER, SMTP_PORT

logger = logging.getLogger(__name__)

class EmailSender:
    """Handles sending emails using SMTP."""

    def __init__(self):
        """Initialize the EmailSender."""
        self.sender_email = SENDER_EMAIL
        self.sender_password = SENDER_PASSWORD
        self.recipient_email = RECIPIENT_EMAIL
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT

        if not all([self.sender_email, self.sender_password, self.recipient_email, self.smtp_server, self.smtp_port]):
            raise ValueError("Email configuration (sender, password, recipient, server, port) is not fully set in environment variables.")

        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def _format_html_content(self, items: List[WishlistItem]) -> str:
        """Formats the list of WishlistItems into an HTML email body."""
        try:
            template = self.env.get_template('email_template.html')
            # Filter out items with price -1.0 (unavailable) before rendering
            available_items = [item for item in items if item.price > 0.0]
            unavailable_items = [item for item in items if item.price == -1.0]
            html_content = template.render(
                available_items=available_items,
                unavailable_items=unavailable_items,
                recipient_email=self.recipient_email # Optional: Personalize if needed
            )
            return html_content
        except Exception as e:
            logger.error(f"Error loading or rendering email template: {e}")
            # Fallback to a simple text representation if template fails
            fallback_content = "<h1>Price Tracking Update</h1>"
            fallback_content += "<h2>Available Items:</h2><ul>"
            for item in available_items:
                fallback_content += f"<li>{item.name} - Price: {item.price}, Discount: {item.discount}% <a href='{item.url}'>Link</a></li>"
            fallback_content += "</ul>"
            fallback_content += "<h2>Unavailable Items:</h2><ul>"
            for item in unavailable_items:
                 fallback_content += f"<li>{item.name} - <a href='{item.url}'>Link</a></li>"
            fallback_content += "</ul>"
            return fallback_content


    def send_email(self, subject: str, items: List[WishlistItem]):
        """
        Sends an email with the provided subject and list of items.

        Args:
            subject: The subject line of the email.
            items: A list of WishlistItem objects to include in the email body.
        """
        if not items:
            logger.info("No items to send in the email.")
            return

        html_body = self._format_html_content(items)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.sender_email
        message["To"] = self.recipient_email

        # Attach the HTML part
        message.attach(MIMEText(html_body, "html"))

        try:
            logger.info(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                logger.info("Logging into SMTP server")
                server.login(self.sender_email, self.sender_password)
                logger.info(f"Sending email to {self.recipient_email}")
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
                logger.info("Email sent successfully")
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication Error: Check sender email and password.")
        except smtplib.SMTPConnectError:
             logger.error(f"SMTP Connection Error: Could not connect to {self.smtp_server}:{self.smtp_port}.")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

