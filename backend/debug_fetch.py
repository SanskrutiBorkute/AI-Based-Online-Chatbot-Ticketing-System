import urllib.request
from urllib.error import HTTPError
try:
    resp = urllib.request.urlopen('http://127.0.0.1:5000/api/analytics/data')
    print(resp.read().decode())
except HTTPError as e:
    print('HTTPError', e.code)
    try:
        print(e.read().decode())
    except Exception as ex:
        print('no body', ex)
except Exception as ex:
    print('EX', ex)
