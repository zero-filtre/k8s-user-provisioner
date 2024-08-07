import json
import os
import random
import string

import yaml
from dotenv import load_dotenv
from grafana_client import GrafanaApi
from keycloak import KeycloakAdmin
from kubernetes import client, config, utils
from slugify import slugify

load_dotenv("/vault/secrets/config")
load_dotenv(".env")

grafana = GrafanaApi.from_url(
    url="https://grafana.zerofiltre.tech",
    credential=(os.environ.get('GRAFANA_USER'), os.environ.get('GRAFANA_PASSWORD'))
)


def generate_password(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def create_keycloak_user(username, email):
    KEYCLOAK_BASE_URL = os.environ.get('KEYCLOAK_BASE_URL')
    REALM = os.environ.get('KEYCLOAK_REALM')
    CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET')

    keycloak_admin = KeycloakAdmin(
        server_url=KEYCLOAK_BASE_URL,
        client_id=CLIENT_ID,
        client_secret_key=CLIENT_SECRET,
        realm_name=REALM,
        verify=True
    )

    generated_password = generate_password()

    user_data = {
        'email': email,
        'enabled': True,
        'username': username,
        'credentials': [{'type': 'password', 'value': generated_password}]
    }

    user_id = keycloak_admin.get_user_id(username)

    if not user_id:
        keycloak_admin.create_user(user_data, exist_ok=True)
    else:
        return "CREATED"

    user_id = keycloak_admin.get_user_id(username)

    return user_id, generated_password


def delete_keycloak_user(username):
    KEYCLOAK_BASE_URL = os.environ.get('KEYCLOAK_BASE_URL')
    REALM = os.environ.get('KEYCLOAK_REALM')
    CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET')

    keycloak_admin = KeycloakAdmin(
        server_url=KEYCLOAK_BASE_URL,
        client_id=CLIENT_ID,
        client_secret_key=CLIENT_SECRET,
        realm_name=REALM,
        verify=True
    )

    user_id = keycloak_admin.get_user_id(username)

    if user_id:
        keycloak_admin.delete_user(user_id)

    return user_id


def apply_k8s_config(username, user_id):
    k8s_file = 'app/k8s_templates/provisionner.yaml'

    template = None

    with open(k8s_file) as f:
        template = f.read()

    template = template.replace("username", username)
    template = template.replace("user_id", user_id)

    templates = yaml.safe_load_all(template)

    config.load_kube_config_from_dict(
        json.loads(os.environ.get('KUBE_CONFIG')))

    for template in templates:
        k8s_client = client.ApiClient()

        utils.create_from_dict(k8s_client, template)

    return True


def delete_k8s_namespace(username):
    config.load_kube_config_from_dict(
        json.loads(os.environ.get('KUBE_CONFIG')))

    with client.ApiClient() as api_client:
        api_instance = client.CoreV1Api(api_client)
        api_instance.delete_namespace(username)

    return True


def create_grafana_user(username, email, password):
    user = grafana.admin.create_user({
        "name": username,
        "email": email,
        "login": username,
        "password": password,
        "role": "Viewer",
        "OrgId": 1})

    return user


def delete_grafana_user(username):
    user = grafana.users.find_user(username)

    if user:
        grafana.admin.delete_user(user['id'])

    return True


def make_username(email, full_name):
    if email:
        username = email.split('@')[0]
        username = username.replace(".", "_")
        username = slugify(username)
    else:
        pf = full_name.replace(" ", "_")
        pf = pf.lower()
        username = slugify(pf)

    return username


def make_usernames(email, full_name):
    username_based_email = None
    username_based_fullname = None

    if email:
        username_based_email = email.split('@')[0]
        username_based_email = username_based_email.replace(".", "_")
        username_based_email = slugify(username_based_email)

    if full_name:
        pf = full_name.replace(" ", "_")
        pf = pf.lower()
        username_based_fullname = slugify(pf)

    return username_based_email, username_based_email
