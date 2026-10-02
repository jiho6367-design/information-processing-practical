"""Independently execute the anticipated code and check network calculations."""
from pathlib import Path
import ipaddress
import json
import re
import sqlite3
import subprocess
import sys
from collections import deque
import heapq

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'study-materials/exam-guide/data'
TMP=ROOT/'tmp/exam-analysis/prediction-checks'
TMP.mkdir(parents=True,exist_ok=True)
results=[]
def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert p.returncode==0,p.stderr
    return p.stdout.strip()
for q in json.loads((DATA/'predictions.json').read_text(encoding='utf-8')):
    language=q['language'];folder=TMP/q['id'];folder.mkdir(exist_ok=True)
    if language=='네트워크':
        v=q.get('verification')
        if v is None:
            results.append({'id':q['id'],'status':'manual-check-required'});continue
        if v['type']=='subnet':
            net=ipaddress.ip_network(f'{v["ip"]}/{v["prefix"]}',strict=False)
            actual={'network':str(net.network_address),'broadcast':str(net.broadcast_address),'hosts':net.num_addresses-2 if net.prefixlen<31 else net.num_addresses,'first':str(net.network_address+1 if net.prefixlen<31 else net.network_address),'last':str(net.broadcast_address-1 if net.prefixlen<31 else net.broadcast_address)}
            for k,value in v['expected'].items():assert actual[k]==value,(q['id'],k,actual,value)
            if v.get('candidates'):
                chosen=[c['label'] for c in v['candidates'] if ipaddress.ip_address(c['ip']) in net and c['ip'] not in [str(net.network_address),str(net.broadcast_address)]]
                assert chosen==v['expected_selected'],q['id']
            if v.get('required_hosts'):
                assert actual['hosts']>=v['required_hosts'] and 2**(31-v['prefix'])-2<v['required_hosts'],q['id']
                assert 2**(v['prefix']-v['base_prefix'])==v['expected_subnet_count'],q['id']
        elif v['type']=='subnets':
            for item in v['items']:
                net=ipaddress.ip_network(f'{item["ip"]}/{item["prefix"]}',strict=False)
                actual={'network':str(net.network_address),'broadcast':str(net.broadcast_address),'hosts':net.num_addresses-2,'first':str(net.network_address+1),'last':str(net.broadcast_address-1)}
                for k,value in item['expected'].items():assert actual[k]==value,(q['id'],k,actual,value)
            if v.get('expected_count'):
                networks=list(ipaddress.ip_network(v['base']).subnets(new_prefix=v['new_prefix']))
                assert len(networks)==v['expected_count']==len(v['items']),q['id']
                assert 2**(v['new_prefix']-ipaddress.ip_network(v['base']).prefixlen-1)<v['minimum_subnets']<=len(networks),q['id']
            if v.get('expected_assignment'):
                for port,index in v['port_to_subnet'].items():
                    item=v['items'][index];net=ipaddress.ip_network(f'{item["ip"]}/{item["prefix"]}',strict=False)
                    choices=[ip for ip in v['candidates'] if ipaddress.ip_address(ip) in net and ip not in [str(net.network_address),str(net.broadcast_address)]]
                    assert choices==[v['expected_assignment'][port]],q['id']
        elif v['type']=='routes':
            adj={n:[] for n in v['nodes']}
            for a,b,w in v['edges']:adj[a].append((b,w));adj[b].append((a,w))
            distances={v['start']:0};queue=deque([v['start']])
            while queue:
                a=queue.popleft()
                for b,w in adj[a]:
                    if b not in distances:distances[b]=distances[a]+1;queue.append(b)
            costs={v['start']:0};pq=[(0,v['start'])]
            while pq:
                cost,a=heapq.heappop(pq)
                if cost!=costs[a]:continue
                for b,w in adj[a]:
                    if cost+w<costs.get(b,float('inf')):costs[b]=cost+w;heapq.heappush(pq,(cost+w,b))
            assert distances[v['end']]==v['expected_hops'],q['id']
            assert costs[v['end']]==v['expected_cost'],q['id']
        else:raise ValueError((q['id'],v['type']))
        results.append({'id':q['id'],'status':'pass','language':language,'method':'Python ipaddress / graph algorithm'});continue
    code=q['code']
    if language=='C':
        path=folder/'main.c';exe=folder/'main.exe';path.write_text(code,encoding='utf-8')
        run(['gcc','-std=c11','-Wall','-Wextra','-Werror',str(path),'-o',str(exe)]);actual=run([str(exe)])
    elif language=='Java':
        cls=re.search(r'public\s+class\s+(\w+)',code)[1]
        path=folder/(cls+'.java');path.write_text(code,encoding='utf-8')
        run(['javac','-encoding','UTF-8','-d',str(folder),str(path)]);actual=run(['java','-cp',str(folder),cls])
    elif language=='Python':
        path=folder/'main.py';path.write_text(code,encoding='utf-8');actual=run([sys.executable,str(path)])
    elif language=='SQL':
        db=sqlite3.connect(':memory:');statement='';out=[]
        for char in code:
            statement+=char
            if char==';' and sqlite3.complete_statement(statement):
                cur=db.execute(statement)
                if cur.description:
                    out.append('|'.join(c[0] for c in cur.description))
                    out+=['|'.join('' if v is None else str(v) for v in row) for row in cur.fetchall()]
                statement=''
        assert not statement.strip(),q['id'];actual='\n'.join(out)
    else:raise ValueError(language)
    assert actual==q['answer'].strip(),(q['id'],actual,q['answer'])
    results.append({'id':q['id'],'status':'pass','language':language,'output':actual})
(DATA/'prediction-verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':sum(r['status']=='pass' for r in results),'other':[r for r in results if r['status']!='pass']},ensure_ascii=False))
