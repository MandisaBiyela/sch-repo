from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from app.models import db, User,Book, TransactionModel, ShippingAddress, Review
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user,login_required, current_user,logout_user
from datetime import datetime, timedelta
from sqlalchemy import func
import re
import os
from dotenv import load_dotenv
from .notifications import send_email, send_sms, send_purchase_confirmation  # Import notification functions
    

# Blueprint for the main application routes
main = Blueprint('main', __name__)

# Regular expression for validating credit card numbers
CREDIT_CARD_PATTERN = r'^[0-9]{13,19}$'

# ----- AUTHENTICATION ROUTES -----
@main.route('/', methods=['GET', 'POST'])
def login():
    """
    Login page handling both admin and regular user authentication
    - Provides separate path for admin login
    - Validates user credentials and initializes session
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('isAdmin') 
        
        # Handle admin login with hardcoded credentials
        if is_admin == 'on':
            if email == 'admin@admin.com' and password == 'admin':
                return redirect(url_for('admin.admin_page'))
                
            else:
                flash('Incorrect admin details', 'error')
                return render_template('Login.html')

        # Handle regular user login
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password): 
            login_user(user)
            return redirect(url_for('main.bookstore'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('Login.html')

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    User registration functionality
    - Validates user input and checks for existing accounts
    - Creates new user with securely hashed password
    """
    if request.method == 'POST':
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists. Please log in or use a different email.", "error")
            return redirect(url_for('main.signup'))

        # Validate passwords
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('main.signup'))

        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create a new user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password
        )

        # Save user to database
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('main.login'))

    return render_template('Signup.html')

# ----- BOOKSTORE MAIN FUNCTIONALITY -----
@main.route('/books', methods=['GET', 'POST'])
@login_required
def bookstore():
    """
    Main bookstore page with book browsing and cart management
    - Handles book filtering and search
    - Manages shopping cart operations via AJAX
    - Provides book details for individual products
    - Handles review retrieval and submission
    """
    # Handle book detail requests with reviews
    if 'id' in request.args:
        try:
            book_id = request.args.get('id')
            book = Book.query.get(book_id)
            
            if not book:
                return jsonify({'error': f'Book with ID {book_id} not found'}), 404
                
            # Check if user has purchased this book
            can_review = False
            if current_user.is_authenticated:
                transaction = TransactionModel.query.filter(
                    TransactionModel.user_id == current_user.id,
                    TransactionModel.book_id == book.id,
                    TransactionModel.status == 'Completed' 
                ).first()
                can_review = transaction is not None
            
            # Get reviews for this book
            reviews = Review.query.filter_by(book_id=book.id).order_by(Review.created_at.desc()).all()
            reviews_data = []
            for review in reviews:
                user = User.query.get(review.user_id)
                # Make sure you're using a field that exists on your User model
                username = user.email if user else "Anonymous"  # Assuming email is used as username
                reviews_data.append({
                    'id': review.id,
                    'rating': review.rating,
                    'title': review.title,
                    'content': review.content,
                    'created_at': review.created_at.isoformat() if review.created_at else None,
                    'user': username
                })
            
            return jsonify({
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'price': float(book.price),
                'condition': book.condition,
                'format': book.format,
                'description': book.description,
                'barcode': book.barcode,
                'stock_quantity': book.stock_quantity,
                'is_lendable': book.is_lendable,
                'created_at': book.created_at.isoformat() if book.created_at else None,
                'image_url': book.image_url,
                'can_review': can_review,
                'reviews': reviews_data
            })
        except Exception as e:
            # Log the error
            print(f"Error in book detail request: {str(e)}")
            return jsonify({'error': 'An error occurred processing your request', 'details': str(e)}), 500
        

            # Step 1: Get the most frequently purchased book IDs
    recommended_book_ids = (
        db.session.query(TransactionModel.book_id, func.count(TransactionModel.book_id).label('purchase_count'))
        .group_by(TransactionModel.book_id)
        .order_by(func.count(TransactionModel.book_id).desc())
        .limit(4)  # Limit to 4 recommended books
        .all()
    )

    # Step 2: Extract book IDs from the query result
    book_ids = [book_id for book_id, _ in recommended_book_ids]

    # Step 3: Fetch the book details for the recommended books
    recommended_books = Book.query.filter(Book.id.in_(book_ids)).all()
    
    # Handle review submission
    if request.method == 'POST' and request.is_json:
        try:
            data = request.get_json()
            
            # If this is a review submission
            if 'review' in data:
                review_data = data['review']
                book_id = review_data.get('book_id')
                rating = review_data.get('rating')
                title = review_data.get('title')
                content = review_data.get('content')
                
                # Validate input
                if not all([book_id, rating, title, content]):
                    return jsonify({'error': 'Missing required review fields'}), 400
                
                # Check if user has purchased this book - FIXED CASE ISSUE HERE
                transaction = TransactionModel.query.filter(
                    TransactionModel.user_id == current_user.id,
                    TransactionModel.book_id == book_id,
                    TransactionModel.status == 'Completed'  # Match case with what's in the database
                ).first()
                
                if not transaction:
                    return jsonify({'error': 'You can only review books you have purchased'}), 403
                
                # Check if user has already reviewed this book
                existing_review = Review.query.filter_by(
                    user_id=current_user.id,
                    book_id=book_id
                ).first()
                
                if existing_review:
                    # Update existing review
                    existing_review.rating = rating
                    existing_review.title = title
                    existing_review.content = content
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Review updated successfully'})
                else:
                    # Create new review
                    new_review = Review(
                        user_id=current_user.id,
                        book_id=book_id,
                        rating=rating,
                        title=title,
                        content=content
                    )
                    db.session.add(new_review)
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Review submitted successfully'})
            
            # Continue with existing cart functionality
            book_id = data.get('book_id')
            if not book_id:
                return jsonify({'error': 'Missing book_id parameter'}), 400
                
            quantity = int(data.get('quantity', 1))
            book = Book.query.get(book_id)
            
            if not book:
                return jsonify({'error': f'Book with ID {book_id} not found'}), 404
                
            cart = session.get('cart', {})
            book_id_str = str(book_id)
            
            # Cart item removal
            if quantity <= -999 and book_id_str in cart:
                del cart[book_id_str]
            
            # Update existing item quantity
            elif book_id_str in cart:
                cart[book_id_str]['quantity'] += quantity
                
                # Remove if quantity becomes zero
                if cart[book_id_str]['quantity'] <= 0:
                    del cart[book_id_str]
            
            # Add new item to cart
            elif quantity > 0:
                cart[book_id_str] = {
                    'title': book.title,
                    'author': book.author,
                    'format': book.format,
                    'price': float(book.price),
                    'quantity': quantity,
                    'image_url': book.image_url
                }
            
            # Update cart summary
            session['cart_count'] = sum(item['quantity'] for item in cart.values())
            session['cart_total'] = sum(item['price'] * item['quantity'] for item in cart.values())
            
            session['cart'] = cart
            session.modified = True
            
            return jsonify({
                'success': True,
                'cart_count': session['cart_count'],
                'cart_total': session['cart_total'],
                'cart_items': cart
            })
        except Exception as e:
            # Log the error
            print(f"Error in POST request: {str(e)}")
            return jsonify({'error': 'An error occurred processing your request', 'details': str(e)}), 500
    
    try:
        # Book filtering system
        book_type = request.args.get('type', 'all')
        condition = request.args.get('condition', 'all')
        search = request.args.get('search', '')
        
        # Apply filters to database query
        query = Book.query.filter(Book.is_purchasable == True)
        if book_type != 'all':
            query = query.filter(Book.format == book_type)
        if condition != 'all':
            query = query.filter(Book.condition == condition)
        if search:
            query = query.filter(
                (Book.title.ilike(f'%{search}%')) |
                (Book.author.ilike(f'%{search}%')) |
                (Book.description.ilike(f'%{search}%'))
            )
        
        books = query.all()
        
        # Shopping cart initialization
        if 'cart' not in session:
            session['cart'] = {}
            session['cart_count'] = 0
            session['cart_total'] = 0

    
        
        return render_template('Book_Store_Main.html', books=books, cart=session['cart'], recommended_books=recommended_books)
    except Exception as e:
        # Log the error
        print(f"Error in main book listing: {str(e)}")
        # For HTML page request, render an error template
        return render_template('error.html', error=str(e)), 500
#----------WISH LIST----------

@main.route('/sync_wishlist_count', methods=['POST'])
def sync_wishlist_count():
    count = request.json.get('count', 0)
    session['wishlist_count'] = count
    return jsonify({'success': True})
# ----- USER PURCHASE HISTORY -----
@main.route('/Purchases')
@login_required
def purchases():
    """
    User purchase history page
    - Displays all past transactions for the current user
    """
    user = current_user
    
    # Get purchase statistics
    books_purchased = TransactionModel.query.filter_by(user_id=user.id).count()
    
    # Get detailed purchase history
    purchases = TransactionModel.query.filter_by(user_id=user.id).all()

    return render_template('My_Purchases.html',books_purchased=books_purchased,purchases=purchases)

# ----- CHECKOUT PROCESS -----
@main.route('/complete_purchase', methods=['GET', 'POST'])
@login_required
def complete_purchase():
    """
    Checkout page with address collection and payment processing
    - Validates shipping and payment information
    - Creates transaction records in database
    - Manages order completion process
    - Sends confirmation email and optional SMS
    """
    
    # Load environment variables
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # Prevent checkout with empty cart
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty. Please add items before proceeding.', 'error')
        return redirect(url_for('main.bookstore'))
    
    # Calculate order total
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Check if any physical books are in the cart
    has_physical_book = any(item["format"].lower() == "physical" for item in cart.values())
    
    # Process checkout submission
    if request.method == 'POST':
        # Get customer information (always required)
        first_name = request.form.get('firstName', '')
        last_name = request.form.get('lastName', '')
        email = request.form.get('email', current_user.email if hasattr(current_user, 'email') else '')
        phone = request.form.get('phone', '')
        
        # Validate basic customer information (always required)
        if not all([first_name, last_name, email]):
            flash('Please fill in all required customer information fields.', 'error')
            return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
        
        # Determine delivery option
        shipping_option = request.form.get('shipping_option', 'digital')
        shipping_option = request.form.get('shipping_option', 'digital')
        print(f"Selected shipping option: {shipping_option}")
        
        # Default to 'digital' for PDF-only orders
        if not has_physical_book:
            delivery_option = 'digital'
        elif shipping_option == 'pickup':
            delivery_option = 'store_pickup'
        else:
            delivery_option = 'delivery'
        
        # Only validate shipping address for actual delivery
        needs_shipping = has_physical_book and delivery_option == 'delivery'
        
        # Initialize shipping address fields
        address = address2 = city = province = zip_code = None
        
        # Only validate shipping fields if delivery is needed
        if needs_shipping:
            address = request.form.get('address')
            address2 = request.form.get('address2', '')  # Optional
            city = request.form.get('city')
            province = request.form.get('state')
            zip_code = request.form.get('zip')
            
            # Check if required shipping fields are missing
            if not all([address, city, province, zip_code]):
                flash('Please fill in all required shipping fields for delivery.', 'error')
                return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
        
        # Collect payment information
        card_number = request.form.get('cardNumber')
        card_name = request.form.get('cardName')
        exp_date = request.form.get('expDate')
        cvv = request.form.get('cvv')
        
        # Validate required payment fields
        if not all([card_number, card_name, exp_date, cvv]):
            flash('Please fill in all payment details.', 'error')
            return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
        
        # Validate credit card format
        card_number = card_number.replace(' ', '')
        if not re.match(CREDIT_CARD_PATTERN, card_number):
            flash('Invalid credit card number. Please enter a valid card with 13-19 digits.', 'error')
            return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
        
        # Validate expiration date format
        if not re.match(r'^(0[1-9]|1[0-2])\/([0-9]{2})$', exp_date):
            flash('Invalid expiration date. Please use MM/YY format.', 'error')
            return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
        
        # Validate CVV format
        if not re.match(r'^[0-9]{3,4}$', cvv):
            flash('Invalid CVV. Please enter 3-4 digits.', 'error')
            return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
            
        # Apply delivery fee if applicable
        order_total = total
        if needs_shipping:
            order_total += 50  
            
        try:
            # Create appropriate shipping address record based on delivery type
            shipping_address = None
            formatted_shipping_address = None
            delivery_date = None
            
            # Create ShippingAddress object with appropriate fields based on delivery_option
            shipping_address = ShippingAddress(
                user_id=current_user.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                delivery_type=delivery_option,
                created_at=datetime.utcnow()
            )
            
            # Only add shipping details if it's a delivery
            if delivery_option == 'delivery':
                shipping_address.street_address = address
                shipping_address.apartment = address2
                shipping_address.city = city
                shipping_address.province = province
                shipping_address.zip_code = zip_code
                
                # Format shipping address for email
                formatted_shipping_address = f"{address} {address2 if address2 else ''}, {city}, {province}, {zip_code}"
                
                # Estimate delivery date (5-7 business days from now)
                today = datetime.now()
                delivery_days = 7  # Default to standard delivery
                delivery_date = (today + timedelta(days=delivery_days)).strftime('%Y-%m-%d')
            elif delivery_option == 'store_pickup':
                # Store pickup option - use a placeholder for delivery location
                formatted_shipping_address = "Store Pickup"
                delivery_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')  # Available next day
            else:  # digital
                # Digital delivery
                formatted_shipping_address = "Digital Delivery"
                delivery_date = datetime.now().strftime('%Y-%m-%d')  # Available immediately
            
            # Add the shipping address to the session and flush to get ID
            db.session.add(shipping_address)
            db.session.flush()
            
            # Rest of the code remains the same...
            # (transaction handling, email sending, etc.)
            
            # Create transaction records for each book
            transactions = []
            order_items = []
            pdf_books = []
            
            for book_id, item in cart.items():
                # Get the book from the database to access all required fields
                book = Book.query.get(int(book_id))
                if not book:
                    flash(f"Book with ID {book_id} not found in database.", 'error')
                    continue
                
                transaction = TransactionModel(
                    user_id=current_user.id,
                    book_id=int(book_id),
                    shipping_address_id=shipping_address.id,
                    quantity=item['quantity'],
                    total_price=item['price'] * item['quantity'],
                    status='Pending',
                    purchase_date=datetime.utcnow(),
                    delivery_option=delivery_option
                )
                db.session.add(transaction)
                transactions.append(transaction)
                
                # Prepare order items for email with all required fields
                order_item = {
                    'title': book.title,
                    'author': book.author,
                    'image_url': book.image_url,
                    'price': book.price,
                    'quantity': item['quantity'],
                    'format': book.format,
                    'subtotal': book.price * item['quantity']
                }
                order_items.append(order_item)
                
                # If PDF, add to download links
                if book.format.lower() == 'pdf':
                    if book.pdf_url:
                        pdf_books.append({
                            'title': book.title,
                            'author': book.author,
                            'download_link': book.pdf_url,
                            'image_url': book.image_url
                        })
                    else:
                        # Handle the case where the pdf_url is not available
                        flash(f"PDF download link not available for {book.title}. Please contact support.", 'warning')
            
            # Commit all database changes
            db.session.commit()
            
            # Store non-sensitive transaction details in session
            session['last_transaction'] = {
                'date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'items': len(cart),
                'total': order_total,
                'shipping': {
                    'name': f"{first_name} {last_name}" if has_physical_book else None,
                    'address': formatted_shipping_address,
                    'delivery_option': delivery_option,
                    'delivery_date': delivery_date
                }
            }
            
            # Send purchase confirmation email using the imported function
            try:
                # Create a user-like object using the form data
                class UserData:
                    def __init__(self, email, name, phone=None):
                        self.email = email
                        self.name = name
                        self.phone = phone
                
                # Get customer name from form data
                customer_name = f"{first_name} {last_name}" if first_name and last_name else "Valued Customer"
                
                user_data = UserData(
                    email=email,
                    name=customer_name,
                    phone=phone
                )
                
                # Call the purchase confirmation function
                send_purchase_confirmation(
                    user=user_data,
                    order_items=order_items,
                    order_total=order_total,
                    shipping_address=formatted_shipping_address,
                    delivery_date=delivery_date,
                    pdf_books=pdf_books if pdf_books else None
                )
                
            except Exception as notification_error:
                import traceback
                traceback.print_exc()
            
            # Reset shopping cart
            session['cart'] = {}
            session['cart_count'] = 0
            session['cart_total'] = 0
            session.modified = True
            
            # If only PDFs, send the link via email, else proceed with shipping
            if not has_physical_book:
                flash('Your purchase was successful! You will receive an email with links to download your PDFs.', 'success')
            elif delivery_option == 'store_pickup':
                flash('Purchase successful! Your books will be ready for pickup tomorrow. Confirmation email sent.', 'success')
            else:
                flash('Purchase successful! Thank you for shopping with us. You will receive a confirmation email shortly.', 'success')
            
            return redirect(url_for('main.purchases'))
            
        except Exception as e:
            # Handle transaction errors
            db.session.rollback()
            flash(f'An error occurred while processing your purchase: {str(e)}', 'error')
            import traceback
            traceback.print_exc()
            return render_template('Complete_Purchase.html', cart=cart, total=total, has_physical_book=has_physical_book, user=current_user, google_maps_api_key=google_maps_api_key)
    
    # Display checkout page 
    return render_template('Complete_Purchase.html', cart=cart, total=total, user=current_user, google_maps_api_key=google_maps_api_key, has_physical_book=has_physical_book)

#-----USER PROFILE----------
@main.route('/user_profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    # Get current user's shipping info
    shipping_info = ShippingAddress.query.filter_by(user_id=current_user.id).first()
    
    # If no shipping info exists yet, create empty object for template
    if not shipping_info:
        shipping_info = ShippingAddress(
            user_id=current_user.id,
            phone="",
            street_address="",
            apartment="",
            city="",
            province="",
            zip_code=""
        )
    
    # Handle form submission
    if request.method == 'POST':
        # Update user information
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        
        # Update or create shipping information
        if not shipping_info.id:  # If it's a new record
            shipping_info = ShippingAddress(user_id=current_user.id)
            db.session.add(shipping_info)
        
        shipping_info.phone = request.form.get('phone')
        shipping_info.street_address = request.form.get('street_address')
        shipping_info.apartment = request.form.get('apartment')
        shipping_info.city = request.form.get('city')
        shipping_info.province = request.form.get('province')
        shipping_info.zip_code = request.form.get('zip_code')
        
        # Save changes to database
        db.session.commit()
        
        flash('Profile updated successfully!')
        return redirect(url_for('main.user_profile'))
    
    return render_template('user_profile.html', user=current_user, shipping_info=shipping_info)
# ----- SESSION MANAGEMENT -----
@main.route('/logout')
@login_required
def logout():
    """
    User logout functionality
    - Clears user session and redirects to login page
    """
    logout_user()
    return redirect(url_for('main.login'))