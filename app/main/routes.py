from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime, timezone
from app import db, limiter
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.enums import SubscriptionStatus, SubscriptionPlan
from app.auth.forms import LoginForm, RegisterForm, ResetPasswordForm
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.decorators import anonymous_required
from app.models.subscription import Subscription, SubscriptionPlan
from app.utils.decorators import role_required
from app.services.subscription_service import SubscriptionService
import stripe
import os
import re

bp = Blueprint('main', __name__)

# Initialize subscription service
def get_subscription_service():
    """Get subscription service instance"""
    return SubscriptionService()

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
            
            # STEP 1: Create organization first WITHOUT owner_id
            org_slug = f"{username}-org"
            counter = 1
            while Organization.query.filter_by(slug=org_slug).first():
                org_slug = f"{username}-org-{counter}"
                counter += 1
            
            org = Organization(
                name=f"{first_name}'s Organization",
                slug=org_slug,
                subscription_plan='free',
                subscription_status=SubscriptionStatus.TRIAL.value,
                owner_id=None  # Important: Set to None initially
            )
            db.session.add(org)
            db.session.flush()  # Get the organization ID without committing
            
            # STEP 2: Create user with organization_id
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.ADMIN,
                organization_id=org.id,  # Now we have the org ID
                is_active=True,
                is_verified=False  # Will be set to True after email verification
            )
            user.set_password(form.password.data)
            
            # Generate verification token
            token = user.generate_verification_token()
            
            db.session.add(user)
            db.session.flush()  # Get the user ID without committing
            
            # STEP 3: Update organization with owner_id
            org.owner_id = user.id  # Now we can set the owner
            
            # STEP 4: Create subscription using service
            subscription_service = get_subscription_service()
            subscription = subscription_service.create_subscription(org, 'free')
            
            # Start trial for new organizations
            subscription.start_trial(days=14)
            
            # STEP 5: Commit everything together
            db.session.commit()
            
            # Send verification email
            try:
                send_verification_email(user, token)
                flash('Registration successful! Please check your email to verify your account before logging in. You also have a 14-day free trial of Pro features!', 'success')
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
        
        # Get subscription info for dashboard context
        try:
            subscription_service = get_subscription_service()
            subscription = subscription_service.get_organization_subscription(current_user.organization_id)
            
            # Add subscription info to stats
            stats['subscription'] = {
                'plan': subscription.plan.value if subscription else 'free',
                'status': subscription.status.value if subscription else 'unknown',
                'is_trialing': subscription.is_trialing if subscription else False,
                'days_remaining': subscription.days_remaining_in_trial if subscription else 0
            }
        except Exception as e:
            print(f"Error getting subscription info for dashboard: {e}")
            stats['subscription'] = None
            
    else:
        stats = {
            'total_users': 0, 
            'active_users': 0, 
            'verified_users': 0, 
            'admin_users': 0,
            'subscription': None
        }
        recent_users = []
    
    return render_template('dashboard/index.html', stats=stats, recent_users=recent_users)

# Admin route - Updated to show all users system-wide
@bp.route('/admin')
@login_required
def admin():
    """Admin dashboard page"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get system-wide statistics (all users across all organizations)
    all_users = User.query.all()
    stats = {
        'total_users': len(all_users),
        'active_users': sum(1 for user in all_users if user.is_active),
        'verified_users': sum(1 for user in all_users if user.is_verified),
        'admin_users': sum(1 for user in all_users if user.role == UserRole.ADMIN)
    }
    
    # Additional system-wide stats
    total_organizations = Organization.query.count()
    stats['total_organizations'] = total_organizations
    
    # Recent registrations (last 10 users across all organizations)
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    return render_template('dashboard/admin.html', stats=stats, recent_users=recent_users)
# Users management route - Enhanced version
# Users management route - Updated to show all users or organization users based on preference
@bp.route('/users')
@login_required
def users():
    """Users management page"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Check if admin wants to see all users or just organization users
        view_all = request.args.get('all', 'false').lower() == 'true'
        
        if view_all:
            # Show all users across all organizations (super admin view)
            users = User.query.order_by(User.created_at.desc()).all()
            # Get all organizations for context
            organizations = Organization.query.all()
            org_dict = {org.id: org for org in organizations}
        else:
            # Show only users from the same organization (organization admin view)
            users = User.query.filter_by(organization_id=current_user.organization_id)\
                             .order_by(User.created_at.desc())\
                             .all()
            org_dict = {current_user.organization_id: current_user.organization}
        
        return render_template('dashboard/users.html', 
                             users=users, 
                             organizations=org_dict,
                             view_all=view_all,
                             UserRole=UserRole)
        
    except Exception as e:
        flash('Error loading users. Please try again.', 'error')
        print(f"Error in users management: {e}")
        return redirect(url_for('main.dashboard'))

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
# API stats endpoint - Updated to include system-wide stats
@bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard statistics"""
    if current_user.is_admin():
        # System-wide stats for admins
        view_type = request.args.get('view', 'organization')  # 'organization' or 'system'
        
        if view_type == 'system':
            all_users = User.query.all()
            stats = {
                'total_users': len(all_users),
                'active_users': sum(1 for user in all_users if user.is_active),
                'verified_users': sum(1 for user in all_users if user.is_verified),
                'admin_users': sum(1 for user in all_users if user.role == UserRole.ADMIN),
                'total_organizations': Organization.query.count()
            }
        else:
            # Organization-specific stats
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
    else:
        # Non-admin users only see their organization stats
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

@bp.route('/admin/analytics')
@login_required
@role_required('admin')
def admin_analytics():
    """System-wide analytics for admins"""
    try:
        # User registration trends
        from sqlalchemy import func, extract
        
        # Users registered per month (last 12 months)
        monthly_registrations = db.session.query(
            extract('year', User.created_at).label('year'),
            extract('month', User.created_at).label('month'),
            func.count(User.id).label('count')
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        # Organization growth
        monthly_orgs = db.session.query(
            extract('year', Organization.created_at).label('year'),
            extract('month', Organization.created_at).label('month'),
            func.count(Organization.id).label('count')
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        # Active users by organization
        org_stats = db.session.query(
            Organization.name,
            func.count(User.id).label('total_users'),
            func.sum(User.is_active.cast(db.Integer)).label('active_users')
        ).join(User).group_by(Organization.id).all()
        
        analytics_data = {
            'monthly_registrations': [
                {'year': int(r.year), 'month': int(r.month), 'count': r.count}
                for r in monthly_registrations
            ],
            'monthly_organizations': [
                {'year': int(r.year), 'month': int(r.month), 'count': r.count}
                for r in monthly_orgs
            ],
            'organization_stats': [
                {'name': r.name, 'total_users': r.total_users, 'active_users': r.active_users}
                for r in org_stats
            ]
        }
        
        return render_template('dashboard/analytics.html', analytics=analytics_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading admin analytics: {e}")
        flash('Error loading analytics. Please try again.', 'error')
        return redirect(url_for('main.admin'))

# API routes
@bp.route('/api/v1/health')
def api_health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})

# SUBSCRIPTION ROUTES - Updated to use service consistently

@bp.route('/subscription')
@login_required
def subscription():
    """Current subscription details"""
    try:
        subscription_service = get_subscription_service()
        subscription = subscription_service.get_organization_subscription(current_user.organization_id)
        
        return render_template('pricing.html', subscription=subscription)
    
    except Exception as e:
        current_app.logger.error(f"Error loading subscription: {e}")
        flash('Error loading subscription information. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@bp.route('/pricing')
def pricing():
    """Display subscription plans and pricing"""
    try:
        # Define plan prices with detailed information
        plans = {
            'free': {
                'name': 'Free',
                'price': 0,
                'features': [
                    'Up to 5 users',
                    'Basic features',
                    '1GB storage',
                    'Community support'
                ],
                'recommended': False
            },
            'pro': {
                'name': 'Pro',
                'price': 29,
                'features': [
                    'Up to 25 users',
                    'Advanced features',
                    '10GB storage',
                    'Priority support',
                    'Custom branding'
                ],
                'recommended': True
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 99,
                'features': [
                    'Unlimited users',
                    'All features',
                    '100GB storage',
                    '24/7 dedicated support',
                    'Custom integrations',
                    'SLA guarantee'
                ],
                'recommended': False
            }
        }
        
        # Check if user is logged in and get their current subscription
        current_subscription = None
        if current_user.is_authenticated and current_user.organization_id:
            subscription_service = get_subscription_service()
            current_subscription = subscription_service.get_organization_subscription(
                current_user.organization_id
            )
        
        return render_template('pricing.html', 
                             plans=plans, 
                             subscription=current_subscription)  # Changed to 'subscription' for consistency
    
    except Exception as e:
        # Log the error for debugging
        current_app.logger.error(f"Error loading pricing page: {str(e)}")
        
        # Fallback plans in case of error
        fallback_plans = {
            'free': {'name': 'Free', 'price': 0},
            'pro': {'name': 'Pro', 'price': 29},
            'enterprise': {'name': 'Enterprise', 'price': 99}
        }
        
        flash('We encountered a temporary issue loading our plans. Please try again shortly.', 'warning')
        return render_template('pricing.html', plans=fallback_plans, subscription=None)

@bp.route('/upgrade/<plan_key>')
@login_required
@role_required('admin')
def upgrade_plan(plan_key):
    """Upgrade subscription plan"""
    if plan_key not in ['pro', 'enterprise']:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('main.subscription'))
    
    try:
        subscription_service = get_subscription_service()
        
        # Check current subscription
        current_subscription = subscription_service.get_organization_subscription(current_user.organization_id)
        
        # Prevent downgrading through this route
        if current_subscription and current_subscription.plan.value == plan_key:
            flash(f'You are already on the {plan_key.title()} plan.', 'info')
            return redirect(url_for('main.subscription'))
        
        success_url = url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = url_for('main.subscription', _external=True)
        
        checkout_session = subscription_service.create_stripe_checkout_session(
            current_user.organization,
            plan_key,
            success_url,
            cancel_url
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        current_app.logger.error(f"Error creating payment session: {e}")
        flash(f'Error creating payment session: {str(e)}', 'error')
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
                # Update subscription using service
                subscription_service = get_subscription_service()
                organization_id = session['metadata']['organization_id']
                plan_key = session['metadata']['plan']
                
                # The webhook should handle this, but let's be safe
                subscription = subscription_service.get_organization_subscription(organization_id)
                if subscription:
                    subscription.upgrade_plan(plan_key)
                    db.session.commit()
                
                flash('Payment successful! Your subscription has been upgraded.', 'success')
            else:
                flash('Payment is being processed. You will receive confirmation shortly.', 'info')
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Error verifying payment: {e}")
            flash('Payment completed, but we could not verify the details.', 'warning')
    else:
        flash('Payment completed successfully!', 'success')
    
    return redirect(url_for('main.subscription'))

@bp.route('/subscription/cancel')
@login_required
@role_required('admin')
def cancel_subscription():
    """Cancel subscription"""
    try:
        subscription_service = get_subscription_service()
        success = subscription_service.cancel_subscription(current_user.organization_id)
        
        if success:
            flash('Your subscription has been canceled. You can continue using the service until the end of your billing period.', 'success')
        else:
            flash('Error canceling subscription. Please try again or contact support.', 'error')
            
    except Exception as e:
        current_app.logger.error(f"Error canceling subscription: {e}")
        flash(f'Error canceling subscription: {str(e)}', 'error')
    
    return redirect(url_for('main.subscription'))

@bp.route('/subscription/reactivate')
@login_required
@role_required('admin')
def reactivate_subscription():
    """Reactivate a canceled subscription"""
    try:
        subscription_service = get_subscription_service()
        subscription = subscription_service.get_organization_subscription(current_user.organization_id)
        
        if subscription and subscription.status == SubscriptionStatus.CANCELLED:
            subscription.renew()
            db.session.commit()
            flash('Your subscription has been reactivated successfully.', 'success')
        else:
            flash('No canceled subscription found to reactivate.', 'info')
    
    except Exception as e:
        current_app.logger.error(f"Error reactivating subscription: {e}")
        flash('Error reactivating subscription. Please try again.', 'error')
    
    return redirect(url_for('main.subscription'))

@bp.route('/downgrade/<plan_key>', methods=['POST'])
@login_required
@role_required('admin')
def downgrade_plan(plan_key):
    """Downgrade subscription plan"""
    if plan_key not in ['free']:  # Only allow downgrade to free
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('main.pricing'))
    
    try:
        subscription_service = get_subscription_service()
        current_subscription = subscription_service.get_organization_subscription(current_user.organization_id)
        
        if not current_subscription:
            flash('No subscription found.', 'error')
            return redirect(url_for('main.pricing'))
        
        if current_subscription.plan.value == plan_key:
            flash(f'You are already on the {plan_key.title()} plan.', 'info')
            return redirect(url_for('main.pricing'))
        
        # Cancel current subscription if it has Stripe integration
        if current_subscription.stripe_subscription_id:
            success = subscription_service.cancel_subscription(current_user.organization_id, at_period_end=True)
            if success:
                flash('Your subscription will be downgraded to Free at the end of your current billing period.', 'success')
            else:
                flash('Error scheduling downgrade. Please contact support.', 'error')
        else:
            # Immediately downgrade local subscription
            subscription_service.upgrade_subscription(current_user.organization_id, plan_key)
            flash('Your subscription has been downgraded to Free.', 'success')
            
    except Exception as e:
        current_app.logger.error(f"Error downgrading subscription: {e}")
        flash('Error processing downgrade. Please try again.', 'error')
    
    return redirect(url_for('main.pricing'))

@bp.route('/subscription/analytics')
@login_required
@role_required('admin')
def subscription_analytics():
    """Get subscription analytics"""
    try:
        subscription_service = get_subscription_service()
        analytics = subscription_service.get_subscription_analytics(current_user.organization_id)
        
        if analytics:
            return jsonify(analytics)
        else:
            return jsonify({'error': 'No subscription found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting subscription analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# WEBHOOK HANDLING - Updated

@bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        
        subscription_service = get_subscription_service()
        subscription_service.handle_webhook_event(event)
        
        return jsonify({'status': 'success'})
        
    except ValueError as e:
        current_app.logger.error(f"Invalid webhook payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        current_app.logger.error(f"Invalid webhook signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        current_app.logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# UTILITY FUNCTIONS - Removed duplicates, everything goes through service

def get_plan_price(plan_key):
    """Get plan price in dollars - DEPRECATED: Use subscription service instead"""
    prices = {
        'pro': 29,
        'enterprise': 99
    }
    return prices.get(plan_key, 0)