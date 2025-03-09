from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user exists in the database
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # If the user exists and password is correct, log them in
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('main.bookstore'))  # Redirect to bookstore or main page
        else:
            # If no user found or password doesn't match
            flash('Invalid email or password. Please try again.', 'error')

    # Render login template
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

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('main.signup'))

        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create a new user
        new_user = User(first_name=first_name, last_name=last_name, email=email, password=hashed_password)

        # Add user to database
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('main.login'))

    return render_template('Signup.html')

@main.route('/Bookstore')
def bookstore():
    flash("This is a success message!", "success")
    return render_template('Book_Store_Main.html')

@main.route('/Purchases')
def purchases():
    return render_template('My_Purchases.html')

@main.route('/Complete_Purchase')
def complete_purchase():
    return render_template('Complete_Purchase.html')
