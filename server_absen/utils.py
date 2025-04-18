from functools import wraps
import jwt
from flask import request, jsonify, g, current_app

def protected(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Header otorisasi tidak ada'}), 401
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Format token tidak valid'}), 401

        try:
            data = jwt.decode(parts[1], current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user_data = data
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token kedaluwarsa'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid'}), 401

    return wrapper