from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime, timezone
from app import db, limiter
from app.models.user import User, UserRole
from app.models.organization import Organization, SubscriptionStatus
from app.auth.forms import LoginForm, RegisterForm, ResetPasswordForm
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.decorators import anonymous_required


from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.utils.decorators import role_required
import stripe
import os


bp = Blueprint('main', __name__)

# Main/Home routes
@bp.route('/')
def index():
    return render_template('index.html')

# Auth routes (moved from auth blueprint)
@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@anonymous_required
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated.', 'error')
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.dashboard')
            
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_page)
        
        flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
@anonymous_required
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            # Create organization first
            org = Organization(
                name=f"{form.first_name.data}'s Organization",
                slug=f"{form.username.data.lower()}-org",
                subscription_plan='free',
                subscription_status=SubscriptionStatus.TRIAL
            )
            db.session.add(org)
            db.session.flush()  # Get the organization ID without committing
            
            # Create user
            user = User(
                username=form.username.data.lower(),
                email=form.email.data.lower(),
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                role=UserRole.ADMIN,
                organization_id=org.id
            )
            user.set_password(form.password.data)
            
            # Generate verification token
            token = user.generate_verification_token()
            
            db.session.add(user)
            db.session.flush()  # Get the user ID without committing
            
            # Set organization owner
            org.owner_id = user.id
            
            # Commit everything together
            db.session.commit()
            
            # Send verification email
            send_verification_email(user, token)
            
            flash('Registration successful! Please check your email to verify your account.', 'success')
            return redirect(url_for('main.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            # Log the error for debugging
            print(f"Registration error: {e}")
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if user:
        user.is_verified = True
        user.email_verification_token = None
        db.session.commit()
        flash('Email verified successfully!', 'success')
    else:
        flash('Invalid or expired verification token.', 'error')
    
    return redirect(url_for('main.login'))

# Dashboard routes (moved from dashboard blueprint)
@bp.route('/dashboard')
@login_required
def dashboard():
    # Get stats for the dashboard
    if current_user.organization_id:
        org_users = User.query.filter_by(organization_id=current_user.organization_id).all()
        stats = {
            'total_users': len(org_users),
            'active_users': sum(1 for user in org_users if user.is_active),
            'verified_users': sum(1 for user in org_users if user.is_verified),
            'admin_users': sum(1 for user in org_users if user.role == UserRole.ADMIN)
        }
        
        # Get recent users (last 5)
        recent_users = User.query.filter_by(organization_id=current_user.organization_id)\
                                 .order_by(User.created_at.desc())\
                                 .limit(5).all()
    else:
        stats = {'total_users': 0, 'active_users': 0, 'verified_users': 0, 'admin_users': 0}
        recent_users = []
    
    return render_template('dashboard/index.html', stats=stats, recent_users=recent_users)

# Admin route (THIS WAS MISSING - ADDED TO FIX THE ERROR)
@bp.route('/admin')
@login_required
def admin():
    """Admin dashboard page"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get organization statistics
    if current_user.organization_id:
        org_users = User.query.filter_by(organization_id=current_user.organization_id).all()
        stats = {
            'total_users': len(org_users),
            'active_users': sum(1 for user in org_users if user.is_active),
            'verified_users': sum(1 for user in org_users if user.is_verified),
            'admin_users': sum(1 for user in org_users if user.role == UserRole.ADMIN)
        }
    else:
        stats = {
            'total_users': 0,
            'active_users': 0,
            'verified_users': 0,
            'admin_users': 0
        }
    
    return render_template('dashboard/admin.html', stats=stats)

# Users management route
@bp.route('/users')
@login_required
def users():
    """Users management page"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get users from the same organization
    users = User.query.filter_by(organization_id=current_user.organization_id).all()
    return render_template('dashboard/users.html', users=users)

# Settings route
@bp.route('/settings')
@login_required
def settings():
    """Organization settings page"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return render_template('dashboard/settings.html')

# Profile route
@bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('dashboard/profile.html')

# API stats endpoint (for dashboard)
@bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard statistics"""
    if current_user.organization_id:
        org_users = User.query.filter_by(organization_id=current_user.organization_id).all()
        stats = {
            'total_users': len(org_users),
            'active_users': sum(1 for user in org_users if user.is_active),
            'verified_users': sum(1 for user in org_users if user.is_verified),
            'admin_users': sum(1 for user in org_users if user.role == UserRole.ADMIN)
        }
    else:
        stats = {
            'total_users': 0,
            'active_users': 0,
            'verified_users': 0,
            'admin_users': 0
        }
    
    return jsonify(stats)

# API routes (moved from api blueprint)
@bp.route('/api/v1/health')
def api_health():
    return jsonify({'status': 'healthy'})

# Pricing route (to fix the earlier error)
# @bp.route('/pricing')
# def pricing():
#     return render_template('pricing.html')

# Add more routes as needed

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
    
    return render_template('pricing.html', subscription=subscription)

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
