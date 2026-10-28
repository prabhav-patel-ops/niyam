"""Isolated synthetic fixture for browser tests. Never use as a deployment server."""
from pathlib import Path
import os
import sys
import threading
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def start():
    base=Path(os.environ['NIYAM_BROWSER_FIXTURE']).resolve()
    base.mkdir(parents=True,exist_ok=True)
    os.environ.update(NIYAM_ENV='development',NIYAM_STATE_DIR=str(base/'state'),NIYAM_DATA_DIR=str(base/'data'),
                      NIYAM_PRICE_BASIS='split_bonus_adjusted_ex_dividend',LLM_BASE_URL='http://127.0.0.1:8178/v1',LLM_MODEL='synthetic-fixture')
    os.environ.pop('NIYAM_PUBLIC_URL',None)
    import numpy as np
    import pandas as pd
    dates=pd.bdate_range('2020-01-01',periods=300)
    close=100+np.arange(300)*.06+12*np.sin(np.arange(300)/11)
    for folder in ['prices','benchmark','fundamentals']:(base/'data'/folder).mkdir(parents=True,exist_ok=True)
    pd.DataFrame({'date':dates,'symbol':'TEST','open':close-.1,'high':close+1,'low':close-1,'close':close,'volume':100000}).to_csv(base/'data/prices/test.csv',index=False)
    pd.DataFrame({'date':dates,'close':close}).to_csv(base/'data/benchmark/nifty.csv',index=False)
    from app.models import template
    class Model(BaseHTTPRequestHandler):
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            context=json.loads(body['messages'][1]['content'])
            spec=template().model_dump(mode='json')
            spec.update({k:context['defaults'][k] for k in ['symbols','start','end','price_basis_confirmed'] if k in context['defaults']})
            payload={'choices':[{'message':{'content':json.dumps({'status':'ready','summary':'Synthetic fixture: 20/50 SMA crossover with a fixed 5% stop.','strategy':spec})}}]}
            data=json.dumps(payload).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def log_message(self,*args):pass
    provider=ThreadingHTTPServer(('127.0.0.1',8178),Model)
    threading.Thread(target=provider.serve_forever,daemon=True).start()
    from app.main import app
    import uvicorn
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8177,log_level='warning'))
    from fastapi import Request,HTTPException
    @app.post('/__test__/stop')
    def stop(request:Request):
        if request.headers.get('x-test-token')!=os.environ['NIYAM_TEST_STOP_TOKEN']:
            raise HTTPException(403)
        server.should_exit=True
        return {'ok':True}
    # Test-only route must precede the static mount.
    app.router.routes.insert(0,app.router.routes.pop())
    try:server.run()
    finally:provider.shutdown();provider.server_close()

if __name__=='__main__':start()
