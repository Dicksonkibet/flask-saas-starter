import requests
import json
from flask import current_app
from app.models.organization import Organization
import hmac
import hashlib

class WebhookManager:
    """Manage outgoing webhooks"""
    
    @staticmethod
    def send_webhook(organization_id, event_type, data, webhook_url=None):
        """Send webhook to organization's configured endpoint"""
        try:
            org = Organization.query.get(organization_id)
            if not org:
                return False
            
            # Get webhook URL from organization settings
            if not webhook_url:
                webhook_url = org.settings.get('webhook_url')
            
            if not webhook_url:
                return False
            
            # Prepare payload
            payload = {
                'event': event_type,
                'data': data,
                'organization_id': organization_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Create signature for security
            webhook_secret = org.settings.get('webhook_secret', '')
            signature = None
            if webhook_secret:
                signature = hmac.new(
                    webhook_secret.encode('utf-8'),
                    json.dumps(payload).encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
            
            # Send webhook
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Flask-SaaS-Starter/1.0'
            }
            
            if signature:
                headers['X-Webhook-Signature'] = f'sha256={signature}'
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            return response.status_code < 400
            
        except Exception as e:
            current_app.logger.error(f'Webhook failed: {str(e)}')
            return False
    
    @staticmethod
    def trigger_user_event(user, event_type):
        """Trigger webhook for user events"""
        return WebhookManager.send_webhook(
            user.organization_id,
            f'user.{event_type}',
            user.to_dict()
        )