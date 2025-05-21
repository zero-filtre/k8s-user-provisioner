import os
import logging

from opentelemetry import trace

from flask import Flask, request

from app.utils import create_keycloak_user, apply_k8s_config, delete_keycloak_user, delete_k8s_namespace, \
    create_grafana_user, delete_grafana_user, make_username, make_usernames, get_provisioned_users, \
    get_old_provisioned_users

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
            # Get all provisioned users from Keycloak
            users = get_provisioned_users()
            
            print(users)
            
            
            # Delete all existing namespaces for provisioned users
            for user in users:
                username = user.get('username')
                if username:
                    try:
                        delete_k8s_namespace(username)
                        logger.info(f"Deleted namespace for user: {username}")
                    except Exception as e:
                        logger.error(f"Failed to delete namespace for user {username}: {e}", exc_info=True)

            # Recreate namespaces for all provisioned users
            for user in users:
                username = user.get('username')
                user_id = user.get('id')
                if username and user_id:
                    try:
                        apply_k8s_config(username, user_id)
                        logger.info(f"Recreated namespace for user: {username}")
                    except Exception as e:
                        logger.error(f"Failed to recreate namespace for user {username}: {e}", exc_info=True)

            return {
                'message': 'All provisioned namespaces have been reset successfully',
                'users_processed': len(users),
                'namespaces_recreated': len(users)
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
            
            print(old_users)
                        
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

if __name__ == '__main__':
    app.run()
