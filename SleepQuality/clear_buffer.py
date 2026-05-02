import requests

print('=== Clearing Sleep Buffer ===')

# Clear buffer
resp = requests.post('http://localhost:3001/api/clear-buffer')
print(f'Clear buffer: {resp.status_code}')
print(f'Response: {resp.json()}')

print('\nDone!')
