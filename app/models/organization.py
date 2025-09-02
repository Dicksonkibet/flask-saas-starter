from app import db
from datetime import datetime, timezone
from enum import Enum

class SubscriptionStatus(Enum):
    ACTIVE = "ACTIVE"      # Changed to uppercase to match database
    TRIAL = "TRIAL"        # Changed to uppercase to match database
    EXPIRED = "EXPIRED"    # Changed to uppercase to match database
    CANCELLED = "CANCELLED"  # Changed to uppercase to match database

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Subscription info
    subscription_plan = db.Column(db.String(50), default='free')
    # FIX: Add native_enum=False to force SQLAlchemy to use string values
    subscription_status = db.Column(db.Enum(SubscriptionStatus, native_enum=False),
                                   default=SubscriptionStatus.TRIAL)
    subscription_expires_at = db.Column(db.DateTime)
    
    # Settings
    settings = db.Column(db.JSON, default=dict)
    logo_url = db.Column(db.String(255))
    website = db.Column(db.String(255))
    
    # Owner relationship - this creates the circular reference with User
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # FIXED: Define relationships with proper foreign_keys to avoid ambiguity
    users = db.relationship('User',
                           foreign_keys='User.organization_id',
                           back_populates='organization',
                           lazy='dynamic')
    
    owner = db.relationship('User',
                           foreign_keys=[owner_id],
                           back_populates='owned_organizations')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Organization {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'subscription_plan': self.subscription_plan,
            'subscription_status': self.subscription_status.value if isinstance(self.subscription_status, SubscriptionStatus) else str(self.subscription_status),
            'created_at': self.created_at.isoformat()
        }
    
    def set_subscription_status(self, status):
        """Safely set subscription status"""
        if isinstance(status, str):
            self.subscription_status = SubscriptionStatus(status)
        elif isinstance(status, SubscriptionStatus):
            self.subscription_status = status
        else:
            raise ValueError(f"Invalid subscription status: {status}")