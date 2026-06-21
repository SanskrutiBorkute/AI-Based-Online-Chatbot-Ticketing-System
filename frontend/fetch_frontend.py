import urllib.request
import sys
url = 'http://localhost:5174/'
try:
    resp = urllib.request.urlopen(url, timeout=5)
    data = resp.read(1000).decode('utf-8', errors='ignore')
    print('OK', resp.status)
    print(data[:800])
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
