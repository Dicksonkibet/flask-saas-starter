import stripe
from datetime import datetime, timezone, timedelta
from flask import current_app
from app import db
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.organization import Organization

class SubscriptionService:
    def __init__(self):
        self.stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY')
        stripe.api_key = self.stripe_api_key
    
    def create_subscription(self, organization, plan_key, payment_method_id=None):
        """Create a new subscription for an organization"""
        try:
            plan = SubscriptionPlan(plan_key)
            
            # Check if organization already has a subscription
            subscription = Subscription.query.filter_by(organization_id=organization.id).first()
            
            if not subscription:
                # Create new subscription
                subscription = Subscription(
                    organization_id=organization.id,
                    plan=plan,
                    status=SubscriptionStatus.ACTIVE
                )
                db.session.add(subscription)
            else:
                # Update existing subscription
                subscription.plan = plan
                subscription.status = SubscriptionStatus.ACTIVE
            
            # Update organization subscription fields for backward compatibility
            organization.subscription_plan = plan_key
            organization.subscription_status = SubscriptionStatus.ACTIVE
            
            db.session.commit()
            return subscription
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating subscription: {e}")
            raise
    
    def create_stripe_checkout_session(self, organization, plan_key, success_url, cancel_url):
        """Create a Stripe checkout session"""
        try:
            plan = SubscriptionPlan(plan_key)
            price_id = self._get_stripe_price_id(plan)
            
            checkout_session = stripe.checkout.Session.create(
                customer_email=organization.owner.email,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'organization_id': organization.id,
                    'plan': plan_key
                },
                subscription_data={
                    'metadata': {
                        'organization_id': organization.id,
                        'plan': plan_key
                    }
                }
            )
            
            return checkout_session
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error creating checkout session: {e}")
            raise
    
    def handle_webhook_event(self, event):
        """Handle Stripe webhook events"""
        try:
            if event['type'] == 'checkout.session.completed':
                self._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'customer.subscription.updated':
                self._handle_subscription_updated(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event['data']['object'])
            elif event['type'] == 'invoice.payment_succeeded':
                self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                self._handle_payment_failed(event['data']['object'])
                
        except Exception as e:
            current_app.logger.error(f"Error handling webhook event: {e}")
            raise
    
    def _get_stripe_price_id(self, plan):
        """Get Stripe price ID for a plan"""
        price_ids = {
            SubscriptionPlan.PRO: current_app.config.get('STRIPE_PRO_PRICE_ID'),
            SubscriptionPlan.ENTERPRISE: current_app.config.get('STRIPE_ENTERPRISE_PRICE_ID')
        }
        return price_ids.get(plan)
    
    def _handle_checkout_completed(self, session):
        """Handle completed checkout session"""
        organization_id = session['metadata']['organization_id']
        plan_key = session['metadata']['plan']
        
        organization = Organization.query.get(organization_id)
        if organization:
            self.create_subscription(organization, plan_key)
    
    def _handle_subscription_updated(self, subscription):
        """Handle subscription updates"""
        organization_id = subscription['metadata']['organization_id']
        subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
        
        if subscription_obj:
            subscription_obj.stripe_subscription_id = subscription['id']
            subscription_obj.current_period_start = datetime.fromtimestamp(subscription['current_period_start'], timezone.utc)
            subscription_obj.current_period_end = datetime.fromtimestamp(subscription['current_period_end'], timezone.utc)
            subscription_obj.status = SubscriptionStatus.ACTIVE
            
            db.session.commit()
    
    def _handle_subscription_deleted(self, subscription):
        """Handle subscription cancellation"""
        organization_id = subscription['metadata']['organization_id']
        subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
        
        if subscription_obj:
            subscription_obj.status = SubscriptionStatus.CANCELED
            subscription_obj.plan = SubscriptionPlan.FREE
            
            # Update organization for backward compatibility
            organization = Organization.query.get(organization_id)
            if organization:
                organization.subscription_plan = 'free'
                organization.subscription_status = SubscriptionStatus.CANCELED
            
            db.session.commit()
    
    def _handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        subscription_id = invoice['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        organization_id = subscription['metadata']['organization_id']
        subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
        
        if subscription_obj:
            subscription_obj.status = SubscriptionStatus.ACTIVE
            db.session.commit()
    
    def _handle_payment_failed(self, invoice):
        """Handle failed payment"""
        subscription_id = invoice['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        organization_id = subscription['metadata']['organization_id']
        subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
        
        if subscription_obj:
            subscription_obj.status = SubscriptionStatus.PAST_DUE
            db.session.commit()
    
    def get_organization_subscription(self, organization_id):
        """Get subscription for an organization"""
        subscription = Subscription.query.filter_by(organization_id=organization_id).first()
        
        if not subscription:
            # Create default free subscription
            organization = Organization.query.get(organization_id)
            if organization:
                subscription = self.create_subscription(organization, 'free')
        
        return subscription
    
    def cancel_subscription(self, organization_id, at_period_end=True):
        """Cancel an organization's subscription"""
        subscription = Subscription.query.filter_by(organization_id=organization_id).first()
        
        if subscription and subscription.stripe_subscription_id:
            try:
                # Cancel with Stripe
                stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                
                if at_period_end:
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
                    subscription.cancel_at_period_end = True
                else:
                    stripe.Subscription.delete(subscription.stripe_subscription_id)
                    subscription.status = SubscriptionStatus.CANCELED
                    subscription.plan = SubscriptionPlan.FREE
                    
                    # Update organization for backward compatibility
                    organization = Organization.query.get(organization_id)
                    if organization:
                        organization.subscription_plan = 'free'
                        organization.subscription_status = SubscriptionStatus.CANCELED
                
                db.session.commit()
                return True
                
            except stripe.error.StripeError as e:
                current_app.logger.error(f"Stripe error canceling subscription: {e}")
                return False
        
        return False