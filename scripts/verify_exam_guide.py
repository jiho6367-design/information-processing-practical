"""Check independent teaching examples with native language runtimes.

No PDF answers or explanations are accessed by this check.
"""
from pathlib import Path
import json
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'study-materials/exam-guide/data'
TMP=ROOT/'tmp/exam-analysis/verification'
TMP.mkdir(parents=True,exist_ok=True)
results=[]

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=30)
    if p.returncode: raise RuntimeError(p.stderr)
    return p.stdout.strip()

def check_example(l):
    lang=l.get('language','')
    if lang not in ['C','Java','Python','SQL'] or not l.get('code'): return
    folder=TMP/l['id'];folder.mkdir(exist_ok=True)
    code=l['code']
    if lang=='C':
        path=folder/'main.c';path.write_text(code,encoding='utf-8')
        exe=folder/'main.exe'
        run(['gcc','-std=c11','-Wall','-Wextra',str(path),'-o',str(exe)])
        actual=run([str(exe)])
    elif lang=='Java':
        name=re.search(r'public\s+class\s+(\w+)',code)
        if not name: name=re.search(r'class\s+(\w+)',code)
        if not name: raise RuntimeError('missing Java class')
        path=folder/(name[1]+'.java');path.write_text(code,encoding='utf-8')
        run(['javac','-encoding','UTF-8','-d',str(folder),str(path)])
        actual=run(['java','-cp',str(folder),name[1]])
    elif lang=='Python':
        path=folder/'main.py';path.write_text(code,encoding='utf-8')
        actual=run([sys.executable,str(path)])
    else:
        db=sqlite3.connect(':memory:')
        if not l.get('setup_sql'):
            outputs=[]; statement=''
            for char in code:
                statement+=char
                if char==';' and sqlite3.complete_statement(statement):
                    cur=db.execute(statement)
                    if cur.description:
                        outputs.append('|'.join(d[0] for d in cur.description))
                        outputs.extend('|'.join('' if v is None else str(v) for v in row) for row in cur.fetchall())
                    statement=''
            assert not statement.strip(), (l['id'],'unterminated SQL')
            actual='\n'.join(outputs)
            assert actual==l['output'].strip(), (l['id'],actual,l['output'])
            results.append({'id':l['id'],'status':'pass','runtime':'SQLite '+sqlite3.sqlite_version,'output':actual})
            return
        db.executescript(l['setup_sql'])
        rows=db.execute(code).fetchall()
        if 'verify_rows' in l:
            assert [list(r) for r in rows]==l['verify_rows'], (l['id'],rows,l['verify_rows'])
            results.append({'id':l['id'],'status':'pass','runtime':'SQLite '+sqlite3.sqlite_version,'rows':rows});return
        actual='\n'.join(' | '.join(str(v) for v in row) for row in rows)
    expected=l['output'].strip()
    assert actual==expected,(l['id'],actual,expected)
    results.append({'id':l['id'],'status':'pass','runtime':lang,'output':actual})

for filename in ['early-lessons.json','recent-lessons.json','root-lessons.json']:
    for lesson in json.loads((DATA/filename).read_text(encoding='utf-8')): check_example(lesson)

# Independently verify exact recent questions used by the visual labs.
check_example({'id':'lab-pointer-exact','language':'C','code':'''#include <stdio.h>
void func1(int *p){*p=50;} void func2(int p){p=60;}
void func34(int p[]){int *q=p;printf("3. %d\\n",*q);printf("4. %d",*(q+3));}
int main(void){int i=30,arr[]={2,4,6,8,10};func1(&i);printf("1. %d\\n",i);func2(i);printf("2. %d\\n",i);func34(arr);return 0;}
''','output':'1. 50\n2. 50\n3. 2\n4. 8'})
tree_code='''#include <stdio.h>
typedef struct N {int v; struct N *a,*b;} N;
int c=0,rst=0;
void fts(N *n){if(!n)return;fts(n->a);fts(n->b);if(++c==3)rst=n->v;}
int main(void){N d={0,0,0},e={0,0,0},cn={53,0,0},b={12,&d,&e},a={64,&b,&cn};fts(&a);printf("%d",rst);return 0;}
'''
check_example({'id':'lab-postorder-exact','language':'C','code':tree_code,'output':'12'})
check_example({'id':'case-recursion-exact','language':'Java','code':'''public class Main {
static int compute(int num){if(num<=1)return num;return compute(num-3)+compute(num-1);}
public static void main(String[] args){System.out.print(compute(5));}
}''','output':'1'})
check_example({'id':'case-dictionary-exact','language':'Python','code':'''locations={"NYC":"NEWYORK","LDN":"LONDON","PAR":"PARIS","TKY":"TOKYO"}
s=""
for key,value in locations.items():s+=key[-1]+value[0]
print(s,end="")''','output':'CNNLRPYT'})
check_example({'id':'case-correlated-exact','language':'SQL','setup_sql':'''CREATE TABLE A(id,x);INSERT INTO A VALUES(1,10),(2,20),(3,30),(4,40);
CREATE TABLE B(id,y);INSERT INTO B VALUES(1,5),(1,15),(2,20),(3,35),(5,50);''',
'code':'''SELECT COUNT(*) FROM A WHERE x > (SELECT AVG(y) FROM B WHERE B.id IN (SELECT A2.id FROM A A2 WHERE A2.x < A.x));''', 'verify_rows':[[3]]})
check_example({'id':'case-right-join-exact','language':'SQL','setup_sql':'''CREATE TABLE A(id,v);INSERT INTO A VALUES(1,10),(1,20),(2,30);
CREATE TABLE B(id,w);INSERT INTO B VALUES(1,100),(3,300),(4,400);''',
'code':'''SELECT COUNT(*) AS Result FROM A RIGHT OUTER JOIN B ON A.id=B.id WHERE A.id IS NULL;''','verify_rows':[[2]]})

# SRT mini-case and LFU/LRU mini-cases are derived without PDF explanations.
arrivals=[0,1,2,3];burst=[8,4,9,5];remaining=burst.copy();completion=[None]*4;t=0;gantt=[]
while any(remaining):
    candidates=[i for i in range(4) if arrivals[i]<=t and remaining[i]>0]
    if not candidates:t+=1;continue
    i=min(candidates,key=lambda i:(remaining[i],arrivals[i],i))
    gantt.append(i);remaining[i]-=1;t+=1
    if remaining[i]==0:completion[i]=t
wait=[completion[i]-arrivals[i]-burst[i] for i in range(4)]
assert wait==[9,0,15,2] and sum(wait)/4==6.5,(completion,wait)
results.append({'id':'srt-exact','status':'pass','waiting':wait,'mean':6.5})

(DATA/'verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':sum(x['status']=='pass' for x in results),'not_run':[x for x in results if x['status']!='pass']},ensure_ascii=False))
