from flask import Flask, request, jsonify, g
from functools import wraps
import jwt
import datetime

app = Flask(__name__)

# Secret key for JWT
SECRET_KEY = "mysecretkey"

# Hardcoded users with credentials and dashboard messages
users = {
    "user": {"password": "default", "message": "Hi normal user"},
    "admin": {"password": "default", "message": "Hi first level admin"},
    "superadmin": {"password": "default", "message": "Hi root"}
}

# Decorator to protect routes
def protected(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Authorization header is missing'}), 401

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({'message': 'Invalid Authorization header'}), 401

        token = parts[1]
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            g.user_data = data  # Store decoded token data in g
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
    return wrapper

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400

    username = data['username']
    password = data['password']

    if username in users and users[username]['password'] == password:
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }, SECRET_KEY, algorithm='HS256')
        # Ensure token is a string (handles PyJWT 1.x and 2.x compatibility)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

# Protected dashboard data endpoint
@app.route('/dashboard_data', methods=['GET'])
@protected
def dashboard_data():
    username = g.user_data['user']
    message = users.get(username, {}).get('message', 'Unknown user')
    return jsonify({'message': message})

@app.route('/cek_login', methods=['GET'])
@protected
def cek_login():
    return jsonify({'message': 'logged_in'})

@app.route('/get_permitted_locations', methods=['GET'])
@protected
def get_permitted_locations():
    data = [
          {
            'id': '1',
            'name': 'SMAIT Ihsanul Fikri',
            'latitude': '-7.583571594340874',
            'longitude': '110.25037258950822',
            # depan TU SMAIT
          },
          {
            'id': '2',
            'name': 'SMPIT Ihsanul Fikri',
            'latitude': '-7.584018928602248',
            'longitude': '110.25155007925902',
            # depan TU Akhwat SMPIT
          },
          {
            'id': '3',
            'name': 'SMKIT Ihsanul Fikri',
            'latitude': '-7.5684832452628825',
            'longitude': '110.2397089624626',
            # depan TU SMKIT
          },
        ] # bisa jadi error dari sini
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
