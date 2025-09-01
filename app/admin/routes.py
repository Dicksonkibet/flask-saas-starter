from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.utils.decorators import role_required
from sqlalchemy import func

bp = Blueprint('admin', __name__)

@bp.route('/')
@login_required
@role_required('admin')
def index():
    """Admin dashboard"""
    # System-wide statistics
    total_users = User.query.count()
    total_orgs = Organization.query.count()
    verified_users = User.query.filter_by(is_verified=True).count()
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_orgs = Organization.query.order_by(Organization.created_at.desc()).limit(5).all()
    
    stats = {
        'total_users': total_users,
        'total_organizations': total_orgs,
        'verified_users': verified_users,
        'unverified_users': total_users - verified_users
    }
    
    return render_template('admin/index.html', 
                         stats=stats,
                         recent_users=recent_users,
                         recent_orgs=recent_orgs)

@bp.route('/users')
@login_required
@role_required('admin')
def users():
    """Manage all users"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    if role_filter:
        query = query.filter_by(role=UserRole(role_filter))
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page,
        per_page=25,
        error_out=False
    )
    
    return render_template('admin/users.html', 
                         users=users, 
                         search=search,
                         role_filter=role_filter,
                         roles=UserRole)

@bp.route('/organizations')
@login_required
@role_required('admin')
def organizations():
    """Manage all organizations"""
    page = request.args.get('page', 1, type=int)
    
    orgs = Organization.query.order_by(Organization.created_at.desc()).paginate(
        page=page,
        per_page=25,
        error_out=False
    )
    
    return render_template('admin/organizations.html', organizations=orgs)