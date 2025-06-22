# Quick test script
import requests

api_token = "E1OvSUYfQeIHTWivnKgB6luIIiopkcNa"
headers = {
    'Authorization': f'Token {api_token}',
    'Content-Type': 'application/json'
}

# Test listing fields from your SKU_Mappings table (this endpoint exists)
response = requests.get(
    'https://api.baserow.io/api/database/fields/table/581827/',
    headers=headers
)

print("Status:", response.status_code)
print("Fields info:", response.json())
