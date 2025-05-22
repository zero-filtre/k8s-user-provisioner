import os
from dotenv import load_dotenv
from keycloak import KeycloakAdmin
import sys

# Load environment variables
load_dotenv("/vault/secrets/config")
load_dotenv(".env")

def get_keycloak_admin():
    """Initialize and return KeycloakAdmin instance"""
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

def migrate_users():
    """Main function to migrate users"""
    try:
        # Initialize Keycloak admin client
        keycloak_admin = get_keycloak_admin()
        
        # Get all users
        users = keycloak_admin.get_users()
        
        print(f"\nFound {len(users)} users in Keycloak")
        print("\nStarting migration process...")
        
        migrated = 0
        skipped = 0
        
        for user in users:
            username = user.get('username')
            email = user.get('email')
            attributes = user.get('attributes', {})
            
            # Skip users that already have the tag
            if attributes.get('managed-by') == ['k8s-provisioner']:
                print(f"\nSkipping {username} (already tagged)")
                skipped += 1
                continue
            
            print(f"\nUser: {username}")
            print(f"Email: {email}")
            print(f"Current attributes: {attributes}")
            
            while True:
                response = input("Apply managed-by:k8s-provisioner tag? (y/n/q to quit): ").lower()
                if response in ['y', 'n', 'q']:
                    break
                print("Please enter 'y', 'n', or 'q'")
            
            if response == 'q':
                print("\nMigration stopped by user")
                break
            elif response == 'y':
                # Update user attributes
                if not attributes:
                    attributes = {}
                attributes['managed-by'] = ['k8s-provisioner']
                attributes['provisioned'] = ['true']
                
                # Update user in Keycloak
                keycloak_admin.update_user(
                    user_id=user['id'],
                    payload={'attributes': attributes}
                )
                print(f"✓ Tagged user: {username}")
                migrated += 1
            else:
                print(f"Skipped user: {username}")
                skipped += 1
        
        print("\nMigration Summary:")
        print(f"Total users processed: {len(users)}")
        print(f"Users migrated: {migrated}")
        print(f"Users skipped: {skipped}")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_users() 