from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db, cache
from app.models.user import User
from app.models.organization import Organization
from app.utils.decorators import role_required
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    # Get dashboard stats
    stats = get_dashboard_stats()
    recent_users = get_recent_users()
    
    return render_template('dashboard/index.html', 
                         stats=stats, 
                         recent_users=recent_users)

@bp.route('/users')
@login_required
@role_required('manager')
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query.filter_by(organization_id=current_user.organization_id)
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    users = query.paginate(
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    return render_template('dashboard/users.html', users=users, search=search)

@bp.route('/settings')
@login_required
def settings():
    return render_template('dashboard/settings.html')

@bp.route('/stats')
@login_required
def api_stats():
    """HTMX endpoint for live dashboard updates"""
    stats = get_dashboard_stats()
    return jsonify(stats)

@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_dashboard_stats():
    """Get dashboard statistics"""
    org_id = current_user.organization_id
    
    total_users = User.query.filter_by(organization_id=org_id).count()
    active_users = User.query.filter_by(
        organization_id=org_id, 
        is_active=True
    ).count()
    
    # Users created this month
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = User.query.filter(
        User.organization_id == org_id,
        User.created_at >= month_start
    ).count()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'new_users_this_month': new_users_this_month,
        'inactive_users': total_users - active_users
    }

def get_recent_users(limit=5):
    """Get recently registered users"""
    return User.query.filter_by(
        organization_id=current_user.organization_id
    ).order_by(User.created_at.desc()).limit(limit).all()
