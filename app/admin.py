from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from app.models import db,Book, TransactionModel, ShippingAddress
from datetime import datetime
import re
from .cloud_storage import upload_book_file, allowed_file, storage_client, BUCKET_NAME
import uuid
from werkzeug.utils import secure_filename
from .gemini_utils import initialize_gemini, generate_book_description
from .notifications import send_shipping_notification

# Create the admin blueprint
admin = Blueprint('admin', __name__)

@admin.route('/admin')
def admin_page():
    total_books = Book.query.count()
    new_orders = TransactionModel.query.filter_by(status="Pending").count()
    low_stock = Book.query.filter(Book.is_purchasable == True, Book.stock_quantity < 100).count()
    recent_orders = TransactionModel.query.order_by(TransactionModel.purchase_date.desc()).limit(5).all()


    return render_template('admin_base.html', 
                           total_books=total_books, 
                           new_orders=new_orders, 
                           low_stock=low_stock, 
                           recent_orders=recent_orders)

@admin.route('/admin/order/<int:order_id>')
def view_order(order_id):
    # Fetch the order
    order = TransactionModel.query.get_or_404(order_id)
    
    # Fetch the shipping address
    shipping_address = ShippingAddress.query.get(order.shipping_address_id)
    
    # Fetch the book details
    book = Book.query.get(order.book_id)
    
    return render_template('admin_order_detail.html', 
                          order=order, 
                          shipping_address=shipping_address,
                          book=book)



@admin.route('/All_books', methods=['GET', 'POST'])
def books():
    if request.method == 'POST':
        action = request.form.get('action')
        book_id = request.form.get('book_id')
        book = Book.query.get_or_404(book_id)
        
        if action == 'update_stock':
            book.stock_quantity = request.form.get('stock')
            db.session.commit()
            flash('Stock updated successfully', 'success')
            
        elif action == 'update_price':
            book.price = request.form.get('price')
            db.session.commit()
            flash('Price updated successfully', 'success')
            
        elif action == 'delete_book':
            db.session.delete(book)
            db.session.commit()
            flash('Book deleted successfully', 'success')
            
        return redirect(url_for('admin.books'))
        
    # For GET requests, show all books
    books = Book.query.all()  
    return render_template('books.html', books=books)
# In your route handler:
@admin.route('/add-book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        # Get form data
        barcode = request.form.get('barcode')
        title = request.form.get('title')
        author = request.form.get('author')
        price = request.form.get('price')
        book_format = request.form.get('format')
        condition = request.form.get('condition')
        stock = request.form.get('stock')
        description = request.form.get('description')
        image_url = request.form.get('image_url')
        file_url = None  # Default to None for the book PDF
        
        # For PDF books, ensure condition is "New"
        if book_format == 'PDF':
            condition = 'New'
        
        # Validate required fields
        if not all([barcode, title, author, price, book_format, condition, stock]):
            print(f"Missing fields: barcode={barcode}, title={title}, author={author}, price={price}, format={book_format}, condition={condition}, stock={stock}")
            flash('Please fill in all required fields', 'error')
            return render_template('add_book.html')
        
        # If description is empty, generate one using Gemini
        if not description and title and author:
            generated_description = generate_book_description(title, author)
            if generated_description:
                description = generated_description
        
        # Handle image upload to Google Cloud Storage
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            
            if not allowed_file(image_file.filename):
                flash('Invalid image format. Allowed formats: png, jpg, jpeg, gif', 'error')
                return render_template('add_book.html')
            
            cloud_image_url = upload_book_file(image_file)  # Upload the image
            
            if cloud_image_url:
                image_url = cloud_image_url
            else:
                flash('Failed to upload image to cloud storage', 'error')
                return render_template('add_book.html')
        
        # Handle book file (PDF) upload to Google Cloud Storage
        if book_format == 'PDF':
            # PDF upload is mandatory for PDF books
            if 'pdf_file' not in request.files or not request.files['pdf_file'].filename:
                flash('PDF file is required for PDF books', 'error')
                return render_template('add_book.html')
                
            book_file = request.files['pdf_file']
            
            # Restrict to PDF files only
            if book_file.filename.rsplit('.', 1)[1].lower() != 'pdf':
                flash('Invalid file format. Allowed formats: pdf', 'error')
                return render_template('add_book.html')
            
            # Use the same upload_book_file function for PDF as well
            cloud_file_url = upload_book_file(book_file)
            
            if cloud_file_url:
                file_url = cloud_file_url
            else:
                flash('Failed to upload PDF to cloud storage', 'error')
                return render_template('add_book.html')
        
        try:
            # Create new book
            new_book = Book(
                barcode=barcode,
                title=title,
                author=author,
                description=description,
                price=float(price),
                format=book_format,
                condition=condition,
                is_lendable=False,
                is_purchasable=True,
                stock_quantity=int(stock),
                image_url=image_url,
                pdf_url=file_url,  # Store the PDF URL if available
                created_at=datetime.utcnow()
            )
            
            # Add to database
            db.session.add(new_book)
            db.session.commit()
            
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.add_book'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'error')
            return render_template('add_book.html')
    
    # GET request - display the form
    return render_template('add_book.html')

# Add an API endpoint to generate description dynamically
@admin.route('/api/generate-description', methods=['POST'])
def generate_description_api():
    data = request.get_json()
    title = data.get('title')
    author = data.get('author')
    
    if not title or not author:
        return jsonify({'error': 'Title and author are required'}), 400
    
    description = generate_book_description(title, author)
    
    if description:
        return jsonify({'description': description})
    else:
        return jsonify({'error': 'Failed to generate description'}), 500


@admin.route('/orders')
def orders():
    # Query to fetch orders (transactions)
    orders = TransactionModel.query.all()
    
    # Get any flash messages
    message = request.args.get('message')
    success = request.args.get('success', 'true') == 'true'
    
    # Pass the orders to the template
    return render_template('orders.html', orders=orders, message=message, success=success)

@admin.route('/complete-order/<int:order_id>', methods=['POST'])
def complete_order(order_id):
    try:
        # Get the order from the database
        order = TransactionModel.query.get_or_404(order_id)
        
        # Update status to complete
        order.status = 'Completed'
        
        # Commit changes to the database
        db.session.commit()
        
        # Send the appropriate notification email based on the delivery option
        email_sent = send_shipping_notification(order.user, order)
        
        # Optionally send SMS notification (if implemented)
        # sms_sent = send_shipping_sms(order.user, order.id)
        
        if email_sent:
            # Redirect with success message
            return redirect(url_for('admin.orders', message="Order marked as complete and notification sent successfully!", success=True))
        else:
            # Email sending failed but order updated
            return redirect(url_for('admin.orders', message="Order marked as complete but notification could not be sent.", success=True))
    
    except Exception as e:
        # Order update failed
        db.session.rollback()  # Rollback in case of an error
        return redirect(url_for('admin.orders', message=f"Failed to update order. Error: {str(e)}", success=False))