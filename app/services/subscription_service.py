import stripe
from datetime import datetime, timezone, timedelta
from flask import current_app
from app import db
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.organization import Organization

class SubscriptionService:
    def __init__(self):
        self.stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY')
        if self.stripe_api_key:
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
                    status=SubscriptionStatus.ACTIVE if plan != SubscriptionPlan.FREE else SubscriptionStatus.ACTIVE
                )
                db.session.add(subscription)
            else:
                # Update existing subscription
                subscription.plan = plan
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.updated_at = datetime.now(timezone.utc)
            
            # Update organization subscription fields for backward compatibility
            organization.subscription_plan = plan_key
            organization.subscription_status = SubscriptionStatus.ACTIVE
            organization.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            return subscription
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating subscription: {e}")
            raise
    
    def create_stripe_checkout_session(self, organization, plan_key, success_url, cancel_url):
        """Create a Stripe checkout session"""
        try:
            if not self.stripe_api_key:
                raise Exception("Stripe API key not configured")
            
            plan = SubscriptionPlan(plan_key)
            price_id = self._get_stripe_price_id(plan)
            
            if not price_id:
                raise Exception(f"No Stripe price ID configured for plan: {plan_key}")
            
            checkout_session = stripe.checkout.Session.create(
                customer_email=organization.owner.email if organization.owner else None,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'organization_id': str(organization.id),
                    'plan': plan_key
                },
                subscription_data={
                    'metadata': {
                        'organization_id': str(organization.id),
                        'plan': plan_key
                    }
                }
            )
            
            return checkout_session
            
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe error creating checkout session: {e}")
            raise Exception(f"Payment processing error: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Error creating checkout session: {e}")
            raise
    
    def handle_webhook_event(self, event):
        """Handle Stripe webhook events"""
        try:
            event_type = event['type']
            current_app.logger.info(f"Processing webhook event: {event_type}")
            
            if event_type == 'checkout.session.completed':
                self._handle_checkout_completed(event['data']['object'])
            elif event_type == 'customer.subscription.updated':
                self._handle_subscription_updated(event['data']['object'])
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event['data']['object'])
            elif event_type == 'invoice.payment_succeeded':
                self._handle_payment_succeeded(event['data']['object'])
            elif event_type == 'invoice.payment_failed':
                self._handle_payment_failed(event['data']['object'])
            else:
                current_app.logger.info(f"Unhandled webhook event type: {event_type}")
                
        except Exception as e:
            current_app.logger.error(f"Error handling webhook event {event.get('type', 'unknown')}: {e}")
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
        try:
            organization_id = int(session['metadata']['organization_id'])
            plan_key = session['metadata']['plan']
            
            organization = Organization.query.get(organization_id)
            if not organization:
                current_app.logger.error(f"Organization {organization_id} not found for checkout completion")
                return
            
            # Create or update subscription
            subscription = self.create_subscription(organization, plan_key)
            
            # Update with Stripe data
            if subscription:
                subscription.stripe_customer_id = session.get('customer')
                subscription.stripe_subscription_id = session.get('subscription')
                db.session.commit()
                
            current_app.logger.info(f"Checkout completed for organization {organization_id}, plan {plan_key}")
            
        except Exception as e:
            current_app.logger.error(f"Error handling checkout completion: {e}")
            raise
    
    def _handle_subscription_updated(self, stripe_subscription):
        """Handle subscription updates"""
        try:
            organization_id = int(stripe_subscription['metadata'].get('organization_id'))
            if not organization_id:
                current_app.logger.error("No organization_id in subscription metadata")
                return
                
            subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
            
            if subscription_obj:
                subscription_obj.stripe_subscription_id = stripe_subscription['id']
                subscription_obj.current_period_start = datetime.fromtimestamp(
                    stripe_subscription['current_period_start'], timezone.utc
                )
                subscription_obj.current_period_end = datetime.fromtimestamp(
                    stripe_subscription['current_period_end'], timezone.utc
                )
                subscription_obj.status = SubscriptionStatus.ACTIVE
                subscription_obj.updated_at = datetime.now(timezone.utc)
                
                db.session.commit()
                current_app.logger.info(f"Updated subscription for organization {organization_id}")
            else:
                current_app.logger.error(f"Subscription not found for organization {organization_id}")
                
        except Exception as e:
            current_app.logger.error(f"Error handling subscription update: {e}")
            raise
    
    def _handle_subscription_deleted(self, stripe_subscription):
        """Handle subscription cancellation"""
        try:
            organization_id = int(stripe_subscription['metadata'].get('organization_id'))
            if not organization_id:
                current_app.logger.error("No organization_id in subscription metadata")
                return
                
            subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
            
            if subscription_obj:
                subscription_obj.status = SubscriptionStatus.CANCELLED
                subscription_obj.plan = SubscriptionPlan.FREE
                subscription_obj.updated_at = datetime.now(timezone.utc)
                
                # Update organization for backward compatibility
                organization = Organization.query.get(organization_id)
                if organization:
                    organization.subscription_plan = 'free'
                    organization.subscription_status = SubscriptionStatus.CANCELLED
                    organization.updated_at = datetime.now(timezone.utc)
                
                db.session.commit()
                current_app.logger.info(f"Cancelled subscription for organization {organization_id}")
            else:
                current_app.logger.error(f"Subscription not found for organization {organization_id}")
                
        except Exception as e:
            current_app.logger.error(f"Error handling subscription deletion: {e}")
            raise
    
    def _handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        try:
            subscription_id = invoice['subscription']
            if not subscription_id:
                return
                
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            organization_id = int(stripe_subscription['metadata'].get('organization_id'))
            
            if not organization_id:
                current_app.logger.error("No organization_id in subscription metadata")
                return
                
            subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
            
            if subscription_obj:
                subscription_obj.status = SubscriptionStatus.ACTIVE
                subscription_obj.updated_at = datetime.now(timezone.utc)
                
                # Update organization status too
                organization = Organization.query.get(organization_id)
                if organization:
                    organization.subscription_status = SubscriptionStatus.ACTIVE
                    organization.updated_at = datetime.now(timezone.utc)
                
                db.session.commit()
                current_app.logger.info(f"Payment succeeded for organization {organization_id}")
            else:
                current_app.logger.error(f"Subscription not found for organization {organization_id}")
                
        except Exception as e:
            current_app.logger.error(f"Error handling payment success: {e}")
            raise
    
    def _handle_payment_failed(self, invoice):
        """Handle failed payment"""
        try:
            subscription_id = invoice['subscription']
            if not subscription_id:
                return
                
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            organization_id = int(stripe_subscription['metadata'].get('organization_id'))
            
            if not organization_id:
                current_app.logger.error("No organization_id in subscription metadata")
                return
                
            subscription_obj = Subscription.query.filter_by(organization_id=organization_id).first()
            
            if subscription_obj and hasattr(SubscriptionStatus, 'PAST_DUE'):
                subscription_obj.status = SubscriptionStatus.PAST_DUE
                subscription_obj.updated_at = datetime.now(timezone.utc)
                
                # Update organization status too
                organization = Organization.query.get(organization_id)
                if organization:
                    organization.subscription_status = SubscriptionStatus.PAST_DUE
                    organization.updated_at = datetime.now(timezone.utc)
                
                db.session.commit()
                current_app.logger.info(f"Payment failed for organization {organization_id}")
            else:
                current_app.logger.warning(f"PAST_DUE status not available or subscription not found for org {organization_id}")
                
        except Exception as e:
            current_app.logger.error(f"Error handling payment failure: {e}")
            raise
    
    def get_organization_subscription(self, organization_id):
        """Get subscription for an organization"""
        try:
            subscription = Subscription.query.filter_by(organization_id=organization_id).first()
            
            if not subscription:
                # Create default free subscription
                organization = Organization.query.get(organization_id)
                if organization:
                    current_app.logger.info(f"Creating default subscription for organization {organization_id}")
                    subscription = self.create_subscription(organization, 'free')
                else:
                    current_app.logger.error(f"Organization {organization_id} not found")
                    return None
            
            return subscription
            
        except Exception as e:
            current_app.logger.error(f"Error getting organization subscription: {e}")
            raise
    
    def cancel_subscription(self, organization_id, at_period_end=True):
        """Cancel an organization's subscription"""
        try:
            subscription = Subscription.query.filter_by(organization_id=organization_id).first()
            
            if not subscription:
                current_app.logger.warning(f"No subscription found for organization {organization_id}")
                return False
            
            if subscription.stripe_subscription_id:
                try:
                    # Cancel with Stripe
                    if at_period_end:
                        stripe.Subscription.modify(
                            subscription.stripe_subscription_id,
                            cancel_at_period_end=True
                        )
                        subscription.cancel_at_period_end = True
                        current_app.logger.info(f"Scheduled cancellation at period end for org {organization_id}")
                    else:
                        stripe.Subscription.delete(subscription.stripe_subscription_id)
                        subscription.status = SubscriptionStatus.CANCELLED
                        subscription.plan = SubscriptionPlan.FREE
                        
                        # Update organization for backward compatibility
                        organization = Organization.query.get(organization_id)
                        if organization:
                            organization.subscription_plan = 'free'
                            organization.subscription_status = SubscriptionStatus.CANCELLED
                            organization.updated_at = datetime.now(timezone.utc)
                        
                        current_app.logger.info(f"Immediately cancelled subscription for org {organization_id}")
                    
                    subscription.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
                    return True
                    
                except stripe.error.StripeError as e:
                    current_app.logger.error(f"Stripe error canceling subscription: {e}")
                    return False
            else:
                # Local subscription only (no Stripe)
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.plan = SubscriptionPlan.FREE
                subscription.updated_at = datetime.now(timezone.utc)
                
                # Update organization
                organization = Organization.query.get(organization_id)
                if organization:
                    organization.subscription_plan = 'free'
                    organization.subscription_status = SubscriptionStatus.CANCELLED
                    organization.updated_at = datetime.now(timezone.utc)
                
                db.session.commit()
                current_app.logger.info(f"Cancelled local subscription for org {organization_id}")
                return True
        
        except Exception as e:
            current_app.logger.error(f"Error canceling subscription for org {organization_id}: {e}")
            db.session.rollback()
            return False
    
    def upgrade_subscription(self, organization_id, new_plan_key):
        """Upgrade a subscription to a new plan"""
        try:
            subscription = self.get_organization_subscription(organization_id)
            if not subscription:
                return None
            
            old_plan = subscription.plan.value if subscription.plan else 'free'
            subscription.upgrade_plan(new_plan_key)
            subscription.updated_at = datetime.now(timezone.utc)
            
            # Update organization
            organization = Organization.query.get(organization_id)
            if organization:
                organization.subscription_plan = new_plan_key
                organization.subscription_status = SubscriptionStatus.ACTIVE
                organization.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            current_app.logger.info(f"Upgraded org {organization_id} from {old_plan} to {new_plan_key}")
            return subscription
            
        except Exception as e:
            current_app.logger.error(f"Error upgrading subscription: {e}")
            db.session.rollback()
            raise
    
    def get_subscription_analytics(self, organization_id):
        """Get subscription analytics data"""
        try:
            subscription = self.get_organization_subscription(organization_id)
            if not subscription:
                return None
            
            analytics = {
                'current_plan': subscription.plan.value,
                'status': subscription.status.value,
                'features': subscription.plan_features,
                'price': subscription.plan_price,
                'is_active': subscription.is_active,
                'is_trialing': subscription.is_trialing,
                'trial_days_remaining': subscription.days_remaining_in_trial,
                'created_at': subscription.created_at.isoformat(),
                'updated_at': subscription.updated_at.isoformat()
            }
            
            if subscription.current_period_end:
                analytics['current_period_end'] = subscription.current_period_end.isoformat()
            
            if subscription.trial_end:
                analytics['trial_end'] = subscription.trial_end.isoformat()
            
            return analytics
            
        except Exception as e:
            current_app.logger.error(f"Error getting subscription analytics: {e}")
            return None