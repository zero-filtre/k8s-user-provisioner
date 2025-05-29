# k8s-user-provisioner
API for playground management on zerofiltre grafana instance and k8s cluster 

## How it works

### Creation

```shell
curl --location 'https://provisioner.zerofiltre.tech/provisioner' \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json' \
--data-raw '{
    "full_name":"username",
    "email":"email_address"
}'
```
This will create :
 - a k8s namespace named after `username`
 - a k8s user + password : get it from the response body
 - a grafana user + password, same as k8s credentials

### Deletion

```shell
curl --location 'https://provisioner.zerofiltre.tech/provisioner' \
--request DELETE \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json' \
--data-raw '{
    "full_name":"username",
    "email":"email_address"
}'
```
This will delete everything that has been created for that user.

### Reset Namespaces

```shell
curl --location 'https://provisioner.zerofiltre.tech/reset' \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json'
```
This will:
- Delete all resources in each namespace for provisioned users (except ResourceQuotas and RoleBindings)
- Keep the namespaces themselves intact
- Return statistics about the operation including:
  - Total users processed
  - Number of namespaces successfully reset
  - List of failed resets

### Cleanup Old Users

```shell
curl --location 'https://provisioner.zerofiltre.tech/cleanup' \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json'
```
This will:
- Find all users created more than a year ago
- Delete their namespaces, Grafana users, and Keycloak users
- Return statistics about the cleanup operation

### Sync Users

```shell
curl --location 'https://provisioner.zerofiltre.tech/sync' \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json'
```
This will:
- Check all provisioned users in Keycloak
- For each user:
  - Verify if they have a Grafana account
  - Verify if they have a Kubernetes namespace
  - Create missing Grafana accounts or namespaces as needed
- Return a detailed report including:
  - Total number of users checked
  - List of fixed users (with details of what was fixed)
  - List of failed fixes (with error messages)

## Automated Tasks

The following tasks are automated using Kubernetes CronJobs:

### Monthly Namespace Reset
- Runs at midnight on the first day of every month
- Resets all provisioned namespaces by removing all resources (except ResourceQuotas and RoleBindings)
- Ensures clean state for all users while preserving namespace structure

### Daily User Cleanup
- Runs at midnight every day
- Removes users and their resources that are more than a year old
- Helps maintain system cleanliness

## To start the app locally for testing purposes

### Install the virtual env

```
python -m venv .venv 
```

the .venv dir will be created à the root of the projetct

### Activate the virtual env 

At the root of the project 

* On windows
```
.venv\Scripts\activate
```

* On linux 
```
source .venv/bin/activate
```

### Start the app locally 

Create a file .env at the root of the project then fill it with the content [located here](https://vault.zerofiltre.tech/ui/vault/secrets/prod/show/zerofiltre-provisioner)  

✍🏼 You must have access to our vault !

Replace the xxx placeholders with the values located in the same dir in the vault.
Then:
```
 python run.py
```

## Testing

You can use the provided test script to test all endpoints:

```shell
# Test user creation
python test_api.py create <email> <full_name>

# Test user deletion
python test_api.py delete <email> <full_name>

# Test namespace reset
python test_api.py reset

# Test old users cleanup
python test_api.py cleanup

# Run complete test process
python test_api.py process
```