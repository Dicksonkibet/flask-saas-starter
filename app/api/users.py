from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_login import login_required, current_user
from app import db, limiter
from app.models.user import User, UserRole
from app.utils.decorators import role_required

bp = Blueprint('api_users', __name__)

@bp.route('/users', methods=['GET'])
@jwt_required()
@limiter.limit("100 per minute")
def get_users():
    """Get users for current organization"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.organization_id:
        return jsonify({'error': 'Organization required'}), 400
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    search = request.args.get('search', '')
    
    query = User.query.filter_by(organization_id=user.organization_id)
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    users = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'users': [user.to_dict() for user in users.items],
        'pagination': {
            'page': users.page,
            'pages': users.pages,
            'per_page': users.per_page,
            'total': users.total,
            'has_next': users.has_next,
            'has_prev': users.has_prev
        }
    })

@bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get specific user"""
    current_user_id = get_jwt_identity()
    current_user_obj = User.query.get(current_user_id)
    
    user = User.query.get_or_404(user_id)
    
    # Check if user belongs to same organization
    if user.organization_id != current_user_obj.organization_id:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({'user': user.to_dict()})

@bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@limiter.limit("30 per minute")
def update_user(user_id):
    """Update user"""
    current_user_id = get_jwt_identity()
    current_user_obj = User.query.get(current_user_id)
    
    user = User.query.get_or_404(user_id)
    
    # Check permissions
    if user.organization_id != current_user_obj.organization_id:
        return jsonify({'error': 'Access denied'}), 403
    
    if not current_user_obj.has_role(UserRole.MANAGER) and user_id != current_user_id:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    # Update allowed fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'bio' in data:
        user.bio = data['bio']
    
    # Only managers/admins can update these fields
    if current_user_obj.has_role(UserRole.MANAGER):
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'role' in data and current_user_obj.is_admin():
            user.role = UserRole(data['role'])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required('manager')
def delete_user(user_id):
    """Delete user (soft delete by deactivation)"""
    current_user_id = get_jwt_identity()
    current_user_obj = User.query.get(current_user_id)
    
    user = User.query.get_or_404(user_id)
    
    if user.organization_id != current_user_obj.organization_id:
        return jsonify({'error': 'Access denied'}), 403
    
    if user.is_admin() and not current_user_obj.is_admin():
        return jsonify({'error': 'Cannot delete admin users'}), 403
    
    # Soft delete - just deactivate
    user.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User deactivated successfully'})