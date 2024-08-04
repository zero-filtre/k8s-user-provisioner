from flask import Flask, request
import os
from app.utils import create_keycloak_user, apply_k8s_config, delete_keycloak_user, delete_k8s_namespace, \
    create_grafana_user, delete_grafana_user
from slugify import slugify

app = Flask(__name__)


@app.route('/')
def home():
    return "Hello"


@app.route('/provisioner', methods=['POST'])
def provisioner():
    token = request.headers.get('Authorization')

    expected_token = os.environ.get('VERIFICATION_TOKEN')

    if token != expected_token:
        return {'message': 'Please submit a valid token'}, 401

    data = request.get_json()
    email = data.get('email')
    full_name = data.get('full_name')

    username = None

    if not email:

        if not full_name:
            return {'message': 'Email address and full name are missing'}, 400

    if email:
        username = email.split('@')[0]
        username = username.replace(".", "_")
        username = slugify(username)
    else:
        pf = full_name.replace(" ", "_")
        pf = pf.lower()
        username = slugify(pf)

    print(username)

    user_data = create_keycloak_user(username, email)

    if user_data == "CREATED":
        return {'message': "USER ALREADY EXIST"}, 500

    user_id, password = user_data

    try:
        apply_k8s_config(username, user_id)
    except:
        delete_keycloak_user(username)
        return {'message': "Can't create k8s user"}, 500

    try:
        create_grafana_user(username, email, password)
    except:
        delete_keycloak_user(username)
        delete_k8s_namespace(username)
        return {'message': "Can't create grafana user"}, 500

    return {
        'message': 'User has been successfully created',
        'user_id': user_id,
        'password': password,
        'username': username
    }


@app.route('/provisioner', methods=['DELETE'])
def provisioner_clean():
    token = request.headers.get('Authorization')

    expected_token = os.environ.get('VERIFICATION_TOKEN')

    if token != expected_token:
        return {'message': 'Please submit a valid token'}, 401

    data = request.get_json()
    username = data.get('username')

    user_id = delete_keycloak_user(username)

    delete_k8s_namespace(username)
    delete_grafana_user(username)

    return {
        'message': 'User has been deleted successfully',
        'user_id': user_id,
        'username': username
    }


if __name__ == '__main__':
    app.run()
