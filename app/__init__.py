import os
import logging
import json
from datetime import datetime

from opentelemetry import trace

from flask import Flask, request


from app.utils import create_keycloak_user, apply_k8s_config, delete_keycloak_user, delete_k8s_namespace, \
    create_grafana_user, delete_grafana_user, make_username, make_usernames, get_provisioned_users, \
    get_old_provisioned_users, delete_namespace_resources, generate_password, check_namespace_exists, get_grafana_user, get_keycloak_admin

app = Flask(__name__)
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)
tracer = trace.get_tracer_provider().get_tracer(__name__)

with tracer.start_as_current_span("provisioner-flask-endpoint"):
    logger.info("Provisioning flask endpoint.")
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

        if not email and not full_name:
            return {'message': 'Email address and full name are missing'}, 400

        username = make_username(email, full_name)
        logger.info(f"will attempt to create sandbox with username : {username}")

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
        email = data.get("email")
        full_name = data.get('full_name')

        if not email and not full_name:
            return {'message': 'Email address and full name are missing'}, 400

        usernames = make_usernames(email, full_name)

        for username in usernames:
            try:
                logger.info(f"Attempting to delete sandbox with username : {username}")
                delete_k8s_namespace(username)
                user_id = delete_keycloak_user(username)
                delete_grafana_user(username)
                return {
                    'message': 'User has been deleted successfully',
                    'user_id': user_id,
                    'username': username
                }
            except Exception as e:
                logger.error(f"Failed to delete with this username : {username} : {e}", exc_info=True)

        return {"Failed to delete user and related resources, it may not exist."}, 500

    @app.route('/reset', methods=['POST'])
    def reset_namespaces():
        token = request.headers.get('Authorization')

        expected_token = os.environ.get('VERIFICATION_TOKEN')

        if token != expected_token:
            return {'message': 'Please submit a valid token'}, 401

        try:
            data = request.get_json() or {}
            target_username = data.get('username')
            
            # Get all provisioned users from Keycloak
            users = get_provisioned_users()
            reset_namespaces = []
            failed_resets = []
     
            # Filter users if a specific username is provided
            if target_username:
                users = [user for user in users if user.get('username') == target_username]
                if not users:
                    return {'message': f'No provisioned user found with username: {target_username}'}, 404
            
            # Delete all resources in each namespace
            for user in users:
                username = user.get('username')
                if username:
                    try:
                        delete_namespace_resources(username)
                        logger.info(f"Reset namespace for user: {username}")
                        reset_namespaces.append(username)
                    except Exception as e:
                        print(e)
                        logger.error(f"Failed to reset namespace for user {username}: {e}", exc_info=True)
                        failed_resets.append(username)

            message = 'All provisioned namespaces have been reset successfully' if not target_username else f'Namespace for user {target_username} has been reset successfully'
            return {
                'message': message,
                'users_processed': len(users),
                'namespaces_reset': len(reset_namespaces),
                'failed_resets': failed_resets
            }

        except Exception as e:
            logger.error(f"Failed to reset namespaces: {e}", exc_info=True)
            return {'message': 'Failed to reset namespaces'}, 500

    @app.route('/cleanup', methods=['POST'])
    def cleanup_old_users():
        token = request.headers.get('Authorization')

        expected_token = os.environ.get('VERIFICATION_TOKEN')

        if token != expected_token:
            return {'message': 'Please submit a valid token'}, 401

        try:
            # Get all old provisioned users
            old_users = get_old_provisioned_users()
            
            deleted_users = []
            failed_deletions = []
            
            # Delete all resources for each old user
            for user in old_users:
                username = user.get('username')
                if not username:
                    continue
                    
                try:
                    logger.info(f"Cleaning up resources for user: {username}")
                    
                    # Delete namespace
                    try:
                        delete_k8s_namespace(username)
                        logger.info(f"Deleted namespace for user: {username}")
                    except Exception as e:
                        logger.error(f"Failed to delete namespace for user {username}: {e}", exc_info=True)
                    
                    # Delete Grafana user
                    try:
                        delete_grafana_user(username)
                        logger.info(f"Deleted Grafana user: {username}")
                    except Exception as e:
                        logger.error(f"Failed to delete Grafana user {username}: {e}", exc_info=True)
                    
                    # Delete Keycloak user
                    try:
                        user_id = delete_keycloak_user(username)
                        logger.info(f"Deleted Keycloak user: {username}")
                        deleted_users.append({
                            'username': username,
                            'user_id': user_id
                        })
                    except Exception as e:
                        logger.error(f"Failed to delete Keycloak user {username}: {e}", exc_info=True)
                        failed_deletions.append(username)
                        
                except Exception as e:
                    logger.error(f"Failed to clean up user {username}: {e}", exc_info=True)
                    failed_deletions.append(username)

            return {
                'message': 'Cleanup completed',
                'deleted_users': deleted_users,
                'failed_deletions': failed_deletions,
                'total_processed': len(old_users),
                'successfully_deleted': len(deleted_users),
                'failed': len(failed_deletions)
            }

        except Exception as e:
            logger.error(f"Failed to perform cleanup: {e}", exc_info=True)
            return {'message': 'Failed to perform cleanup'}, 500

    @app.route('/sync', methods=['POST'])
    def sync_users():
        token = request.headers.get('Authorization')

        expected_token = os.environ.get('VERIFICATION_TOKEN')

        if token != expected_token:
            return {'message': 'Please submit a valid token'}, 401

        try:
            data = request.get_json() or {}
            target_username = data.get('username')
            
            # Get all provisioned users from Keycloak
            users = get_provisioned_users()
            
            print(target_username)
            
            # Filter users if a specific username is provided
            if target_username:
                users = [user for user in users if user.get('username') == target_username]
                if not users:
                    return {'message': f'No provisioned user found with username: {target_username}'}, 404
            
            sync_results = {
                'total_users': len(users),
                'fixed_users': [],
                'failed_fixes': []
            }

            for user in users:
                username = user.get('username')
                email = user.get('email')
                if not username:
                    continue

                try:
                    # Check Grafana user
                    grafana_user = get_grafana_user(username)
                    needs_grafana = not grafana_user
                    print(needs_grafana)

                    # Check Kubernetes namespace
                    needs_namespace = not check_namespace_exists(username)
                    print(needs_namespace)

                    if needs_grafana or needs_namespace:
                        # Get user's password from Keycloak
                        keycloak_admin = get_keycloak_admin()
                        user_id = keycloak_admin.get_user_id(username)
                        
                        if needs_grafana:
                            try:
                                # Get user creation year from Keycloak
                                created_timestamp = user.get('createdTimestamp', 0) / 1000  # Convert to seconds
                                created_date = datetime.fromtimestamp(created_timestamp)
                                creation_year = created_date.year
                                
                                # Create Grafana user with password based on creation year
                                password = generate_password(username, creation_year)
                                create_grafana_user(username, email, password)
                                logger.info(f"Created missing Grafana user: {username}")
                            except Exception as e:
                                logger.error(f"Failed to create Grafana user {username}: {e}", exc_info=True)
                                sync_results['failed_fixes'].append({
                                    'username': username,
                                    'error': f"Failed to create Grafana user: {str(e)}"
                                })
                                continue

                        if needs_namespace:
                            try:
                                # Create Kubernetes namespace
                                apply_k8s_config(username, user_id)
                                logger.info(f"Created missing namespace for user: {username}")
                            except Exception as e:
                                logger.error(f"Failed to create namespace for user {username}: {e}", exc_info=True)
                                sync_results['failed_fixes'].append({
                                    'username': username,
                                    'error': f"Failed to create namespace: {str(e)}"
                                })
                                continue

                        sync_results['fixed_users'].append({
                            'username': username,
                            'fixed_grafana': needs_grafana,
                            'fixed_namespace': needs_namespace
                        })

                except Exception as e:
                    logger.error(f"Failed to sync user {username}: {e}", exc_info=True)
                    sync_results['failed_fixes'].append({
                        'username': username,
                        'error': str(e)
                    })

            message = 'Sync completed for all users' if not target_username else f'Sync completed for user {target_username}'
            return {
                'message': message,
                'results': sync_results
            }

        except Exception as e:
            logger.error(f"Failed to perform sync: {e}", exc_info=True)
            return {'message': 'Failed to perform sync'}, 500
        
        
if __name__ == '__main__':
    app.run()
