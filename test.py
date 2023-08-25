import requests, os

url = 'http://127.0.0.1:5000/aprovisionner'
headers = {
    'Authorization': os.environ.get('VERIFICATION_TOKEN'),
    'Content-Type': 'application/json'
}
data = {
    'email': 'toto@email.com'
}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
print(response.json())
