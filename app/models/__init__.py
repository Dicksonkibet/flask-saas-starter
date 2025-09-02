# app/models/__init__.py
"""
Models initialization with proper relationship setup
"""

# Import all models
from app.models.user import User, UserRole
from app.models.organization import Organization, SubscriptionStatus

# Setup relationships after all models are imported
def setup_model_relationships():
    """Setup model relationships after all models are loaded"""
    from app import db
    
    # Setup User -> Organization relationship
    User.organization = db.relationship('Organization', 
                                      foreign_keys=[User.organization_id],
                                      backref=db.backref('users', lazy='dynamic'))
    
    # Setup Organization -> User (owner) relationship  
    Organization.owner = db.relationship('User',
                                       foreign_keys=[Organization.owner_id],
                                       backref=db.backref('owned_organizations', lazy='dynamic'))

# Call this function after app initialization
setup_model_relationships()