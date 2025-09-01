from app import db
from datetime import datetime, timezone
from enum import Enum

class SubscriptionPlan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Organization relationship
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), unique=True, nullable=False)
    organization = db.relationship('Organization', backref=db.backref('subscription', uselist=False))
    
    # Subscription details
    plan = db.Column(db.Enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    status = db.Column(db.Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    
    # Billing
    stripe_customer_id = db.Column(db.String(255))
    stripe_subscription_id = db.Column(db.String(255))
    
    # Dates
    trial_start = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    trial_end = db.Column(db.DateTime)
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Usage tracking
    user_limit = db.Column(db.Integer, default=5)  # Based on plan
    feature_flags = db.Column(db.JSON, default=dict)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    
    def is_active(self):
        """Check if subscription is active"""
        return self.status == SubscriptionStatus.ACTIVE
    
    def is_trial(self):
        """Check if in trial period"""
        return self.status == SubscriptionStatus.TRIAL
    
    def days_until_expiry(self):
        """Get days until subscription expires"""
        if self.current_period_end:
            return (self.current_period_end - datetime.now(timezone.utc)).days
        return None
    
    def can_access_feature(self, feature_name):
        """Check if subscription allows access to feature"""
        plan_features = {
            SubscriptionPlan.FREE: ['basic_dashboard', 'user_management'],
            SubscriptionPlan.PRO: ['basic_dashboard', 'user_management', 'advanced_analytics', 'api_access'],
            SubscriptionPlan.ENTERPRISE: ['all_features']
        }
        
        if self.plan == SubscriptionPlan.ENTERPRISE:
            return True
        
        return feature_name in plan_features.get(self.plan, [])
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan': self.plan.value,
            'status': self.status.value,
            'user_limit': self.user_limit,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'days_until_expiry': self.days_until_expiry()
        }
