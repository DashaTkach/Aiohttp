import requests

response = requests.patch("http://127.0.0.1:8080/ann/4",
                          json={"description": "new description"},
                          )

response = requests.get(
    "http://127.0.0.1:8080/ann/1",
)

print(response.status_code)
print(response.text)
