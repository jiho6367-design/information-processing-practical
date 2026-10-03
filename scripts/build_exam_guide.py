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

def plain_words(value):
    replacements={'동적 디스패치':'실제 객체에 맞는 함수 선택','디스패치':'함수 선택',
                  '시그니처':'함수 이름·받는 값의 종류','기저값':'멈출 때 돌려주는 값',
                  '단락 평가':'뒤 조건을 건너뛰는 계산','미매칭':'짝이 없는',
                  '역참조':'주소가 가리키는 값 읽기','인스턴스 필드':'객체에 저장된 값',
                  '메서드':'함수','일반 지역 변수':'함수 안의 일반 변수','지역 변수':'함수 안의 변수'}
    text=str(value)
    for old,new in replacements.items(): text=text.replace(old,new)
    return text

def learning_table(value,kind):
    headers=['먼저 볼 곳','예제에서 적은 값','보는 이유'] if kind=='start-table' else ['상황','바로 할 일','예제에 적용']
    assert len(value['headers'])==3 and all(len(row)==3 for row in value['rows'])
    return table(headers,[[plain_words(cell) for cell in row] for row in value['rows']],kind)

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
    easier=read('early-easy.json')+read('recent-easy.json')+read('root-easy.json')+read('theory-easy.json')
    easy_by_id={item['id']:item for item in easier}
    assert len(easy_by_id)==len(easier)==len(lessons)
    assert set(easy_by_id)=={lesson['id'] for lesson in lessons}
    sections = {'coding':[], 'sql':[], 'theory':[]}
    all_ids = set()
    for i,l in enumerate(lessons):
        view=easy_by_id[l['id']]
        assert l['id'] not in all_ids, l['id']
        all_ids.add(l['id'])
        lang = l.get('language','이론')
        category = 'sql' if lang=='SQL' else ('theory' if lang=='이론' else 'coding')
        for s in l['sources']:
            assert (s['exam'],s['number']) in seen, s
            assert next(q['page'] for q in inventory if q['exam']==s['exam'] and q['number']==s['number']) == s['page'], s
        body = '<div class="lesson-start"><h4>시작할 때 보는 표</h4>'+learning_table(view['start_table'],'start-table')+'</div>'
        if l.get('code'):
            body += '<div class="code-head"><span>'+esc(lang)+' 예제</span><button class="copy" type="button">코드 복사</button></div><pre><code>'+esc(l['code'])+'</code></pre>'
        if l.get('trace'):
            t=view.get('trace',l['trace'])
            body+='<h4>이 줄을 실행하면 이렇게 바뀝니다</h4><div class="trace" data-step="0">'+table([plain_words(v) for v in t['headers']],[[plain_words(v) for v in row] for row in t['rows']],'trace-table')+'<div class="trace-controls"><button class="trace-next" type="button">한 줄씩 보기</button><button class="trace-all" type="button">전체 보기</button><output aria-live="polite">전체 단계 표시</output></div></div>'
        if l.get('rows'):
            rows=view.get('rows',l['rows'])
            body += '<details class="extra-table"><summary>다른 예시·비교표 보기</summary>'+table([plain_words(v) for v in rows['headers']],[[plain_words(v) for v in row] for row in rows['rows']])+'</details>'
        if l.get('output'):
            body += '<details class="answer"><summary>정답 보기</summary><pre>'+esc(l['output'])+'</pre></details>'
        body += '<div class="lesson-shortcut"><h4>빠르게 푸는 표</h4>'+learning_table(view['shortcut_table'],'shortcut-table')+'</div><div class="pitfall"><strong>이것만 주의</strong><p>'+esc(plain_words(view['pitfall']))+'</p></div>'
        if view.get('quiz'):
            body += '<details class="quiz"><summary>확인 문제 · '+esc(plain_words(view['quiz']['question']))+'</summary><p>'+esc(plain_words(view['quiz']['answer']))+'</p></details>'
        body += '<footer class="sources"><span>출제 근거</span>'+''.join(source(s) for s in l['sources'])+'</footer>'
        search = ' '.join([view['title'],view['lead'],l['title'],l['lead'],lang,l.get('topic',''),l.get('explanation',''),
                           *l['steps'],l['pitfall'],l['shortcut'],l.get('code',''),
                           ' '.join(s['exam'] for s in l['sources'])])
        card = f'<details class="lesson" id="{esc(l["id"])}" data-language="{esc(lang)}" data-search="{esc(search)}"><summary><span class="lang">{esc(lang)}</span><span><strong>{esc(plain_words(view["title"]))}</strong><span class="lead">{esc(plain_words(view["lead"]))}</span></span><span class="plus" aria-hidden="true">+</span></summary><div class="lesson-body"><label class="complete"><input type="checkbox" data-complete="{esc(l["id"])}"> 이해했음</label>{body}</div></details>'
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
