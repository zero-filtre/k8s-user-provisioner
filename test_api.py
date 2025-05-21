import requests
import json
import sys
from datetime import datetime
import time
import os

# Configuration

load_dotenv("/vault/secrets/config")
load_dotenv(".env")

BASE_URL = "http://127.0.0.1:8000"  # Change this to your API URL
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

def test_create_user(email, full_name):
    """Test user creation"""
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
    return response.json() if response.status_code == 200 else None

def test_delete_user(email, full_name):
    """Test user deletion"""
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
    return response.json() if response.status_code == 200 else None

def test_reset_namespaces():
    """Test namespace reset"""
    print("\n=== Testing Namespace Reset ===")
    url = f"{BASE_URL}/reset"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers)
    print_response(response)
    return response.json() if response.status_code == 200 else None

def test_cleanup_old_users():
    """Test cleanup of old users"""
    print("\n=== Testing Old Users Cleanup ===")
    url = f"{BASE_URL}/cleanup"
    headers = {
        'Authorization': TOKEN,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers)
    print_response(response)
    return response.json() if response.status_code == 200 else None

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