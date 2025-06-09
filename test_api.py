import requests
import json
import sys
from datetime import datetime
import time
import os
from dotenv import load_dotenv
import yaml
from kubernetes import client, config

from app.utils import (
    get_provisioned_users, get_grafana_user, check_namespace_exists,
    create_keycloak_user, apply_k8s_config, create_grafana_user,
    delete_keycloak_user, delete_k8s_namespace, delete_grafana_user,
    delete_namespace_resources, get_old_provisioned_users
)

# Configuration

load_dotenv("/vault/secrets/config")
load_dotenv(".env")

BASE_URL = "http://localhost:8000"  # Change this to your API URL
TOKEN = os.environ.get('VERIFICATION_TOKEN')

def print_response(response):
    """Helper function to print response details"""
    print(f"\nStatus Code: {response.status_code}")
    try:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except:
        print("Response:", response.text)
    print("-" * 80)

def verify_user_creation(username, email):
    """Verify that a user was properly created in all systems"""
    print("\n=== Verifying User Creation ===")
    verification_results = {
        'keycloak': False,
        'kubernetes': False,
        'grafana': False
    }
    
    # Verify Keycloak user
    users = get_provisioned_users()
    for user in users:
        if user.get('username') == username and user.get('email') == email:
            verification_results['keycloak'] = True
            break
    
    # Verify Kubernetes namespace
    if check_namespace_exists(username):
        verification_results['kubernetes'] = True
    
    # Verify Grafana user
    try:
        if get_grafana_user(username):
            verification_results['grafana'] = True
    except Exception as e:
        print(f"Grafana user not found: {e}")
    
    print("Verification Results:")
    print(json.dumps(verification_results, indent=2))
    return all(verification_results.values())

def verify_user_deletion(username):
    """Verify that a user was properly deleted from all systems"""
    print("\n=== Verifying User Deletion ===")
    verification_results = {
        'keycloak': True,
        'kubernetes': True,
        'grafana': True
    }
    
    # Verify Keycloak user
    users = get_provisioned_users()
    for user in users:
        if user.get('username') == username:
            verification_results['keycloak'] = False
            break
    
    # Verify Kubernetes namespace
    if check_namespace_exists(username):
        verification_results['kubernetes'] = False
    
    # Verify Grafana user
    try:
        if get_grafana_user(username):
            verification_results['grafana'] = False
    except Exception as e:
        # If we get an exception, it means the user doesn't exist, which is what we want
        pass
    
    print("Verification Results:")
    print(json.dumps(verification_results, indent=2))
    return all(verification_results.values())

def create_test_configmap(username):
    """Create a test ConfigMap in the user's namespace"""
    config.load_kube_config_from_dict(
        json.loads(os.environ.get('KUBE_CONFIG')))

    with client.ApiClient() as api_client:
        api_instance = client.CoreV1Api(api_client)
        
        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name="test-configmap",
                namespace=username
            ),
            data={"test": "data"}
        )
        
        try:
            api_instance.create_namespaced_config_map(
                namespace=username,
                body=configmap
            )
            print(f"Created test ConfigMap in namespace {username}")
            return True
        except Exception as e:
            print(f"Failed to create test ConfigMap: {e}")
            return False

def verify_namespace_reset(username):
    """Verify that a namespace was properly reset by checking if the test ConfigMap still exists"""
    print(f"\n=== Verifying Namespace Reset for {username} ===")
    verification_results = {
        'namespace_exists': False,
        'configmap_deleted': False
    }
    
    # Verify namespace still exists
    if check_namespace_exists(username):
        verification_results['namespace_exists'] = True
        
        # Check if test ConfigMap still exists
        try:
            config.load_kube_config_from_dict(
                json.loads(os.environ.get('KUBE_CONFIG')))

            with client.ApiClient() as api_client:
                api_instance = client.CoreV1Api(api_client)
                
                try:
                    # Try to get the test ConfigMap
                    api_instance.read_namespaced_config_map(
                        name="test-configmap",
                        namespace=username
                    )
                    # If we get here, the ConfigMap still exists
                    verification_results['configmap_deleted'] = False
                    print(f"Test ConfigMap still exists in namespace {username}")
                except client.exceptions.ApiException as e:
                    if e.status == 404:
                        # ConfigMap not found, which is what we want
                        verification_results['configmap_deleted'] = True
                    else:
                        raise e
                
        except Exception as e:
            print(f"Error checking ConfigMap: {e}")
    
    print("Verification Results:")
    print(json.dumps(verification_results, indent=2))
    return verification_results['namespace_exists'] and verification_results['configmap_deleted']

def test_create_user(email, full_name):
    """Test user creation with verification"""
    print("\n=== Testing User Creation ===")
    url = f"{BASE_URL}/provisioner"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    data = {
        'email': email,
        'full_name': full_name
    }
    
    response = requests.post(url, headers=headers, json=data)
    print_response(response)
    
    if response.status_code == 200:
        user_data = response.json()
        username = user_data.get('username')
        
        # Wait a bit for all systems to sync
        time.sleep(5)
        
        # Create test ConfigMap
        if create_test_configmap(username):
            print("✓ Test ConfigMap created successfully")
        else:
            print("✗ Failed to create test ConfigMap")
            return None
        
        # Verify user creation
        if verify_user_creation(username, email):
            print("✓ User creation verified successfully")
        else:
            print("✗ User creation verification failed")
            return None
            
        return user_data
    return None

def test_delete_user(email, full_name):
    """Test user deletion with verification"""
    print("\n=== Testing User Deletion ===")
    url = f"{BASE_URL}/provisioner"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    data = {
        'email': email,
        'full_name': full_name
    }
    
    response = requests.delete(url, headers=headers, json=data)
    print_response(response)
    
    if response.status_code == 200:
        user_data = response.json()
        username = user_data.get('username')
        
        # Wait a bit for all systems to sync
        time.sleep(5)
        
        # Verify user deletion
        if verify_user_deletion(username):
            print("✓ User deletion verified successfully")
        else:
            print("✗ User deletion verification failed")
            return None
            
        return user_data
    return None

def test_reset_namespaces():
    """Test namespace reset with verification"""
    print("\n=== Testing Namespace Reset ===")
    url = f"{BASE_URL}/reset"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        result = response.json()
        
        # Wait a bit for all systems to sync
        time.sleep(5)
        
        # Get the test user's username from the last created user
        users = get_provisioned_users()
        if not users:
            print("✗ No users found to verify reset")
            return None
            
        test_user = users[-1]  # Get the last created user
        username = test_user.get('username')
        
        if not username:
            print("✗ Could not find test user's username")
            return None
            
        # Verify namespace reset for the test user
        if verify_namespace_reset(username):
            print("✓ Namespace reset verified successfully")
        else:
            print("✗ Namespace reset verification failed")
            
        return result
    return None

def test_cleanup_old_users():
    """Test cleanup of old users with verification"""
    print("\n=== Testing Old Users Cleanup ===")
    url = f"{BASE_URL}/cleanup"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        result = response.json()
        
        # Wait a bit for all systems to sync
        time.sleep(5)
        
        # Verify user deletions
        all_verified = True
        for user in result.get('deleted_users', []):
            username = user.get('username')
            if not verify_user_deletion(username):
                all_verified = False
                print(f"✗ User deletion verification failed for {username}")
        
        if all_verified:
            print("✓ All user deletions verified successfully")
        else:
            print("✗ Some user deletions failed verification")
            
        return result
    return None

def test_process():
    """Test the complete process:
    1. Create first user and delete it
    2. Create second user and reset namespaces
    3. Create third user and clean old users
    """
    print("\n=== Testing Complete Process ===")
    
    # Step 1: Create and delete first user
    print("\n1. Creating first user...")
    email1 = f"test1_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name1 = "Test User 1"
    user1_data = test_create_user(email1, full_name1)
    
    if user1_data:
        print("\nDeleting first user...")
        test_delete_user(email1, full_name1)
    
    # Step 2: Create second user and reset namespaces
    print("\n2. Creating second user...")
    email2 = f"test2_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name2 = "Test User 2"
    user2_data = test_create_user(email2, full_name2)
    
    if user2_data:
        print("\nResetting namespaces...")
        test_reset_namespaces()
    
    # Step 3: Create third user and clean old users
    print("\n3. Creating third user...")
    email3 = f"test3_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name3 = "Test User 3"
    user3_data = test_create_user(email3, full_name3)
    
    if user3_data:
        print("\nCleaning up old users...")
        test_cleanup_old_users()
    
    print("\n=== Process Completed ===")
    print("Created and deleted users:")
    print(f"1. {email1}")
    print(f"2. {email2}")
    print(f"3. {email3}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_api.py [create|delete|reset|cleanup|all|process]")
        print("For create/delete, provide email and full_name as additional arguments")
        return

    command = sys.argv[1].lower()

    if command == "create":
        if len(sys.argv) != 4:
            print("Usage: python test_api.py create <email> <full_name>")
            return
        test_create_user(sys.argv[2], sys.argv[3])

    elif command == "delete":
        if len(sys.argv) != 4:
            print("Usage: python test_api.py delete <email> <full_name>")
            return
        test_delete_user(sys.argv[2], sys.argv[3])

    elif command == "reset":
        test_reset_namespaces()

    elif command == "cleanup":
        test_cleanup_old_users()

    elif command == "all":
        # Test all operations
        print("\n=== Running All Tests ===")
        
        # Create a test user
        email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        full_name = "Test User"
        
        print("\n1. Creating test user...")
        user_data = test_create_user(email, full_name)
        
        if user_data:
            print("\n2. Resetting namespaces...")
            test_reset_namespaces()
            
            print("\n3. Cleaning up old users...")
            test_cleanup_old_users()
            
            print("\n4. Deleting test user...")
            test_delete_user(email, full_name)

    elif command == "process":
        test_process()
    else:
        print("Invalid command. Use: create, delete, reset, cleanup, all, or process")

if __name__ == "__main__":
    main() 