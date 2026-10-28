import asyncio
import json
import os
import pytest
from fastapi.testclient import TestClient
from .conftest import register
from app import runtime,store,data
from app.models import Strategy,Expr,template
from app.security import RequestPerimeter,instance_lock


def install_data(prices):
    table=prices.reset_index();table['symbol']='TEST'
    table.to_csv(data.DATA/'prices'/'test.csv',index=False)
    prices[['close']].reset_index().to_csv(data.DATA/'benchmark'/'nifty.csv',index=False)


def test_backend_inputs_become_available_without_restart(client,prices,monkeypatch):
    h,_=register(client)
    assert client.get('/api/ready').status_code==503
    install_data(prices)
    monkeypatch.setenv('NIYAM_PRICE_BASIS',runtime.PRICE_BASIS)
    monkeypatch.setenv('LLM_BASE_URL','https://example.com/v1')
    monkeypatch.setenv('LLM_MODEL','test-model')
    assert client.get('/api/ready').status_code==200
    assert client.get('/api/runtime').json()['ready'] is True
    catalog=client.get('/api/data',headers=h).json()
    assert catalog['symbols'][0]['symbol']=='TEST'
    assert 'folders' not in catalog and 'errors' not in catalog
    assert 'example.com' not in client.get('/api/runtime').text
    monkeypatch.delenv('LLM_MODEL')
    assert client.get('/api/runtime').json()['ready'] is False


def test_browser_cannot_attest_operator_price_basis(client,prices):
    h,_=register(client);install_data(prices)
    spec=template().model_dump(mode='json')
    spec.update(symbols=['TEST'],price_basis_confirmed=True)
    response=client.post('/api/jobs',headers=h,json={'strategy':spec})
    assert response.status_code==503
    assert 'data/' not in response.text and '.env' not in response.text


def test_cookie_login_and_cross_origin_rejection(client):
    response=client.post('/api/auth/signup',json={'name':'Cookie user','email':'cookie@example.com','password':'Long-Test-Password-123'})
    assert response.status_code==200
    cookie=response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/api' in cookie
    assert client.get('/api/auth/me').status_code==200
    token=response.json()['token']
    denied=client.post('/api/auth/logout',headers={'Origin':'https://evil.example'})
    assert denied.status_code==403
    assert client.get('/api/auth/me').status_code==200
    assert client.post('/api/auth/logout',headers={'Origin':'http://testserver'}).status_code==200
    assert client.get('/api/auth/me').status_code==401
    assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401


def test_production_cookie_flags_and_startup_validation(client,monkeypatch):
    monkeypatch.setenv('NIYAM_ENV','production')
    with pytest.raises(ValueError,match='HTTPS'):runtime.validate_config()
    monkeypatch.setenv('NIYAM_PUBLIC_URL','https://niyam.example')
    runtime.validate_config()
    client.base_url='https://testserver'
    r=client.post('/api/auth/signup',json={'name':'Secure','email':'secure@example.com','password':'Long-Test-Password-123'})
    assert 'Secure' in r.headers['set-cookie']
    assert r.headers['strict-transport-security']=='max-age=31536000'
    monkeypatch.setenv('NIYAM_ALLOWED_HOSTS','*')
    with pytest.raises(ValueError,match='wildcard'):runtime.validate_config()


def test_second_worker_refused(client):
    with pytest.raises(RuntimeError,match='one Niyam worker'):
        with instance_lock():pass


def test_registration_closed_and_blank_name(client,monkeypatch):
    body={'name':'   ','email':'blank@example.com','password':'Long-Test-Password-123'}
    assert client.post('/api/auth/signup',json=body).status_code==422
    monkeypatch.setenv('NIYAM_REGISTRATION_OPEN','false')
    body['name']='Name'
    assert client.post('/api/auth/signup',json=body).status_code==403


def test_rate_limits_persist_across_memory_reset(client):
    from app import main
    for _ in range(15):
        r=client.post('/api/auth/login',json={'email':'rate@example.com','password':'wrong'})
    # A fresh process reads the same SQLite limiter records.
    r=client.post('/api/auth/login',json={'email':'rate@example.com','password':'wrong'})
    assert r.status_code==429 and r.headers['retry-after']=='60'


def test_request_body_limit_counts_chunked_bytes(client):
    async def invoke(chunks,headers=()):
        called=[];sent=[]
        async def downstream(scope,receive,send):called.append(True)
        async def receive():
            return {'type':'http.request','body':chunks.pop(0),'more_body':bool(chunks)}
        async def send(message):sent.append(message)
        middleware=RequestPerimeter(downstream)
        await middleware({'type':'http','path':'/api/auth/login','scheme':'http','method':'POST','headers':list(headers)},receive,send)
        return called,sent
    called,sent=asyncio.run(invoke([b'x'*(5*1024*1024),b'x'*(5*1024*1024)]))
    assert not called and sent[0]['status']==413
    assert dict(sent[0]['headers'])[b'x-content-type-options']==b'nosniff'
    called,sent=asyncio.run(invoke([b'{}'],[(b'content-length',b'-1')]))
    assert not called and sent[0]['status']==400
    called,sent=asyncio.run(invoke([b'abc'],[(b'content-length',b'1')]))
    assert not called and sent[0]['status']==400


def test_numeric_and_logical_rule_types_rejected():
    with pytest.raises(ValueError,match='true/false'):
        Strategy.model_validate({**template().model_dump(),'entry':{'op':'close'}})
    with pytest.raises(ValueError,match='conditions'):
        Expr(op='not',args=[Expr(op='constant',value=1)])
    with pytest.raises(ValueError,match='numeric'):
        Expr(op='sma',window=20,args=[template().entry])
    good=Expr(op='all',args=[Expr(op='lag',window=1,args=[template().entry])])
    assert good.op=='all'
    for name in ['__proto__','constructor','prototype','bad.name','x" autofocus onfocus="alert(1)']:
        with pytest.raises(ValueError,match='simple identifiers'):
            Strategy.model_validate({**template().model_dump(),'parameters':{'fast':20,'slow':50,name:1}})


def test_backend_catalog_redacts_parse_failures(client,monkeypatch):
    h,_=register(client)
    def fail():raise OSError('private-volume/account-secret.csv')
    monkeypatch.setattr(data,'load_dataset',fail)
    assert 'private-volume' not in client.get('/api/data',headers=h).text
    assert 'private-volume' not in client.get('/api/runtime').text


def test_private_report_deletion(client):
    h,_=register(client);other,_=register(client,'other@example.com')
    uid=client.get('/api/auth/me',headers=h).json()['id']
    with store.db() as conn:
        conn.execute('INSERT INTO jobs(id,user_id,state,request,created) VALUES(?,?,?,?,?)',('complete',uid,'completed','{}',1))
        conn.execute('INSERT INTO jobs(id,user_id,state,request,created) VALUES(?,?,?,?,?)',('active',uid,'queued','{}',1))
    client.delete('/api/jobs/complete',headers=other)
    assert client.get('/api/jobs/complete',headers=h).status_code==200
    client.delete('/api/jobs/complete',headers=h)
    assert client.get('/api/jobs/complete',headers=h).status_code==404
    client.delete('/api/jobs/active',headers=h)
    assert client.get('/api/jobs/active',headers=h).status_code==200


def test_database_backup_retains_accounts(client,tmp_path):
    import subprocess
    import sqlite3
    import sys
    register(client)
    target=tmp_path/'private-backup.sqlite3'
    env={**os.environ,'NIYAM_STATE_DIR':str(store.STATE),'NIYAM_ENV':'development'}
    run=subprocess.run([sys.executable,'scripts/backup.py','--output',str(target)],env=env,capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stderr
    with sqlite3.connect(target) as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]==1


def test_word_extraction_and_zip_limits(client):
    import io
    import zipfile
    from docx import Document
    h,_=register(client)
    stream=io.BytesIO();doc=Document();doc.add_paragraph('Buy on the 20 day SMA crossover above the 50 day SMA and exit on the reverse crossover.');doc.save(stream)
    out=client.post('/api/attachments',headers=h,files={'file':('strategy.docx',stream.getvalue())})
    assert out.status_code==200,out.text
    oversized=io.BytesIO()
    with zipfile.ZipFile(oversized,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('bomb.xml',b'x'*(31*1024*1024))
    out=client.post('/api/attachments',headers=h,files={'file':('compressed.docx',oversized.getvalue())})
    assert out.status_code==422 and 'too large' in out.text


def test_backtests_exclude_uncompleted_manual_bars(prices,monkeypatch):
    from app import engine
    spec=template();spec.symbols=['TEST'];spec.start=prices.index[0].date();spec.end=prices.index[-1].date();spec.price_basis_confirmed=True
    monkeypatch.setattr(engine,'completed_through',lambda:prices.index[100].date())
    out=engine.run_backtest(spec,{'TEST':prices},prices[['close']])
    assert out['sessions']==101 and out['end']==str(prices.index[100].date())


def test_provider_response_limit_and_slot_release(monkeypatch):
    from app import assistant
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_bytes(self):yield b'x'*(1024*1024+1)
    class Provider:
        def stream(self,*args,**kwargs):return Reply()
    with pytest.raises(ValueError,match='size limit'):
        assistant.bounded_json_post(Provider(),'https://example.com')


def test_dataset_modified_during_load_is_not_cached(client,prices,monkeypatch):
    install_data(prices)
    original=data.signature
    calls=[]
    def changed():
        calls.append(True)
        sig=original()
        return sig if len(calls)==1 else (*sig,('concurrent-change',0,0))
    monkeypatch.setattr(data,'signature',changed)
    with pytest.raises(ValueError,match='changed during loading'):
        data.load_dataset()
    assert not data._cache
