import requests, os

url = 'https://approvisionner-dev.zerofiltre.tech/approvisionner'
headers = {
    'Authorization': "zxj,flh344,34xoaxoxaa",
    'Content-Type': 'application/json'
}
data = {
    'email': '@email.com'
}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
print(response.json())
