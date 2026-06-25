import requests
import json

url='http://127.0.0.1:8000/api/datasources/connect'
payload={"name":"local_sqlite","db_type":"sqlite","host":"","port":0,"db_name":"dev.db","username":"","password":""}
try:
    r=requests.post(url,json=payload,timeout=10)
    print('STATUS',r.status_code)
    print(r.text)
except Exception as e:
    print('EXC',e)
