"""Build a self-contained, offline guide from independently authored analysis."""
from pathlib import Path
from collections import Counter, defaultdict
import html
import json
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'study-materials' / 'exam-guide'
DATA = OUT / 'data'
def esc(s):
    value=html.escape(str(s),quote=True)
    return re.sub(r'[ \t]+(?=\n|$)',lambda m:'&#32;'*len(m[0]),value)

def read(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))

def table(headers, rows, cls=''):
    return '<div class="table-scroll"><table class="'+cls+'"><thead><tr>'+''.join('<th scope="col">'+esc(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def main():
    inventory = read('early-inventory.json') + read('recent-inventory.json')
    inventory.sort(key=lambda q: (q['exam'],q['number']))
    manifest = json.loads((ROOT/'tmp/exam-analysis/questions-only/manifest.json').read_text(encoding='utf-8'))
    files = {v['exam']:v['file'] for v in manifest}
    seen = set()
    for q in inventory:
        key = (q['exam'],q['number'])
        assert key not in seen, key
        seen.add(key)
    expected = {(v['exam'],n) for v in manifest for n in v['detected_questions']}
    assert seen == expected, (expected-seen,seen-expected)
    counts = Counter(q['section'] for q in inventory)
    topics = Counter(q['topic'] for q in inventory)
    languages = Counter(q['language'] for q in inventory if q['section']=='coding')
    byyear = defaultdict(Counter)
    for q in inventory: byyear[q['exam'][:4]][q['section']] += 1
    report = {'pdf_count':len(manifest),'question_count':len(inventory),'counts':dict(counts),
              'topics':dict(topics),'languages':dict(languages),'years':dict(byyear),
              'sources':manifest,'inventory':inventory}
    (DATA/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def source(s):
        filename = files[s['exam']]
        title = s['exam'].replace('-', '년 ',1)+'회 '+str(s['number'])+'번 · PDF '+str(s['page'])+'쪽'
        path = '../../pdf/'+quote(filename)+'#page='+str(s['page'])
        remote = 'https://github.com/jiho6367-design/information-processing-practical/blob/main/pdf/'+quote(filename)+'#page='+str(s['page'])
        return f'<span class="source-pair"><a href="{path}" target="_blank" rel="noopener">{esc(title)}</a><a class="remote" href="{remote}" target="_blank" rel="noopener" aria-label="{esc(title)} 깃허브 원문">↗</a></span>'
    lessons = read('early-lessons.json') + read('recent-lessons.json') + read('root-lessons.json') + read('theory-lessons.json')
    sections = {'coding':[], 'sql':[], 'theory':[]}
    all_ids = set()
    for i,l in enumerate(lessons):
        assert l['id'] not in all_ids, l['id']
        all_ids.add(l['id'])
        lang = l.get('language','이론')
        category = 'sql' if lang=='SQL' else ('theory' if lang=='이론' else 'coding')
        for s in l['sources']:
            assert (s['exam'],s['number']) in seen, s
            assert next(q['page'] for q in inventory if q['exam']==s['exam'] and q['number']==s['number']) == s['page'], s
        body = '<p class="lesson-explanation">'+esc(l.get('explanation',''))+'</p>'
        body += '<h4>이 순서로 풀기</h4><ol class="steps">'+''.join('<li>'+esc(v)+'</li>' for v in l['steps'])+'</ol>'
        if l.get('code'):
            body += '<div class="code-head"><span>'+esc(lang)+' · '+esc(l.get('example_label','학습 예제'))+'</span><button class="copy" type="button">코드 복사</button></div><pre><code>'+esc(l['code'])+'</code></pre>'
        if l.get('diagram'):
            nodes = l['diagram'].get('nodes',[])
            kind = l['diagram'].get('kind','flow')
            body += '<div class="flow" data-kind="'+esc(kind)+'" aria-label="개념 관계">'+''.join('<div class="flow-node">'+esc(n)+'</div>' for n in nodes)+'</div>'
        if l.get('trace'):
            t=l['trace']
            body+='<h4>직접 추적하기</h4><div class="trace" data-step="0">'+table(t['headers'],t['rows'],'trace-table')+'<div class="trace-controls"><button class="trace-next" type="button">한 단계씩 보기</button><button class="trace-all" type="button">전체 보기</button><output aria-live="polite">전체 단계 표시</output></div></div>'
        if l.get('rows'):
            body += table(l['rows']['headers'],l['rows']['rows'])
        if l.get('output'):
            body += '<details class="answer"><summary>예제 실행 결과 확인</summary><pre>'+esc(l['output'])+'</pre></details>'
        body += '<div class="tip"><strong>빠르게 푸는 요령</strong><p>'+esc(l['shortcut'])+'</p></div><div class="pitfall"><strong>자주 틀리는 지점</strong><p>'+esc(l['pitfall'])+'</p></div>'
        if l.get('quiz'):
            body += '<details class="quiz"><summary>셀프 체크 · '+esc(l['quiz']['question'])+'</summary><p>'+esc(l['quiz']['answer'])+'</p></details>'
        body += '<footer class="sources"><span>출제 근거</span>'+''.join(source(s) for s in l['sources'])+'</footer>'
        search = ' '.join([l['title'],l['lead'],lang,l.get('topic',''),l.get('explanation',''),
                           *l['steps'],l['pitfall'],l['shortcut'],l.get('code',''),
                           ' '.join(s['exam'] for s in l['sources'])])
        card = f'<details class="lesson" id="{esc(l["id"])}" data-language="{esc(lang)}" data-search="{esc(search)}"><summary><span class="lang">{esc(lang)}</span><span><strong>{esc(l["title"])}</strong><span class="lead">{esc(l["lead"])}</span></span><span class="plus" aria-hidden="true">+</span></summary><div class="lesson-body"><label class="complete"><input type="checkbox" data-complete="{esc(l["id"])}"> 이 개념을 직접 설명할 수 있음</label>{body}</div></details>'
        sections[category].append(card)
    yearbars=[]
    for year,c in sorted(byyear.items()):
        total=sum(c.values())
        segments=''.join(f'<span class="segment {k}" style="width:{100*c[k]/total:.4f}%" title="{esc(k)} {c[k]}문항">{c[k] or ""}</span>' for k in ['coding','sql','theory'])
        yearbars.append(f'<div class="year-bar"><strong>{year}</strong><div class="stacked" role="img" aria-label="{year}년 코딩 {c["coding"]}, SQL {c["sql"]}, 이론 {c["theory"]}문항">{segments}</div><span>{total}문항</span></div>')
    theoryrows = [[t,n,'키워드 → 구별 기준 → 예제 순으로 복습'] for t,n in topics.most_common() if t not in ['반복·배열','포인터·문자열','재귀·자료구조','객체·상속','Python 컬렉션','연산·상태','SQL']]
    codingrows = [[t,n,'동일 유형의 변형 예제를 손으로 추적'] for t,n in topics.most_common() if t in ['반복·배열','포인터·문자열','재귀·자료구조','객체·상속','Python 컬렉션','연산·상태','SQL']]
    qrows=[]
    for q in inventory:
        search = f'{q["exam"]} {q["number"]} {q["title"]} {q["topic"]} {q["language"]} '+ ' '.join(q['skills'])
        qrows.append(f'<tr data-search="{esc(search)}" data-section="{esc(q["section"])}"><td>{esc(q["exam"])}</td><td>{q["number"]}</td><td><span class="small-tag">{esc(q["language"] or "이론")}</span> {esc(q["title"])}'+(f'<small class="source-note">{esc(q["note"])}</small>' if q.get('note') else '')+f'</td><td>{esc(q["topic"])}</td><td>{source(q)}</td></tr>')
    template = (OUT/'guide.template.html').read_text(encoding='utf-8')
    old = [q for q in inventory if q['exam'][:4] <= '2022']
    new = [q for q in inventory if q['exam'][:4] >= '2023']
    applied=lambda group:sum(q['section'] in ['coding','sql'] for q in group)
    trend=f'코딩·SQL은 2020~2022년 {applied(old)}/{len(old)}문항({100*applied(old)/len(old):.1f}%), 2023~2026년 {applied(new)}/{len(new)}문항({100*applied(new)/len(new):.1f}%)입니다. 이 자료에서는 실행 추적 능력에 더 많은 시간을 배분할 근거가 있습니다.'
    replacements={'PDF_COUNT':len(manifest),'QUESTION_COUNT':len(inventory),'CODING_COUNT':counts['coding'],
                  'SQL_COUNT':counts['sql'],'THEORY_COUNT':counts['theory'],'LESSON_COUNT':len(lessons),
                  'YEAR_BARS':''.join(yearbars),'CODING_RANK':table(['유형','문항 수','복습 방법'],codingrows),
                  'THEORY_RANK':table(['분야','문항 수','복습 방법'],theoryrows),
                  'CODING_LESSONS':''.join(sections['coding']),'SQL_LESSONS':''.join(sections['sql']),
                  'THEORY_LESSONS':''.join(sections['theory']),'INVENTORY':''.join(qrows),'TREND':trend,
                  'SCROLL_NAV':(OUT/'scroll-navigation.js').read_text(encoding='utf-8')}
    for k,v in replacements.items(): template=template.replace('__'+k+'__',str(v))
    (OUT/'index.html').write_text(template.rstrip()+'\n',encoding='utf-8')
    print(json.dumps({'questions':len(inventory),'counts':dict(counts),'lessons':len(lessons),'html_bytes':len(template.encode())},ensure_ascii=False))

if __name__=='__main__': main()
