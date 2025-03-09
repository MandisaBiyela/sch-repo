from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed password
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    purchases = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    borrowings = db.relationship('Borrowing', backref='user', lazy=True, cascade="all, delete-orphan")

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    format = db.Column(db.Enum('PDF', 'Physical', name='book_format'), nullable=False)  # Enforce valid values
    condition = db.Column(db.Enum('New', 'Second-hand', name='book_condition'), nullable=False)  
    is_lendable = db.Column(db.Boolean, default=False, nullable=False)  # Can be borrowed?
    is_purchasable = db.Column(db.Boolean, default=True, nullable=False)  # Can be bought?
    image_url = db.Column(db.String(500), nullable=True)  # Store book image URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    purchases = db.relationship('Transaction', backref='book', lazy=True, cascade="all, delete-orphan")
    borrowings = db.relationship('Borrowing', backref='book', lazy=True, cascade="all, delete-orphan")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete="CASCADE"), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Borrowing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete="CASCADE"), nullable=False)
    borrowed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    returned_at = db.Column(db.DateTime, nullable=True)  # If None, book is still borrowed
