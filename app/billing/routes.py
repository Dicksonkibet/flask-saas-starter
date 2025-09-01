from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.utils.decorators import role_required
import stripe
import os

bp = Blueprint('billing', __name__)

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@bp.route('/subscription')
@login_required
def subscription():
    """Current subscription details"""
    subscription = current_user.organization.subscription
    if not subscription:
        # Create default free subscription
        subscription = Subscription(
            organization_id=current_user.organization_id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE
        )
        db.session.add(subscription)
        db.session.commit()
    
    return render_template('billing/subscription.html', subscription=subscription)

@bp.route('/upgrade/<plan_key>')
@login_required
@role_required('admin')
def upgrade_plan(plan_key):
    """Upgrade subscription plan"""
    if plan_key not in ['pro', 'enterprise']:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('billing.subscription'))
    
    subscription = current_user.organization.subscription
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{plan_key.title()} Plan',
                    },
                    'unit_amount': get_plan_price(plan_key) * 100,  # Stripe uses cents
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.subscription', _external=True),
            metadata={
                'organization_id': current_user.organization_id,
                'plan': plan_key
            }
        )
        
        return redirect(checkout_session.url)
        
    except stripe.error.StripeError as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('billing.subscription'))

@bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        handle_successful_payment(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_successful_payment(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_failed_payment(event['data']['object'])
    
    return jsonify({'status': 'success'})

def handle_successful_payment(session):
    """Handle successful payment"""
    org_id = session['metadata']['organization_id']
    plan_key = session['metadata']['plan']
    
    subscription = Subscription.query.filter_by(organization_id=org_id).first()
    if subscription:
        subscription.plan = SubscriptionPlan(plan_key)
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.stripe_customer_id = session['customer']
        subscription.stripe_subscription_id = session['subscription']
        db.session.commit()

def get_plan_price(plan_key):
    """Get plan price in dollars"""
    prices = {
        'pro': 29,
        'enterprise': 99
    }
    return prices.get(plan_key, 0)
