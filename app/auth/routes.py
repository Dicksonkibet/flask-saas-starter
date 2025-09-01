from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime, timezone
from app import db, limiter
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.auth.forms import LoginForm, RegisterForm, ResetPasswordForm
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.decorators import anonymous_required

bp = Blueprint('auth', __name__)

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
                next_page = url_for('dashboard.index')
            
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
        # Create organization
        org = Organization(
            name=f"{form.first_name.data}'s Organization",
            slug=f"{form.username.data}-org"
        )
        db.session.add(org)
        db.session.flush()  # Get the ID
        
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
        org.owner_id = user.id
        db.session.commit()
        
        # Send verification email
        send_verification_email(user, token)
        
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))
    
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
    
    return redirect(url_for('auth.login'))
