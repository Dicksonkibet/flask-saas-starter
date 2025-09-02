import enum
from datetime import datetime, timezone, timedelta
from app import db

class SubscriptionStatus(enum.Enum):
    ACTIVE = 'ACTIVE'        # Match database values
    TRIAL = 'TRIAL'          
    EXPIRED = 'EXPIRED'      
    CANCELLED = 'CANCELLED'  
    PAST_DUE = 'PAST_DUE'   # If you're using this

class SubscriptionPlan(enum.Enum):
    FREE = 'free'
    PRO = 'pro'
    ENTERPRISE = 'enterprise'

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), unique=True, nullable=False)
    plan = db.Column(db.Enum(SubscriptionPlan), default=SubscriptionPlan.FREE, nullable=False)
    status = db.Column(db.Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    
    # Stripe fields
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    stripe_price_id = db.Column(db.String(255), nullable=True)

    # Add these fields to your Subscription model
    paypal_order_id = db.Column(db.String(255), nullable=True)
    paypal_payment_captured = db.Column(db.Boolean, default=False)
    paypal_capture_id = db.Column(db.String(255), nullable=True)
        
    # Billing information
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    
    # Trial information
    trial_start = db.Column(db.DateTime, nullable=True)
    trial_end = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    organization = db.relationship('Organization', backref=db.backref('subscription', uselist=False))
    
    def __repr__(self):
        return f'<Subscription {self.organization.name} - {self.plan.value}>'
    
    @property
    def is_active(self):
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
    
    @property
    def is_trialing(self):
        return self.status == SubscriptionStatus.TRIAL
    
    @property
    def is_past_due(self):
        return self.status == SubscriptionStatus.PAST_DUE if hasattr(SubscriptionStatus, 'PAST_DUE') else False
    
    @property
    def days_remaining_in_trial(self):
        if not self.is_trialing or not self.trial_end:
            return 0
        remaining = (self.trial_end - datetime.now(timezone.utc)).days
        return max(0, remaining)
    
    @property
    def plan_features(self):
        features = {
            SubscriptionPlan.FREE: {
                'users': 5,
                'storage': '1GB',
                'support': 'Basic',
                'analytics': False,
                'api_access': False,
                'custom_domain': False
            },
            SubscriptionPlan.PRO: {
                'users': 25,
                'storage': '10GB',
                'support': 'Priority',
                'analytics': True,
                'api_access': True,
                'custom_domain': True
            },
            SubscriptionPlan.ENTERPRISE: {
                'users': 'Unlimited',
                'storage': '100GB',
                'support': '24/7 Premium',
                'analytics': True,
                'api_access': True,
                'custom_domain': True
            }
        }
        return features.get(self.plan, {})
    
    @property
    def plan_price(self):
        prices = {
            SubscriptionPlan.FREE: 0,
            SubscriptionPlan.PRO: 29,
            SubscriptionPlan.ENTERPRISE: 99
        }
        return prices.get(self.plan, 0)
    
    def start_trial(self, days=14):
        """Start a free trial for the organization"""
        self.plan = SubscriptionPlan.PRO
        self.status = SubscriptionStatus.TRIAL
        self.trial_start = datetime.now(timezone.utc)
        self.trial_end = datetime.now(timezone.utc) + timedelta(days=days)
    
    def upgrade_plan(self, new_plan):
        """Upgrade to a new plan"""
        if not isinstance(new_plan, SubscriptionPlan):
            new_plan = SubscriptionPlan(new_plan)
        
        self.plan = new_plan
        if self.status == SubscriptionStatus.TRIAL:
            self.status = SubscriptionStatus.ACTIVE
            self.trial_end = None
    
    def cancel(self, at_period_end=True):
        """Cancel the subscription"""
        self.cancel_at_period_end = at_period_end
        if not at_period_end:
            self.status = SubscriptionStatus.CANCELLED
    
    def renew(self):
        """Renew the subscription"""
        self.status = SubscriptionStatus.ACTIVE
        self.cancel_at_period_end = False