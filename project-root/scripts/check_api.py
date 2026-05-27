#!/usr/bin/env python3
import time
import urllib.request
import json

url = 'http://127.0.0.1:8000/health'
for i in range(30):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            data = json.load(r)
            print('UP', data)
            break
    except Exception as e:
        print('waiting for API...', i)
        time.sleep(1)
else:
    print('API did not become ready')
