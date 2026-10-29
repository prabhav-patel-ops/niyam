"""Verify production cookies and research THROUGH the real TLS proxy in CI."""
import concurrent.futures
import csv
import http.cookiejar
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request

BASE='https://niyam.test'
PASSWORD='Synthetic-deployment-test-123!'


def request(opener,path,body=None,method=None,headers=None):
    headers={'Content-Type':'application/json',**(headers or {})}
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,method=method,headers=headers)
    try:
        with opener.open(req,timeout=60) as response:
            content=response.read()
            return response.status,response.headers,json.loads(content) if response.headers.get_content_type()=='application/json' else content
    except urllib.error.HTTPError as error:
        return error.code,error.headers,json.loads(error.read())


def main():
    context=ssl.create_default_context(cafile=os.environ['NIYAM_TEST_CA'])
    def new_client():
        cookies=http.cookiejar.CookieJar()
        return urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(cookies))
    client=new_client()
    status,_,state=request(client,'/api/runtime')
    assert status==200 and state['research_ready'] and not state['interpretation_ready']
    status,headers,_=request(client,'/api/auth/signup',{'name':'Deployment fixture','email':'tls@example.com','password':PASSWORD})
    assert status==200
    cookie=headers['Set-Cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=strict' in cookie
    assert headers['Strict-Transport-Security']=='max-age=31536000'
    assert request(client,'/api/auth/me')[0]==200
    assert request(new_client(),'/api/auth/me')[0]==401
    assert request(client,'/api/auth/logout',{},headers={'Origin':'https://other.example'})[0]==403
    _,_,templates=request(client,'/api/templates')
    strategy=templates['trend'];strategy.update(symbols=['TEST'],start='2020-01-01',end='2021-02-23')
    status,_,job=request(client,'/api/jobs',{'strategy':strategy})
    assert status==202
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        _,_,result=request(client,'/api/jobs/'+job['id'])
        if result['state'] not in {'queued','running'}:break
        time.sleep(.2)
    assert result['state']=='completed',result
    assert result['result']['metrics']['trades']>0
    assert request(new_client(),'/api/jobs/'+job['id'])[0]==401
    # A modest parallel read workload proves sessions/proxy routing remain stable.
    started=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        statuses=list(pool.map(lambda _:request(new_client(),'/api/health')[0],range(32)))
    assert statuses==[200]*32
    print(json.dumps({'tls_proxy':True,'secure_cookie_session':True,'account_isolation':True,'real_backtest':True,'synthetic_data':True,'parallel_health_requests':32,'concurrency':8,'elapsed_seconds':round(time.monotonic()-started,3)}))
    assert request(client,'/api/auth/logout',{},headers={'Origin':BASE})[0]==200
    assert request(client,'/api/auth/me')[0]==401


def data_fixture():
    import math
    from datetime import date,timedelta
    dates=[];day=date(2020,1,1)
    while len(dates)<300:
        if day.weekday()<5:dates.append(day)
        day+=timedelta(days=1)
    for folder in ['prices','benchmark','fundamentals']:Path('data',folder).mkdir(parents=True,exist_ok=True)
    with open('data/prices/ci-test.csv','w',newline='') as prices,open('data/benchmark/ci-test.csv','w',newline='') as benchmark:
        pw=csv.writer(prices);bw=csv.writer(benchmark)
        pw.writerow(['date','symbol','open','high','low','close','volume']);bw.writerow(['date','close'])
        for i,day in enumerate(dates):
            close=100+i*.06+12*math.sin(i/11)
            pw.writerow([day,'TEST',close-.1,close+1,close-1,close,100000]);bw.writerow([day,close])


if __name__=='__main__':
    import sys
    if '--prepare-data' in sys.argv:data_fixture()
    else:main()
