from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from app.models import db, User,Book, TransactionModel, ShippingAddress
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user,login_required, current_user,logout_user
from datetime import datetime
import re


main = Blueprint('main', __name__)

CREDIT_CARD_PATTERN = r'^[0-9]{13,19}$'

@main.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user exists in the database
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password): 
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('main.bookstore'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('Login.html')

@main.route('/signup', methods=['GET', 'POST'])
def signup():
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

@main.route('/bookstore', methods=['GET', 'POST'])
@login_required
def bookstore():
    """Display the bookstore page with book listings and handle cart additions."""
    # Get query parameters for filtering books
    book_type = request.args.get('type', 'all')
    condition = request.args.get('condition', 'all')
    search = request.args.get('search', '')

    # Filter purchasable books
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

    # Initialize cart session if not present
    if 'cart' not in session:
        session['cart'] = {}
        session['cart_count'] = 0
        session['cart_total'] = 0

    # Add to cart logic (POST request)
    if request.method == 'POST':
        book_id = request.form.get('book_id')
        quantity = int(request.form.get('quantity', 1))
        book = Book.query.get(book_id)

        if book:
            cart = session['cart']
            if book_id in cart:
                cart[book_id]['quantity'] += quantity
            else:
                cart[book_id] = {
                    'title': book.title,
                    'author': book.author,
                    'price': float(book.price),
                    'quantity': quantity,
                    'image_url': book.image_url
                }

            # Update cart count and total
            session['cart_count'] = sum(item['quantity'] for item in cart.values())
            session['cart_total'] = sum(item['price'] * item['quantity'] for item in cart.values())

            session.modified = True
            flash(f"{book.title} added to cart!", 'success')

    return render_template('Book_Store_Main.html', books=books, cart=session['cart'])

@main.route('/Purchases')
@login_required
def purchases():
    # Get the current user (Flask-Login provides current_user)
    user = current_user
    
    
    # Get the count of books purchased, on loan, and overdue
    books_purchased = TransactionModel.query.filter_by(user_id=user.id).count()
    
    # Get all the user's purchases and borrowings
    purchases = TransactionModel.query.filter_by(user_id=user.id).all()

    # Return the rendered template with context variables
    return render_template('My_Purchases.html',books_purchased=books_purchased,purchases=purchases)


@main.route('/complete_purchase', methods=['GET', 'POST'])
@login_required
def complete_purchase():
    # Check if the cart is empty
    cart = session.get('cart', {})
    if not cart:
        # If the cart is empty, flash an error message and redirect to the bookstore page
        flash('Your cart is empty. Please add items before proceeding.', 'error')
    
    # Calculate the total cost of the items in the cart
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Process the payment (POST request)
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        address2 = request.form.get('address2')
        city = request.form.get('city')
        province = request.form.get('state')
        zip_code = request.form.get('zip')
        
        # Credit card details
        card_number = request.form.get('cardNumber')
        card_name = request.form.get('cardName')
        exp_date = request.form.get('expDate')
        cvv = request.form.get('cvv')
        delivery_option = request.form.get('delivery')
        
        # Form validation
        if not all([first_name, last_name, email, phone, address, city, province, zip_code]):
            flash('Please fill in all required shipping fields.', 'error')
            return render_template('checkout.html', cart=cart, total=total)
        
        if not all([card_number, card_name, exp_date, cvv]):
            flash('Please fill in all payment details.', 'error')
            return render_template('checkout.html', cart=cart, total=total)
        
        # Credit card validation using regex
        card_number = card_number.replace(' ', '')  # Remove any spaces
        if not re.match(CREDIT_CARD_PATTERN, card_number):
            flash('Invalid credit card number. Please enter a valid card with 13-19 digits.', 'error')
            return render_template('checkout.html', cart=cart, total=total)
        
        # Simple expiration date validation (MM/YY format)
        if not re.match(r'^(0[1-9]|1[0-2])\/([0-9]{2})$', exp_date):
            flash('Invalid expiration date. Please use MM/YY format.', 'error')
            return render_template('checkout.html', cart=cart, total=total)
        
        # Simple CVV validation (3-4 digits)
        if not re.match(r'^[0-9]{3,4}$', cvv):
            flash('Invalid CVV. Please enter 3-4 digits.', 'error')
            return render_template('checkout.html', cart=cart, total=total)
            
        try:
            # Save shipping address to database
            shipping_address = ShippingAddress(
                user_id=current_user.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                street_address=address,
                apartment=address2,
                city=city,
                province=province,
                zip_code=zip_code,
                created_at=datetime.utcnow()
            )
            db.session.add(shipping_address)
            db.session.flush()  # Flush to get the shipping_address.id
            
            # Create transactions for each book in the cart
            for book_id, item in cart.items():
                transaction = TransactionModel(
                    user_id=current_user.id,
                    book_id=int(book_id),
                    shipping_address_id=shipping_address.id,
                    quantity=item['quantity'],
                    total_price=item['price'] * item['quantity'],
                    status='Completed',
                    purchase_date=datetime.utcnow()
                )
                db.session.add(transaction)
            
            # Commit all changes
            db.session.commit()
            
            # Store transaction details in session (for reference, not including sensitive data)
            session['last_transaction'] = {
                'date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'items': len(cart),
                'total': total,
                'shipping': {
                    'name': f"{first_name} {last_name}",
                    'address': address,
                    'city': city,
                    'province': province,
                    'zip': zip_code,
                    'delivery_option': delivery_option
                }
            }
            
            # Clear the cart
            session['cart'] = {}
            session['cart_count'] = 0
            session['cart_total'] = 0
            session.modified = True
            
            flash('Purchase successful! Thank you for shopping with us.', 'success')
            return redirect(url_for('main.purchases'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while processing your purchase: {str(e)}', 'error')
            return render_template('Complete_Purchase.html', cart=cart, total=total)
    
    # Render the checkout template with the cart and total
    return render_template('Complete_Purchase.html', cart=cart, total=total)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login')) 
