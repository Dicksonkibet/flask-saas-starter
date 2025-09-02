
# app/models/organization.py - SIMPLE VERSION  
from app import db
from datetime import datetime, timezone
from enum import Enum

class SubscriptionStatus(Enum):
    ACTIVE = "ACTIVE"     # Changed from "active" to "ACTIVE"
    TRIAL = "TRIAL"       # Changed from "trial" to "TRIAL"  
    EXPIRED = "EXPIRED"   # Changed from "expired" to "EXPIRED"
    CANCELLED = "CANCELLED" # Changed from "cancelled" to "CANCELLED"

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Subscription info
    subscription_plan = db.Column(db.String(50), default='free')
    subscription_status = db.Column(db.Enum(SubscriptionStatus),
                                   default=SubscriptionStatus.TRIAL)
                                   
    subscription_expires_at = db.Column(db.DateTime)
    
    # Settings
    settings = db.Column(db.JSON, default=dict)
    logo_url = db.Column(db.String(255))
    website = db.Column(db.String(255))
    
    # Owner relationship - with use_alter and named constraint
    owner_id = db.Column(db.Integer, 
                        db.ForeignKey('users.id', use_alter=True, name='fk_org_owner'), 
                        nullable=True)
    
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
            'subscription_status': self.subscription_status.value if self.subscription_status else 'trial',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }