from enum import Enum
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager
import secrets
import string

class UserRole(Enum):
    ADMIN = 'admin'
    USER = 'user'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(256))
    
    # Foreign key to organization - with use_alter to handle circular dependency
    organization_id = db.Column(db.Integer, 
                               db.ForeignKey('organizations.id', use_alter=True, name='fk_user_org'), 
                               nullable=True)
    
    # User role and status
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Email verification
    email_verification_token = db.Column(db.String(100), nullable=True)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def generate_verification_token(self, length=32):
        """Generate a random verification token"""
        alphabet = string.ascii_letters + string.digits
        self.email_verification_token = ''.join(secrets.choice(alphabet) for _ in range(length))
        return self.email_verification_token
    
    def verify_email(self, token):
        """Verify email with token"""
        if self.email_verification_token == token:
            self.is_verified = True
            self.email_verification_token = None
            self.email_verified_at = datetime.now(timezone.utc)
            return True
        return False

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
