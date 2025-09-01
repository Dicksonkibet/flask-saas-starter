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
from app.models.subscription import Subscription, SubscriptionPlan
from app.utils.decorators import role_required
import stripe
import os
import re

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
        # Clean and validate email
        email = form.email.data.lower().strip()
        password = form.password.data
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Check if account is active
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'error')
                return render_template('auth/login.html', form=form)
            
            # Log the user in
            login_user(user, remember=form.remember_me.data)
            
            # Update last login timestamp
            user.last_login = datetime.now(timezone.utc)
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error updating last login: {e}")
                # Continue with login even if timestamp update fails
            
            # Handle redirect after successful login
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                # Default redirect based on user role
                if user.role == UserRole.ADMIN:
                    next_page = url_for('main.dashboard')
                else:
                    next_page = url_for('main.dashboard')
            
            # Success message with user's name
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_page)
        
        # Invalid credentials
        flash('Invalid email or password. Please try again.', 'error')
    
    # If form validation failed, flash field errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field.title()}: {error}', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
@anonymous_required
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            # Clean form data
            username = form.username.data.lower().strip()
            email = form.email.data.lower().strip()
            first_name = form.first_name.data.strip()
            last_name = form.last_name.data.strip()
            
            # Additional validation
            if not username or not email or not first_name or not last_name:
                flash('All fields are required.', 'error')
                return render_template('auth/register.html', form=form)
            
            # Validate username format (alphanumeric, hyphens, underscores only)
            if not re.match(r'^[a-zA-Z0-9_-]+$', username):
                flash('Username can only contain letters, numbers, hyphens, and underscores.', 'error')
                return render_template('auth/register.html', form=form)
            
            # Check minimum username length
            if len(username) < 3:
                flash('Username must be at least 3 characters long.', 'error')
                return render_template('auth/register.html', form=form)
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('An account with this email already exists.', 'error')
                return render_template('auth/register.html', form=form)
            
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                flash('This username is already taken.', 'error')
                return render_template('auth/register.html', form=form)
            
            # Create organization first with better slug generation
            org_slug = f"{username}-org"
            counter = 1
            while Organization.query.filter_by(slug=org_slug).first():
                org_slug = f"{username}-org-{counter}"
                counter += 1
            
            org = Organization(
                name=f"{first_name}'s Organization",
                slug=org_slug,
                subscription_plan='free',
                subscription_status=SubscriptionStatus.TRIAL
            )
            db.session.add(org)
            db.session.flush()  # Get the organization ID without committing
            
            # Create user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.ADMIN,
                organization_id=org.id,
                is_active=True,
                is_verified=False  # Will be set to True after email verification
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
            try:
                send_verification_email(user, token)
                flash('Registration successful! Please check your email to verify your account before logging in.', 'success')
            except Exception as e:
                print(f"Error sending verification email: {e}")
                flash('Registration successful! However, we could not send the verification email. Please contact support.', 'warning')
            
            return redirect(url_for('main.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            print(f"Registration error: {e}")
            # Log the full error for debugging
            import traceback
            print(traceback.format_exc())
    
    # If form validation failed, flash field errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field.replace("_", " ").title()}: {error}', 'error')
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    user_name = current_user.first_name if current_user.is_authenticated else "User"
    logout_user()
    flash(f'Goodbye, {user_name}! You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/verify-email/<token>')
def verify_email(token):
    if not token:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('main.login'))
    
    user = User.query.filter_by(email_verification_token=token).first()
    
    if user:
        if user.is_verified:
            flash('Your email is already verified. You can log in.', 'info')
        else:
            user.is_verified = True
            user.email_verification_token = None
            
            try:
                db.session.commit()
                flash('Email verified successfully! You can now log in to your account.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while verifying your email. Please try again.', 'error')
                print(f"Email verification error: {e}")
    else:
        flash('Invalid or expired verification token. Please request a new verification email.', 'error')
    
    return redirect(url_for('main.login'))

@bp.route('/resend-verification')
@limiter.limit("3 per hour")
def resend_verification():
    """Resend verification email"""
    email = request.args.get('email')
    if not email:
        flash('Email address is required.', 'error')
        return redirect(url_for('main.login'))
    
    user = User.query.filter_by(email=email.lower().strip()).first()
    if not user:
        flash('No account found with that email address.', 'error')
        return redirect(url_for('main.login'))
    
    if user.is_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('main.login'))
    
    try:
        token = user.generate_verification_token()
        db.session.commit()
        send_verification_email(user, token)
        flash('Verification email sent! Please check your inbox.', 'success')
    except Exception as e:
        flash('Error sending verification email. Please try again later.', 'error')
        print(f"Resend verification error: {e}")
    
    return redirect(url_for('main.login'))

# Dashboard routes
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

# Admin route
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

# API routes
@bp.route('/api/v1/health')
def api_health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})

# Stripe configuration
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
        return redirect(url_for('main.subscription'))
    
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
            success_url=url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.subscription', _external=True),
            metadata={
                'organization_id': current_user.organization_id,
                'plan': plan_key
            }
        )
        
        return redirect(checkout_session.url)
        
    except stripe.error.StripeError as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('main.subscription'))

@bp.route('/payment/success')
@login_required
def payment_success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                flash('Payment successful! Your subscription has been upgraded.', 'success')
            else:
                flash('Payment is being processed. You will receive confirmation shortly.', 'info')
        except stripe.error.StripeError:
            flash('Payment completed, but we could not verify the details.', 'warning')
    else:
        flash('Payment completed successfully!', 'success')
    
    return redirect(url_for('main.subscription'))

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

def handle_failed_payment(invoice):
    """Handle failed payment"""
    # Extract customer ID and find subscription
    customer_id = invoice['customer']
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.PAST_DUE
        db.session.commit()

def get_plan_price(plan_key):
    """Get plan price in dollars"""
    prices = {
        'pro': 29,
        'enterprise': 99
    }
    return prices.get(plan_key, 0)