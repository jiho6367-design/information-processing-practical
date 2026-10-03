"""Build original anticipated exercises and network calculation practice."""
from pathlib import Path
import html
import json
import re
from urllib.parse import quote
from build_exam_guide import table
from prediction_intent import render_intents

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'study-materials/exam-guide'
DATA=OUT/'data'
esc=lambda v:html.escape(str(v),quote=True)

def graph(diagram):
    nodes=diagram['nodes'];edges=diagram.get('edges',[])
    if not edges:
        return '<div class="flow" data-kind="memory">'+''.join('<div class="flow-node">'+esc(n)+'</div>' for n in nodes)+'</div>'
    import math
    long_labels=any(len(n)>8 for n in nodes)
    router=any('라우터' in n for n in nodes)
    positions=[]
    if router and len(nodes)==7:
        positions=[(160,405),(160,245),(480,65),(480,245),(480,405),(800,245),(800,405)]
        view='0 0 960 490'
    elif long_labels:
        positions=[(120+i*240,70) if i<4 else (600,265) for i in range(len(nodes))]
        view='0 0 960 345'
    else:
        for i,n in enumerate(nodes):
            angle=2*math.pi*i/len(nodes)-math.pi/2
            positions.append((340+250*math.cos(angle),210+145*math.sin(angle)))
        view='0 0 680 420'
    parts=['<div class="svg-board"><svg data-long="'+str(long_labels).lower()+'" viewBox="'+view+'" role="img" aria-label="문제에서 주어진 네트워크 연결도">']
    for edge in edges:
        a,b=edge[:2];label=edge[2] if len(edge)>2 else ''
        if isinstance(a,str):a=nodes.index(a)
        if isinstance(b,str):b=nodes.index(b)
        x1,y1=positions[a];x2,y2=positions[b]
        mx,my=(x1+x2)/2,(y1+y2)/2
        if long_labels and y1==y2:my+=65
        width=max(32,len(str(label))*11)
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#738e80" stroke-width="2"/><rect x="{mx-width/2}" y="{my-12}" width="{width}" height="25" fill="#fffefb"/><text x="{mx}" y="{my+5}" text-anchor="middle" font-size="12">{esc(label)}</text>')
    for n,(x,y) in zip(nodes,positions):
        if long_labels:
            import textwrap
            lines=textwrap.wrap(n,width=17)
            parts.append(f'<rect x="{x-100}" y="{y-38}" width="200" height="76" rx="9" fill="#e8f0da" stroke="#176c62" stroke-width="1.5"/>')
            for i,line in enumerate(lines):parts.append(f'<text x="{x}" y="{y-(len(lines)-1)*9+i*18+5}" text-anchor="middle" font-size="13">{esc(line)}</text>')
        else:parts.append(f'<circle cx="{x}" cy="{y}" r="24" fill="#e8f0da" stroke="#176c62" stroke-width="2"/><text x="{x}" y="{y+5}" text-anchor="middle" font-size="15">{esc(n)}</text>')
    return ''.join(parts)+'</svg></div>'

def main():
    parts=[]
    for name in ['predictions-c-python.json','predictions-java-sql.json','predictions-network.json']:
        parts+=json.loads((DATA/name).read_text(encoding='utf-8'))
    order={'C':0,'Java':1,'Python':2,'SQL':3,'네트워크':4}
    parts.sort(key=lambda q:order[q['language']])
    analysis=json.loads((DATA/'analysis.json').read_text(encoding='utf-8'))
    files={s['exam']:s['file'] for s in analysis['sources']}
    inventory={(q['exam'],q['number']):q for q in analysis['inventory']}
    def source(s):
        q=inventory[(s['exam'],s['number'])];assert q['page']==s['page'],s
        return f'<a href="../../pdf/{quote(files[s["exam"]])}#page={s["page"]}" target="_blank" rel="noopener">{esc(s["exam"])} {s["number"]}번 · PDF {s["page"]}쪽</a>'
    groups={lang:[] for lang in order}
    ids=set()
    for n,q in enumerate(parts,1):
        assert q['id'] not in ids,q['id'];ids.add(q['id']);q['number']=n
        body='<p class="question-prompt">'+esc(q['prompt'])+'</p>'
        if q.get('givens'):
            given=q['givens']
            if isinstance(given,dict):body+=table(given['headers'],given['rows'])
            else:body+='<div class="flow">'+''.join('<div class="flow-node">'+esc(g)+'</div>' for g in given)+'</div>'
        if q.get('diagram'):body+=graph(q['diagram'])
        if q.get('code'):
            body+='<div class="code-head"><span>'+esc(q['language'])+' · 독립 제작 문제</span><button class="copy" type="button">코드 복사</button></div><pre><code>'+esc(q['code'])+'</code></pre>'
        body+=f'<label class="answer-label" for="answer-{esc(q["id"])}">내 답안</label><textarea id="answer-{esc(q["id"])}" data-answer-id="{esc(q["id"])}" rows="3" placeholder="정답을 펼치기 전에 직접 계산한 결과를 적어 보세요."></textarea><div class="answer-controls"><button class="compare" type="button">정답 비교</button><button class="clear-answer" type="button">내 답안 지우기</button><output aria-live="polite"></output></div>'
        solution='<h4>정답</h4><pre>'+esc(q['answer'])+'</pre><h4>풀이 순서</h4><ol class="steps">'+''.join('<li>'+esc(x)+'</li>' for x in q['steps'])+'</ol>'
        if q.get('trace'):solution+='<h4>계산·실행 추적표</h4>'+table(q['trace']['headers'],q['trace']['rows'])
        solution+='<div class="pitfall"><strong>함정</strong><p>'+esc(q['pitfall'])+'</p></div><div class="tip"><strong>한 줄을 바꾸면?</strong><p>'+esc(q['variation'])+'</p></div>'
        body+='<details class="solution"><summary>정답·독립 풀이 확인</summary>'+solution+'</details><footer class="sources"><span>유형 선정 근거</span>'+''.join(source(s) for s in q['basis'])+'</footer>'
        title=f'<div class="question-heading"><span class="question-number">{n:02d}</span><div><span class="lang">{esc(q["language"])}</span> <span class="difficulty">{esc(q["difficulty"])}</span><h3>{esc(q["title"])}</h3></div></div><p class="intent"><strong>겨냥하는 능력</strong> {esc(q["intent"])}</p>'
        search=' '.join([q['title'],q['language'],q['difficulty'],q['intent'],q['prompt']])
        groups[q['language']].append(f'<article class="question" id="{esc(q["id"])}" data-language="{esc(q["language"])}" data-search="{esc(search)}" data-expected="{esc(q["answer"])}">{title}{body}</article>')
    intents=json.loads((DATA/'examiner-intent.json').read_text(encoding='utf-8'))
    examples=json.loads((DATA/'intent-examples.json').read_text(encoding='utf-8'))
    intent_html=render_intents(intents,examples,source,parts)
    styles=re.search(r'<style>([\s\S]*?)</style>',(OUT/'guide.template.html').read_text(encoding='utf-8'))[1]
    template=(OUT/'predictions.template.html').read_text(encoding='utf-8-sig')
    rep={'STYLE':styles,'INTENT':intent_html,'TOTAL':len(parts),'NETWORK_COUNT':sum(q['language']=='네트워크' for q in parts),
         'SCROLL_NAV':(OUT/'scroll-navigation.js').read_text(encoding='utf-8')}
    for lang,key in [('C','C'),('Java','JAVA'),('Python','PYTHON'),('SQL','SQL'),('네트워크','NETWORK')]:rep[key+'_QUESTIONS']=''.join(groups[lang])
    for k,v in rep.items():template=template.replace('__'+k+'__',str(v))
    (OUT/'predictions.html').write_text(template.rstrip()+'\n',encoding='utf-8')
    (DATA/'predictions.json').write_text(json.dumps(parts,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'questions':len(parts),'network':rep['NETWORK_COUNT'],'bytes':len(template.encode())},ensure_ascii=False))

if __name__=='__main__':main()
