
from flask import Blueprint, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app import db, limiter
from app.models.user import User
from datetime import timedelta

bp = Blueprint('api', __name__)
jwt = JWTManager()

@bp.route('/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def api_login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email'].lower()).first()
    
    if user and user.check_password(data['password']) and user.is_active:
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=1)
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            expires_delta=timedelta(days=30)
        )
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(
        identity=current_user_id,
        expires_delta=timedelta(hours=1)
    )
    return jsonify({'access_token': access_token})

@bp.route('/auth/me', methods=['GET'])
@jwt_required()
def api_me():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()})
