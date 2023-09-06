import requests, os

url = 'https://provisioner-dev.zerofiltre.tech/provisioner'
headers = {
    'Authorization': "zxj,flh344,34xoaxoxa",
    'Content-Type': 'application/json'
}
data = {
    'email': 'jonathan777@email.com',
}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
print(response.json())
