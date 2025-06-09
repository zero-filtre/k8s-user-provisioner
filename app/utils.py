import json
import os
import random
import string
import logging

import yaml
from dotenv import load_dotenv
from grafana_client import GrafanaApi
from keycloak import KeycloakAdmin
from kubernetes import client, config, utils
from slugify import slugify

load_dotenv("/vault/secrets/config")
load_dotenv(".env")

logger = logging.getLogger(__name__)


grafana = GrafanaApi.from_url(
    url="https://grafana.zerofiltre.tech",
    credential=(os.environ.get('GRAFANA_USER'), os.environ.get('GRAFANA_PASSWORD'))
)


def generate_password(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_keycloak_admin():
    """Get a configured KeycloakAdmin client"""
    KEYCLOAK_BASE_URL = os.environ.get('KEYCLOAK_BASE_URL')
    REALM = os.environ.get('KEYCLOAK_REALM')
    CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET')

    return KeycloakAdmin(
        server_url=KEYCLOAK_BASE_URL,
        client_id=CLIENT_ID,
        client_secret_key=CLIENT_SECRET,
        realm_name=REALM,
        verify=True
    )


def create_keycloak_user(username, email):
    keycloak_admin = get_keycloak_admin()
    generated_password = generate_password()

    user_data = {
        'email': email,
        'enabled': True,
        'username': username,
        'credentials': [{'type': 'password', 'value': generated_password}],
        'attributes': {
            'managed-by': ['k8s-provisioner'],
            'provisioned': ['true']
        }
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


def delete_namespace_resources(username):
    """Delete all resources in a namespace without deleting the namespace itself"""
    config.load_kube_config_from_dict(
        json.loads(os.environ.get('KUBE_CONFIG')))

    with client.ApiClient() as api_client:
        # Get all API resources
        api_resources = api_client.get_api_resources()
        deleted_resources = []
        failed_resources = []

        # Resources to exclude from deletion
        excluded_resources = ['resourcequota', 'rolebinding']

        # For each namespaced resource, delete all instances in the namespace
        for resource in api_resources.resources:
            if resource.namespaced and resource.name.lower() not in excluded_resources:
                try:
                    # Construct the API path
                    if resource.group:
                        # For resources with API group
                        api_path = f"/apis/{resource.group}/{resource.version}/namespaces/{username}/{resource.plural}"
                    else:
                        # For core resources
                        api_path = f"/api/v1/namespaces/{username}/{resource.plural}"

                    # Delete all resources of this type in the namespace
                    api_call_kwargs = {
                        "resource_path": api_path,
                        "method": "DELETE",
                        "response_type": "object",
                    }
                    response = api_client.call_api(**api_call_kwargs)
                    deleted_resources.append(resource.name)
                    logger.info(f"Deleted {resource.name} in namespace {username}")
                except Exception as e:
                    logger.error(f"Failed to delete {resource.name} in namespace {username}: {e}", exc_info=True)
                    failed_resources.append(resource.name)

        return {
            'deleted_resources': deleted_resources,
            'failed_resources': failed_resources
        }


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

def get_grafana_user(username):
    grafana_user = grafana.users.find_user(username)
    return grafana_user


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

    return username_based_email, username_based_fullname


def get_provisioned_users():
    keycloak_admin = get_keycloak_admin()

    # Get all users with our specific attribute
    users = keycloak_admin.get_users({
        'q': 'managed-by:k8s-provisioner'
    })
    
    # Filter users that have both required attributes
    provisioned_users = []
    for user in users:
        attributes = user.get('attributes', {})
        if (attributes.get('managed-by') == ['k8s-provisioner'] and 
            attributes.get('provisioned') == ['true']):
            provisioned_users.append(user)
    
    return provisioned_users


def get_old_provisioned_users():

    # Get all provisioned users
    users = get_provisioned_users()
    
    # Filter users created more than a year ago
    from datetime import datetime, timedelta
    one_year_ago = datetime.now() - timedelta(days=365)
    
    old_users = []
    for user in users:
        created_timestamp = user.get('createdTimestamp', 0) / 1000  # Convert to seconds
        created_date = datetime.fromtimestamp(created_timestamp)
        if created_date < one_year_ago:
            old_users.append(user)
    
    return old_users


def check_namespace_exists(username):
    """Check if a namespace exists in Kubernetes"""
    config.load_kube_config_from_dict(
        json.loads(os.environ.get('KUBE_CONFIG')))

    with client.ApiClient() as api_client:
        api_instance = client.CoreV1Api(api_client)
        try:
            api_instance.read_namespace(username)
            return True
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return False
            raise e
