from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

# Initialize Flask-Login
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configure app with environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)

    # Set the login view for Flask-Login (this will redirect unauthorized users to the login page)
    login_manager.login_view = 'main.login'  # Ensure this matches the name of your login route

    # Import the models and routes after app initialization
    from app.models import User
    from app.routes import main
    from .admin import admin
    app.register_blueprint(main)
    app.register_blueprint(admin, url_prefix='/') 

    # Initialize the user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
