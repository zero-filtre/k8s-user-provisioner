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
curl --location 'https://provisioner.zerofiltre.tech/provisioner/clean' \
--header 'Authorization: <token>' \
--header 'Content-Type: application/json' \
--data-raw '{
  "username":"username"
}'
```
This will delete everything that has been created for that user.



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

Create a file .env at the root of the project then fill it with the content [located here](https://vault.zerofiltre.tech/ui/vault/secrets/dev/show/zerofiltre-approvisionner)
✍🏼 You must have access to our vault !

Replace the xxx placeholders with the values located in the same dir in the vault.
Then:
```
 python run.py
```