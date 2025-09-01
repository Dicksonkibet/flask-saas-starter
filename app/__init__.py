from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()

def create_app(config_class='config.DevelopmentConfig'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Create database tables
    with app.app_context():
        if app.config.get('DEBUG'):
            try:
                db.drop_all()
            except Exception as e:
                print(f"Note during table cleanup: {e}")
        
        db.create_all()
        print("Database setup complete!")
    
    return app