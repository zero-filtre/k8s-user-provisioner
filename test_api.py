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
    get_provisioned_users, get_grafana_user, check_namespace_exists, delete_grafana_user, delete_k8s_namespace
)

# Configuration

load_dotenv("/vault/secrets/config")
load_dotenv(".env")

BASE_URL = "http://localhost:8080"  # Change this to your API URL
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

def test_reset_namespaces(username):
    """Test namespace reset with verification for a specific username"""
    print(f"\n=== Testing Namespace Reset for {username} ===")
    url = f"{BASE_URL}/reset"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Reset specific namespace
    response = requests.post(url, headers=headers, json={'username': username})
    print_response(response)
    
    if response.status_code == 200:
        # Wait a bit for all systems to sync
        time.sleep(5)
        
        # Verify namespace reset for the specific user
        if verify_namespace_reset(username):
            print(f"✓ Namespace reset verified successfully for {username}")
            return True
        else:
            print(f"✗ Namespace reset verification failed for {username}")
    else:
        print("✗ Failed to reset specific namespace")
    
    return False

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
    4. Create fourth user and test sync
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
        test_reset_namespaces(user2_data.get('username'))
    
    # Step 3: Create third user and clean old users
    print("\n3. Creating third user...")
    email3 = f"test3_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name3 = "Test User 3"
    user3_data = test_create_user(email3, full_name3)
    
    if user3_data:
        print("\nCleaning up old users...")
        test_cleanup_old_users()
    
    # Step 4: Create fourth user and test sync
    print("\n4. Creating fourth user...")
    email4 = f"test4_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name4 = "Test User 4"
    user4_data = test_create_user(email4, full_name4)
    
    if user4_data:
        print("\nTesting sync...")
        test_sync_user()
    
    print("\n=== Process Completed ===")
    print("Created and deleted users:")
    print(f"1. {email1}")
    print(f"2. {email2}")
    print(f"3. {email3}")
    print(f"4. {email4}")

def test_sync_user():
    """Test user sync functionality by:
    1. Creating a user
    2. Deleting their Grafana account and K8s namespace
    3. Running sync for specific user
    4. Verifying recreation of Grafana account and K8s namespace
    """
    print("\n=== Testing User Sync ===")
    
    # Step 1: Create a test user
    email = f"test_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name = "Test Sync User"
    
    print("\n1. Creating test user...")
    user_data = test_create_user(email, full_name)
    
    if not user_data:
        print("✗ Failed to create test user")
        return False
        
    username = user_data.get('username')
    print(f"✓ Test user created: {username}")
    
    # Step 2: Delete Grafana account and K8s namespace
    print("\n2. Deleting Grafana account and K8s namespace...")
    
    # Delete Grafana user
    try:
        delete_grafana_user(username)
        print("✓ Grafana account deleted")
    except Exception as e:
        print(f"✗ Failed to delete Grafana account: {e}")
        return False
    
    # Delete K8s namespace
    try:
        delete_k8s_namespace(username)
        print("✓ K8s namespace deleted")
    except Exception as e:
        print(f"✗ Failed to delete K8s namespace: {e}")
        return False
    
    # Step 3: Run sync for specific user
    print("\n3. Running sync for specific user...")
    url = f"{BASE_URL}/sync"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json={'username': username})
    print_response(response)
    
    if response.status_code != 200:
        print("✗ Sync failed")
        return False
    
    # Wait a bit for all systems to sync
    time.sleep(5)
    
    # Step 4: Verify recreation
    print("\n4. Verifying recreation...")
    
    # Verify Grafana user recreation
    try:
        grafana_user = get_grafana_user(username)
        if grafana_user:
            print("✓ Grafana account recreated")
        else:
            print("✗ Grafana account not recreated")
            return False
    except Exception as e:
        print(f"✗ Failed to verify Grafana account: {e}")
        return False
    
    # Verify K8s namespace recreation
    if check_namespace_exists(username):
        print("✓ K8s namespace recreated")
    else:
        print("✗ K8s namespace not recreated")
        return False
    
    print("\n✓ Sync test completed successfully")
    return True

def test_user_lifecycle():
    """Test the complete user lifecycle:
    1. Create user and verify in all systems
    2. Reset namespace and verify configmap deletion
    3. Delete Grafana and K8s resources, then sync and verify recreation
    4. Delete user and verify complete removal
    """
    print("\n=== Testing User Lifecycle ===")
    results = {
        'creation': {'success': False, 'details': {}},
        'reset': {'success': False, 'details': {}},
        'sync': {'success': False, 'details': {}},
        'deletion': {'success': False, 'details': {}}
    }
    
    # Step 1: Create user
    print("\n1. Creating test user...")
    email = f"test_lifecycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    full_name = "Test Lifecycle User"
    
    user_data = test_create_user(email, full_name)
    if not user_data:
        print("✗ Failed to create test user")
        return results
    
    username = user_data.get('username')
    print(f"✓ Test user created: {username}")
    
    # Verify creation in all systems
    print("\nVerifying user creation in all systems...")
    if verify_user_creation(username, email):
        print("✓ User verified in all systems")
        results['creation']['success'] = True
        results['creation']['details'] = {
            'username': username,
            'email': email
        }
    else:
        print("✗ User verification failed")
        return results
    
    # Step 2: Reset namespace
    print("\n2. Resetting namespace...")
    if test_reset_namespaces(username):
        print("✓ Namespace reset successful")
        results['reset']['success'] = True
        results['reset']['details'] = {
            'username': username
        }
    else:
        print("✗ Namespace reset failed")
        return results
    
    # Step 3: Delete Grafana and K8s resources, then sync
    print("\n3. Testing sync functionality...")
    
    # Delete Grafana user and K8s namespace
    try:
        delete_grafana_user(username)
        delete_k8s_namespace(username)
        time.sleep(10)
        print("✓ Resources deleted for sync test")
    except Exception as e:
        print(f"✗ Failed to delete resources: {e}")
        return results
    
    # Run sync
    url = f"{BASE_URL}/sync"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json={'username': username})
    print_response(response)
    
    if response.status_code != 200:
        print("✗ Sync failed")
        return results
    
    # Wait for sync to complete
    time.sleep(5)
    
    # Verify sync results
    try:
        grafana_user = get_grafana_user(username)
        namespace_exists = check_namespace_exists(username)
        
        if grafana_user and namespace_exists:
            print("✓ Resources recreated successfully")
            results['sync']['success'] = True
            results['sync']['details'] = {
                'username': username,
                'grafana_recreated': True,
                'namespace_recreated': True
            }
        else:
            print("✗ Resources not properly recreated")
            return results
    except Exception as e:
        print(f"✗ Failed to verify sync results: {e}")
        return results
    
    # Step 4: Delete user
    print("\n4. Deleting user...")
    if test_delete_user(email, full_name):
        print("✓ User deletion successful")
        results['deletion']['success'] = True
        results['deletion']['details'] = {
            'username': username,
            'email': email
        }
    else:
        print("✗ User deletion failed")
        return results
    
    # Print final report
    print("\n=== Test Results ===")
    print(f"1. User Creation: {'✓' if results['creation']['success'] else '✗'}")
    print(f"   - Username: {results['creation']['details'].get('username')}")
    print(f"   - Email: {results['creation']['details'].get('email')}")
    
    print(f"\n2. Namespace Reset: {'✓' if results['reset']['success'] else '✗'}")
    print(f"   - Username: {results['reset']['details'].get('username')}")
    
    print(f"\n3. Sync Test: {'✓' if results['sync']['success'] else '✗'}")
    print(f"   - Username: {results['sync']['details'].get('username')}")
    print(f"   - Grafana Recreated: {results['sync']['details'].get('grafana_recreated')}")
    print(f"   - Namespace Recreated: {results['sync']['details'].get('namespace_recreated')}")
    
    print(f"\n4. User Deletion: {'✓' if results['deletion']['success'] else '✗'}")
    print(f"   - Username: {results['deletion']['details'].get('username')}")
    print(f"   - Email: {results['deletion']['details'].get('email')}")
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_api.py [create|delete|reset|cleanup|all|process|sync|lifecycle]")
        print("For create/delete, provide email and full_name as additional arguments")
        print("For reset, provide username as additional argument")
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
        if len(sys.argv) != 3:
            print("Usage: python test_api.py reset <username>")
            return
        test_reset_namespaces(sys.argv[2])

    elif command == "cleanup":
        test_cleanup_old_users()

    elif command == "sync":
        test_sync_user()

    elif command == "lifecycle":
        test_user_lifecycle()

    elif command == "all":
        # Test all operations
        print("\n=== Running All Tests ===")
        test_user_lifecycle()

    elif command == "process":
        test_process()
    else:
        print("Invalid command. Use: create, delete, reset, cleanup, all, process, sync, or lifecycle")

if __name__ == "__main__":
    main() 