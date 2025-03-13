from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from app.models import db, User,Book, TransactionModel, ShippingAddress
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user,login_required, current_user,logout_user
from datetime import datetime
import re
from .cloud_storage import upload_book_image, allowed_file


# Create the admin blueprint
admin = Blueprint('admin', __name__)

@admin.route('/admin')
def admin_page():
    total_books = Book.query.count()
    new_orders = TransactionModel.query.filter_by(status="Pending").count()
    low_stock = Book.query.filter(Book.is_purchasable == True, Book.condition == "New").count()
    recent_orders = TransactionModel.query.order_by(TransactionModel.purchase_date.desc()).limit(5).all()


    return render_template('admin_base.html', 
                           total_books=total_books, 
                           new_orders=new_orders, 
                           low_stock=low_stock, 
                           recent_orders=recent_orders)

@admin.route('/books')
def books():
    # Query the books from the database
    books = Book.query.all()  # This fetches all books in the database

    # Pass the books to the template
    return render_template('books.html', books=books)


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
        
        # Validate required fields
        if not all([barcode, title, author, price, book_format, condition, stock]):
            flash('Please fill in all required fields', 'error')
            return render_template('add_book.html')
        
        # Handle image upload to Google Cloud Storage
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            
            if not allowed_file(image_file.filename):
                flash('Invalid image format. Allowed formats: png, jpg, jpeg, gif', 'error')
                return render_template('add_book.html')
                
            # Upload the image to Google Cloud Storage
            cloud_image_url = upload_book_image(image_file)
            
            if cloud_image_url:
                # If upload successful, use the cloud URL
                image_url = cloud_image_url
            else:
                flash('Failed to upload image to cloud storage', 'error')
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
                created_at=datetime.utcnow()
            )
            
            # Add to database
            db.session.add(new_book)
            db.session.commit()
            
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.add_books'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'error')
            return render_template('add_book.html')
    
    # GET request - display the form
    return render_template('add_book.html')

@admin.route('/orders')
def orders():
    # Query to fetch orders (transactions)
    orders = TransactionModel.query.all() 

    # Pass the orders to the template
    return render_template('orders.html', orders=orders)