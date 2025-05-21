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
- Delete all existing namespaces for provisioned users
- Recreate namespaces for all provisioned users
- Return statistics about the operation

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

## Automated Tasks

The following tasks are automated using Kubernetes CronJobs:

### Monthly Namespace Reset
- Runs at midnight on the first day of every month
- Resets all provisioned namespaces
- Ensures clean state for all users

### Yearly User Cleanup
- Runs at midnight on December 31st
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