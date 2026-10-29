import hashlib
import time
from .conftest import register


def test_empty_data_and_no_fake_ai(client):
    h,_=register(client)
    health=client.get('/api/health').json()
    assert 'connections' not in health
    assert client.get('/api/runtime').json()['interpretation_ready'] is False
    data=client.get('/api/data',headers=h).json()
    assert data['ready'] is False and data['rows']==0
    out=client.post('/api/interpret',headers=h,json={'text':'20 ma ke upar buy karo'}).json()
    assert out['status']=='connection_required' and out['strategy'] is None


def test_auth_sessions_and_account_isolation(client):
    h1,u1=register(client);h2,u2=register(client,'second@example.com')
    spec=client.get('/api/templates').json()['trend']
    sid=client.post('/api/strategies',headers=h1,json=spec).json()['id']
    assert len(client.get('/api/strategies',headers=h1).json())==1
    assert client.get('/api/strategies',headers=h2).json()==[]
    client.delete('/api/strategies/'+sid,headers=h2)
    assert len(client.get('/api/strategies',headers=h1).json())==1
    assert client.get('/api/strategies').status_code==401
    client.post('/api/auth/logout',headers=h1)
    assert client.get('/api/auth/me',headers=h1).status_code==401
    assert client.get('/api/auth/me',headers=h2).status_code==200


def test_credentials_are_hashed_and_reset_revokes_sessions(client):
    from app import store
    h,out=register(client)
    with store.db() as c:
        user=c.execute('SELECT * FROM users').fetchone()
        session=c.execute('SELECT * FROM sessions').fetchone()
    assert user['password']!='Test-only-password-123!'
    assert out['token']!=session['token_hash']
    assert out['recovery_code']!=user['recovery_hash']
    reset=client.post('/api/auth/recover',json={'email':'test@example.com','recovery_code':out['recovery_code'],'password':'Another-test-password-123!'})
    assert reset.status_code==200
    assert client.get('/api/auth/me',headers=h).status_code==401
    assert client.post('/api/auth/recover',json={'email':'test@example.com','recovery_code':out['recovery_code'],'password':'Another-test-password-123!'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'test@example.com','password':'Another-test-password-123!'}).status_code==200


def test_document_upload_is_private_and_text_only(client):
    h,_=register(client);h2,_=register(client,'second@example.com')
    doc=client.post('/api/attachments',headers=h,files={'file':('rules.txt',b'Use the previous highest close for a trailing stop; never look ahead.','text/plain')})
    assert doc.status_code==200
    aid=doc.json()['id']
    r=client.post('/api/interpret',headers=h2,json={'text':'Read the attached rules','attachment_ids':[aid]})
    assert r.status_code==404
    assert client.post('/api/attachments',headers=h,files={'file':('bad.exe',b'bad','application/octet-stream')}).status_code==422


def test_bad_password_and_rate_limit(client):
    assert client.post('/api/auth/signup',json={'name':'X','email':'x@example.com','password':'short'}).status_code==422
    for i in range(16):
        result=client.post('/api/auth/login',json={'email':'x@example.com','password':'wrong'})
    assert result.status_code==429


def test_end_to_end_backtest_job_and_private_report(client,prices,monkeypatch):
    from app import data
    monkeypatch.setenv('NIYAM_PRICE_BASIS','split_bonus_adjusted_ex_dividend')
    h,_=register(client);h2,_=register(client,'second@example.com')
    table=prices.reset_index();table['symbol']='TEST'
    table.to_csv(data.DATA/'prices'/'test.csv',index=False)
    prices[['close']].reset_index().to_csv(data.DATA/'benchmark'/'nifty.csv',index=False)
    spec=client.get('/api/templates').json()['trend']
    spec.update(symbols=['TEST'],start=str(prices.index[0].date()),end=str(prices.index[-1].date()),price_basis_confirmed=True)
    out=client.post('/api/jobs',headers=h,json={'strategy':spec})
    assert out.status_code==202,out.text
    jid=out.json()['id']
    deadline=time.time()+30
    while time.time()<deadline:
        report=client.get('/api/jobs/'+jid,headers=h).json()
        if report['state'] not in ['queued','running']:break
        time.sleep(.05)
    assert report['state']=='completed',report
    assert report['result']['metrics']['trades']>0
    assert client.get('/api/jobs/'+jid,headers=h2).status_code==404
    watched=client.post('/api/signals',headers=h,json=spec)
    assert watched.status_code==200,watched.text
    assert client.get('/api/signals',headers=h2).json()['watches']==[]
    assert client.get('/api/signals',headers=h).json()['alerts']==[]


def test_public_static_assets_and_security_headers(client):
    r=client.get('/')
    assert r.status_code==200
    assert 'Content-Security-Policy' in r.text
    assert client.get('/app.js').status_code==200
    assert client.get('/api/health').headers['cache-control']=='no-store'
    assert client.get('/.env').status_code==404
