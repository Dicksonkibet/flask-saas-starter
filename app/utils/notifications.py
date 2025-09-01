
from flask import current_app
from app import db
from app.models.user import User
from app.utils.email import send_email
from datetime import datetime, timezone
from enum import Enum

class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Recipient
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='notifications')
    
    # Content
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(NotificationType), default=NotificationType.INFO)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    is_email_sent = db.Column(db.Boolean, default=False)
    
    # Metadata
    action_url = db.Column(db.String(255))  # Optional URL for action
    metadata = db.Column(db.JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime)
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type.value,
            'is_read': self.is_read,
            'action_url': self.action_url,
            'created_at': self.created_at.isoformat()
        }

class NotificationManager:
    """Manage application notifications"""
    
    @staticmethod
    def create_notification(user_id, title, message, notification_type=NotificationType.INFO, 
                          action_url=None, send_email=False, metadata=None):
        """Create a new notification"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            action_url=action_url,
            metadata=metadata or {}
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Send email if requested
        if send_email:
            user = User.query.get(user_id)
            if user and user.organization.settings.get('email_notifications', True):
                NotificationManager.send_notification_email(notification)
        
        return notification
    
    @staticmethod
    def send_notification_email(notification):
        """Send notification via email"""
        try:
            send_email(
                subject=notification.title,
                recipients=[notification.user.email],
                text_body=notification.message,
                html_body=render_template('emails/notification.html', 
                                        notification=notification)
            )
            notification.is_email_sent = True
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f'Failed to send notification email: {str(e)}')
    
    @staticmethod
    def get_user_notifications(user_id, unread_only=False, limit=50):
        """Get notifications for a user"""
        query = Notification.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def mark_all_read(user_id):
        """Mark all notifications as read for a user"""
        Notification.query.filter_by(user_id=user_id, is_read=False).update({
            'is_read': True,
            'read_at': datetime.now(timezone.utc)
        })
        db.session.commit()