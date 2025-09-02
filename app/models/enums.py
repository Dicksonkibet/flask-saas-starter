from enum import Enum

class SubscriptionStatus(Enum):
    ACTIVE = 'ACTIVE'
    TRIAL = 'TRIAL'          
    EXPIRED = 'EXPIRED'      
    CANCELLED = 'CANCELLED'

class SubscriptionPlan(Enum):
    FREE = 'free'
    PRO = 'pro'
    ENTERPRISE = 'enterprise'