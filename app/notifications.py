import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import dotenv_values
from flask import render_template

# Load environment variables from the .env file using dotenv_values
secrets = dotenv_values(".env")

def send_email(receiver_email, subject, message):
    """Send an email using Gmail SMTP."""
    sender_email = secrets.get("GMAIL_USER")
    password = secrets.get("GMAIL_PASS")
    
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        body = MIMEText(message, 'html')  
        msg.attach(body)
        
        # Use SSL context for secure connection
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"An error occurred while sending email: {e}")

# Converts the user phone number to correct format
def convert_number(phone_number):
    if phone_number.startswith('0'):
        return '+27' + phone_number[1:]
    else:
        return phone_number

def send_sms(to_number, message_body):
    try:
        # Twilio Account SID and Auth Token
        account_sid = secrets.get("ACCOUNT_SID")
        auth_token = secrets.get("AUTH_TOKEN")
        
        # Twilio phone number
        from_number = secrets.get("FROM_NUMBER")

        # Convert phone number to correct format
        formatted_number = convert_number(to_number)
        
        # Create a Twilio client
        client = Client(account_sid, auth_token)

        # Send an SMS
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=formatted_number
        )
        print(f"SMS sent successfully. SID: {message.sid}")
    except Exception as e:
        print(f"An error occurred while sending SMS: {e}")

def send_purchase_confirmation(user, order_items, order_total, shipping_address=None, delivery_date=None, pdf_books=None):
    """
    Send a purchase confirmation email to the user.
    
    Args:
        user: User object containing email and name
        order_items: List of dictionaries with book details (title, author, price, image_url)
        order_total: Total price of the order
        shipping_address: Shipping address for physical books (optional)
        delivery_date: Estimated delivery date (optional)
        pdf_books: List of dictionaries with PDF details (title, author, download_link, image_url) (optional)
    """
    has_physical_books = shipping_address is not None
    has_pdf_books = pdf_books is not None and len(pdf_books) > 0

    try:
        # Generate HTML content using Flask's render_template
        html_content = render_template('purchase_confirmation.html',
            user_name=user.name,
            order_items=order_items,
            order_total=order_total,
            has_physical_books=has_physical_books,
            shipping_address=shipping_address,
            delivery_date=delivery_date,
            has_pdf_books=has_pdf_books,
            pdf_books=pdf_books
        )
        
        # Send the email using our smtplib-based function
        send_email(
            receiver_email=user.email,
            subject="Your Purchase Confirmation",
            message=html_content
        )
        
        print("Purchase confirmation email sent successfully.")
        
    except Exception as e:
        print(f"An error occurred while sending the purchase confirmation email: {e}")

def send_shipping_notification(user, order):
    """
    Send a shipping notification email to the user.
    
    Args:
        user: User object containing email and name
        order: TransactionModel object containing order details
    """
    try:
        # Determine the delivery method and whether the order has digital items
        delivery_method = order.delivery_option  # e.g., "delivery", "store_pickup", "digital"
        has_digital_items = order.book.format == 'PDF'  # Check if the book is digital

        # Generate HTML content using Flask's render_template
        html_content = render_template('shipping_notification.html',
            user_name=f"{user.first_name} {user.last_name}",
            order_id=order.id,
            purchase_date=order.purchase_date.strftime('%d %B %Y'),
            order_total=order.total_price,
            delivery_method=delivery_method,
            has_digital_items=has_digital_items
        )
        
        # Send the email using our smtplib-based function
        send_email(
            receiver_email=user.email,
            subject="Your Order Confirmation",  # Updated subject to be more generic
            message=html_content
        )
        
        print(f"Order confirmation email sent successfully to {user.email}.")
        return True
        
    except Exception as e:
        print(f"An error occurred while sending the order confirmation email: {e}")
        return False
# You can also add SMS notification if needed
def send_shipping_sms(user, order_id):
    """
    Send a shipping notification SMS to the user.
    
    Args:
        user: User object containing phone number
        order_id: The ID of the order that has been shipped
    """
    if not user.phone:
        print("No phone number available for SMS notification")
        return False
    
    try:
        message_body = f"Good news! Your order #{order_id} has been shipped and is on its way to you. Thank you for your purchase!"
        send_sms(user.phone, message_body)
        return True
    except Exception as e:
        print(f"An error occurred while sending shipping SMS: {e}")
        return False
