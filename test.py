import requests

url = 'http://127.0.0.1:5000/aprovisionner'
headers = {
    'Authorization': 'your_expected_token',
    'Content-Type': 'application/json'
}
data = {
    'email': 'example@email.com'
}

response = requests.post(url, headers=headers, json=data)

print(response.status_code)
print(response.json())
