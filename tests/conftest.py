from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def prices():
    dates=pd.bdate_range('2020-01-01',periods=300)
    close=100+np.arange(300)*.06+12*np.sin(np.arange(300)/11)
    return pd.DataFrame({'open':close-.1,'high':close+1,'low':close-1,'close':close,'volume':100000},index=pd.DatetimeIndex(dates,name='date'))

@pytest.fixture
def client(tmp_path,monkeypatch):
    from app import data,store,main
    monkeypatch.setattr(data,'DATA',tmp_path/'data')
    monkeypatch.setattr(store,'STATE',tmp_path/'state')
    for kind in ["prices","benchmark","fundamentals"]:
        data.files_for(kind)
    data._cache.clear()
    main.rate.clear()
    for key in ['LLM_BASE_URL','LLM_MODEL','LLM_API_KEY','TAVILY_API_KEY','DAILY_FEED_URL','DAILY_FEED_API_KEY']:
        monkeypatch.delenv(key,raising=False)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


def register(client,email='test@example.com'):
    response=client.post('/api/auth/signup',json={'name':'Test account','email':email,'password':'Test-only-password-123!'})
    assert response.status_code==200,response.text
    out=response.json()
    return {'Authorization':'Bearer '+out['token']},out
