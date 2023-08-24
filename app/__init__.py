from flask import Flask, request
import os
from utils import create_keycloak_user, apply_k8s_config

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello"

@app.route('/aprovisionner', methods=['POST'])
def aprovisionner():

    token = request.headers.get('Authorization')

    expected_token = os.environ.get('VERIFICATION_TOKEN')

    if token != expected_token:
        return {'message': 'Token invalide'}, 401

    data = request.get_json()
    email = data.get('email')

    if not email:
        return {'message': 'Email manquant'}, 400
    
    user_data = create_keycloak_user(email)

    user_id, password = user_data

    apply_k8s_config(email.split('@')[0], user_id)

    return {
        'message': 'Utilisateur créé',
        'user_id': user_id,
        'password': password
    }

if __name__ == '__main__':
    app.run()
