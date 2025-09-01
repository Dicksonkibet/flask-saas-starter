
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user

def anonymous_required(f):
    """Decorator to redirect logged-in users away from auth pages"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorator to require specific user role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if required_role == 'admin' and not current_user.is_admin():
                abort(403)
            elif required_role == 'manager' and current_user.role.value not in ['manager', 'admin']:
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def organization_required(f):
    """Decorator to ensure user belongs to an organization"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.organization_id:
            flash('You need to join an organization first.', 'warning')
            return redirect(url_for('dashboard.settings'))
        return f(*args, **kwargs)
    return decorated_function
