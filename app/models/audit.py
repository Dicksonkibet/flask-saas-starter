from app import db
from datetime import datetime, timezone
from enum import Enum

class AuditAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    SETTINGS_UPDATE = "settings_update"

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Who performed the action
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='audit_logs')
    
    # What was the action
    action = db.Column(db.Enum(AuditAction), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # 'user', 'organization', etc.
    resource_id = db.Column(db.Integer)
    
    # Additional details
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Organization context
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    organization = db.relationship('Organization')
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<AuditLog {self.action.value} on {self.resource_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action.value,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'created_at': self.created_at.isoformat()
        }

def log_audit(user_id, action, resource_type, resource_id=None, details=None, request=None):
    """Create audit log entry"""
    from flask import request as flask_request
    
    if request is None:
        request = flask_request
    
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None,
        organization_id=getattr(User.query.get(user_id), 'organization_id', None)
    )
    
    db.session.add(log)
    db.session.commit()
