import tempfile,json
from pathlib import Path
from unittest.mock import patch,Mock
import app as m
from easyscholar import normalize
m.DATA=Path(tempfile.mkdtemp(prefix='pawsec-easy-'));m.app.before_request_funcs[None]=[]
c=m.app.test_client();assert c.get('/api/easyscholar/config').json['configured']==False
assert c.post('/api/easyscholar/query',json={'venue':'Test Journal'}).status_code==400
assert c.post('/api/easyscholar/config',json={'key':'test-secret'}).json=={'configured':True,'key_url':'https://www.easyscholar.cc/console/user/open'}
assert b'test-secret' not in (m.DATA/'easyscholar.enc').read_bytes()
data={'officialRank':{'all':{'ccf':'A','sci':'Q1','sciif':'7.2','sciUp':'1'}},'customRank':{'rankInfo':[{'uuid':'1','abbName':'Lab','threeRankText':'B'}],'rank':['1&&&3']}}
r=Mock(status_code=200);r.json.return_value={'code':200,'data':data}
with patch('easyscholar.requests.get',return_value=r) as get:
 out=c.post('/api/easyscholar/query',json={'venue':'A & B'});assert out.status_code==200;assert len(out.json['entries'])==5;assert out.json['data_year'] is None
 assert get.call_args.kwargs['params']['publicationName']=='A & B'
 assert c.post('/api/easyscholar/query',json={'venue':'A & B'}).json['cached'];assert get.call_count==1
 pid='a'*32;(m.DATA/pid).mkdir();m.put({'id':pid,'publication':{'venue':'A & B'}})
 assert c.post('/api/papers/'+pid+'/easyscholar',json={}).status_code==200
 assert c.get('/api/papers/'+pid+'/easyscholar').json['result']['entries'][0]['field']=='ccf'
 r.json.return_value={'code':40002,'msg':'test-secret'}
 bad=c.post('/api/easyscholar/query',json={'venue':'Another'});assert bad.status_code==400;assert 'test-secret' not in bad.text
assert normalize({'officialRank':{'all':{}}})==[]
c.post('/api/easyscholar/config',json={'clear':True});assert not c.get('/api/easyscholar/config').json['configured']
print('PASS: key encryption/redaction, missing key, official/custom fields, cache, paper persistence, error redaction, empty data, key removal')