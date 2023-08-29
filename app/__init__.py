from flask import Flask, request
import os
from app.utils import create_keycloak_user, apply_k8s_config
from slugify import slugify


app = Flask(__name__)

@app.route('/')
def home():
    return "Hello"

@app.route('/approvisionner', methods=['POST'])
def approvisionner():

    token = request.headers.get('Authorization')

    expected_token = os.environ.get('VERIFICATION_TOKEN')

    if token != expected_token:
        return {'message': 'Token invalide'}, 401

    data = request.get_json()
    email = data.get('email')
    full_name = data.get('full_name')

    username = None

    if not email:
        
        if not full_name:
            return {'message': 'Email et Nom complet manquants'}, 400
        
    if email:
        username = email.split('@')[0]
    else:
        pf = full_name.replace(" ", "_")
        pf = pf.lower()
        username = slugify(pf)
        
    user_data = create_keycloak_user(username, email)

    user_id, password = user_data

    apply_k8s_config(username, user_id)

    return {
        'message': 'Utilisateur créé',
        'user_id': user_id,
        'password': password,
        'username': username
    }

if __name__ == '__main__':
    app.run()
