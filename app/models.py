from datetime import datetime
from flask_login import UserMixin
from app import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Fixed relationship definitions with explicit model class references
    purchases = db.relationship('TransactionModel', backref='user', lazy=True, cascade="all, delete-orphan")
    shipping_addresses = db.relationship('ShippingAddress', backref='user', lazy=True, cascade="all, delete-orphan")

    # Required by Flask-Login
    @property
    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    format = db.Column(db.Enum('PDF', 'Physical', name='book_format'), nullable=False)
    condition = db.Column(db.Enum('New', 'Second-hand', name='book_condition'), nullable=False)  
    is_lendable = db.Column(db.Boolean, default=False, nullable=False)
    is_purchasable = db.Column(db.Boolean, default=True, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    pdf_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Fixed relationship definitions
    purchases = db.relationship('TransactionModel', backref='book', lazy=True, cascade="all, delete-orphan")

# Renamed Transaction class to TransactionModel to avoid conflict with SQLAlchemy's Transaction
class TransactionModel(db.Model):
    __tablename__ = 'transaction'  

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete="CASCADE"), nullable=False)
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('shipping_address.id', ondelete="CASCADE"), nullable=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    total_price = db.Column(db.Float, nullable=False) 
    status = db.Column(db.String(50), default='Pending', nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    delivery_option = db.Column(db.Enum('delivery', 'store_pickup', 'digital', name='delivery_option'), nullable=False)  # New field


class ShippingAddress(db.Model):
    __tablename__ = 'shipping_address'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    street_address = db.Column(db.String(255), nullable=True)  # Nullable for store pickup and digital
    apartment = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)  # Nullable for store pickup and digital
    province = db.Column(db.String(100), nullable=True)  # Nullable for store pickup and digital
    zip_code = db.Column(db.String(20), nullable=True)  # Nullable for store pickup and digital
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    delivery_type = db.Column(db.Enum('delivery', 'store_pickup', 'digital', name='delivery_type'), nullable=False)  # New field
    
    transactions = db.relationship('TransactionModel', backref='shipping_address', lazy=True)

class Review(db.Model):
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # Rating from 1-5
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Define relationships
    user = db.relationship('User', backref=db.backref('reviews', lazy=True, cascade="all, delete-orphan"))
    book = db.relationship('Book', backref=db.backref('reviews', lazy=True, cascade="all, delete-orphan"))
    