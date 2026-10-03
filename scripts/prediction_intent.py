"""Render short, visual explanations of the independently observed exam patterns."""
import html
import re

esc = lambda value: html.escape(str(value), quote=True)


def rich(value):
    """Only allow emphasis authored in the data; all other content stays escaped."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc(value))


def example_code(code, lines=()):
    return '<pre class="intent-code"><code>' + ''.join(
        '<span class="example-line' + (' changed' if number in lines else '') + '">' +
        (esc(line) or ' ') + '</span>' for number, line in enumerate(code.splitlines(), 1)
    ) + '</code></pre>'


def svg_board(body, label, key, height=180):
    return f'<svg viewBox="0 0 420 {height}" role="img" aria-label="{esc(label)}"><defs><marker id="arrow-{key}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#176c62"/></marker></defs>{body}</svg>'


def box(x, y, width, height, label, value):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="#fffefb" stroke="#9eb9b0"/><text x="{x+width/2}" y="{y+24}" text-anchor="middle" font-size="14" fill="#536563">{esc(label)}</text><text x="{x+width/2}" y="{y+52}" text-anchor="middle" font-size="22" font-weight="700" fill="#182b2a">{esc(value)}</text>'


def arrow(x1, y1, x2, y2, key, dashed=False):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#176c62" stroke-width="2" marker-end="url(#arrow-{key})"' + (' stroke-dasharray="6 4"' if dashed else '') + '/>'


def drawing(diagram, side, key):
    kind = diagram['kind']
    changed = side == 'after'
    if kind == 'tracks':
        nodes = diagram[side]
        return '<div class="diagram-track">' + ''.join(
            '<div class="track-node' + (' skipped' if node.get('muted') else '') + '"><span>' +
            esc(node['label']) + '</span><strong>' + esc(node['value']) + '</strong><small>' +
            esc(node['note']) + '</small></div>' +
            ('<span class="track-arrow" aria-hidden="true">→</span>' if i < len(nodes)-1 else '')
            for i, node in enumerate(nodes)
        ) + '</div>'
    if kind == 'memory':
        if changed:
            body = box(25, 50, 145, 78, '함수 안의 p', '&a') + box(255, 50, 140, 78, '원래 변수 a', '9')
            body += arrow(170, 90, 253, 90, key) + '<text x="210" y="72" text-anchor="middle" font-size="14">주소로 접근</text>'
        else:
            body = box(25, 50, 145, 78, '원래 변수 a', '1') + box(255, 50, 140, 78, '별도 변수 x', '9')
            body += arrow(170, 90, 253, 90, key, True) + '<text x="210" y="72" text-anchor="middle" font-size="14">1을 복사</text>'
        return svg_board(body, diagram[side+'_caption'], key)
    if kind == 'nested':
        body = box(20, 12, 115, 65, '원래 리스트', 'm[0]') + box(20, 100, 115, 65, '복사한 리스트', 'c[0]')
        if changed:
            body += box(250, 12, 150, 65, '원래 안쪽 리스트', '[1]') + box(250, 100, 150, 65, '새 안쪽 리스트', '[1, 9]')
            body += arrow(135, 45, 248, 45, key) + arrow(135, 133, 248, 133, key)
        else:
            body += box(250, 55, 150, 78, '공유하는 리스트', '[1, 9]')
            body += arrow(135, 45, 248, 83, key) + arrow(135, 133, 248, 107, key)
        return svg_board(body, diagram[side+'_caption'], key)
    if kind == 'tree':
        body = '<line x1="210" y1="65" x2="100" y2="165" stroke="#94aca2" stroke-width="2"/><line x1="210" y1="65" x2="320" y2="165" stroke="#94aca2" stroke-width="2"/>'
        for value, order, x, y in [(1, 3 if changed else 1, 210, 60), (2, 1 if changed else 2, 100, 165), (3, 2 if changed else 3, 320, 165)]:
            body += f'<circle cx="{x}" cy="{y}" r="29" fill="#fffefb" stroke="#176c62" stroke-width="2"/><text x="{x}" y="{y+7}" text-anchor="middle" font-size="23" font-weight="700">{value}</text><rect x="{x+19}" y="{y-39}" width="53" height="24" rx="12" fill="#dbecaa"/><text x="{x+45}" y="{y-22}" text-anchor="middle" font-size="12" font-weight="700">{order}번째</text>'
        return svg_board(body, diagram[side+'_caption'], key, 220)
    if kind == 'rows':
        return '<table class="count-table"><caption>T 테이블 · 집계에 포함되는 대상</caption><thead><tr><th>id</th><th>score</th><th>집계</th></tr></thead><tbody>' + ''.join(
            '<tr'+(' class="null-row"' if score == 'NULL' else '')+'><td>'+str(i)+'</td><td><strong>'+score+'</strong></td><td>'+
            ('<span class="exclude">값 없음 · 제외</span>' if changed and score == 'NULL' else '<span class="include">포함 ✓</span>')+'</td></tr>'
            for i, score in enumerate(['80', 'NULL', '90'], 1)
        ) + '</tbody></table>'
    if kind == 'links':
        body = ''
        for label, value, x in [('a', 1 if changed else 3, 70), ('b', 2, 210), ('c', 3, 350)]:
            y = 84 if changed and label == 'b' else 12
            body += box(x-50, y, 100, 70, '노드 '+label, str(value))
        if changed:
            body += arrow(120, 47, 298, 47, key) + '<text x="210" y="29" text-anchor="middle" font-size="13">a.next = &amp;c</text><text x="210" y="178" text-anchor="middle" font-size="13">b는 존재하지만 방문하지 않음</text>'
        else:
            body += arrow(120, 47, 158, 47, key) + arrow(260, 47, 298, 47, key)
            body += '<text x="70" y="112" text-anchor="middle" font-size="13">a.value = 3</text>'
        return svg_board(body, diagram[side+'_caption'], key, 195)
    raise ValueError(kind)


def render_intents(intents, examples, source, questions):
    views = {example['id']: example for example in examples}
    assert len(views) == len(intents) == 8
    question_map = {question['id']: question for question in questions}
    tabs, cards = [], []
    for n, observed in enumerate(intents, 1):
        view = views[observed['id']]
        key = observed['id']
        tabs.append(f'<button type="button" class="intent-tab" id="choose-{key}" data-intent="{key}" aria-controls="{key}" aria-pressed="{str(n==1).lower()}"><span>{n:02d}</span><strong>{esc(view["label"])}</strong><small>{esc(view["language"])}</small></button>')
        comparisons = []
        visuals = []
        for side in ['before', 'after']:
            example = view[side]
            comparisons.append('<div class="example-version '+side+'"><h4>'+esc(example['label'])+'</h4>'+example_code(example['code'], example['lines'])+'<div class="example-result"><span>출력</span><strong>'+esc(example['result'])+'</strong></div></div>')
            visuals.append('<div class="visual-version"><div class="visual-label">'+('원래' if side=='before' else '변형')+'</div>'+drawing(view['diagram'], side, key+'-'+side)+'<p>'+esc(view['diagram'][side+'_caption'])+'</p></div>')
        common = '<div class="common-example"><span>'+esc(view.get('common_caption', '공통 준비'))+'</span>'+example_code(view['common'])+'</div>' if view.get('common') else ''
        why = '<ol class="intent-why">' + ''.join('<li><span>'+str(i)+'</span><p>'+rich(step)+'</p></li>' for i, step in enumerate(view['why'], 1)) + '</ol>'
        method = '<ol class="intent-method">' + ''.join('<li><span>'+str(i)+'</span><p>'+rich(step)+'</p></li>' for i, step in enumerate(view['method'], 1)) + '</ol>'
        practice = ''.join('<a class="practice-link" href="#'+esc(qid)+'">'+esc(question_map[qid]['language'])+' '+str(question_map[qid]['number'])+'번 연습 →</a>' for qid in view['practice'])
        evidence = '<details class="intent-evidence"><summary>이 유형을 고른 기출 근거 보기</summary><p><strong>문제에서 관찰한 특징</strong><br>'+esc(observed['claim'])+'</p><p>'+esc(observed['evidence'])+'</p><p><strong>추가로 대비할 변형</strong><br>'+esc(observed['expected_variation'])+'</p><footer class="sources">'+''.join(source(s) for s in observed['sources'])+'</footer></details>'
        cards.append(f'<article class="intent-card" id="{key}" aria-labelledby="title-{key}"'+(' hidden' if n != 1 else '')+'><header class="intent-card-heading"><span class="intent-index">'+f'{n:02d}'+'</span><div><span class="intent-subtitle">'+esc(view['language'])+' · '+esc(view['label'])+'</span><h3 id="title-'+key+'">'+esc(view['title'])+'</h3><p class="intent-goal">'+rich(view['goal'])+'</p></div></header><div class="intent-change"><span>예상 변형을 코드로 보면</span><p>'+rich(view['change'])+'</p></div>'+common+'<div class="example-pair">'+''.join(comparisons)+'</div><div class="diagram-heading"><h4>'+esc(view['diagram']['caption'])+'</h4><span>그림으로 확인</span></div><div class="visual-pair">'+''.join(visuals)+'</div><h4 class="intent-section-label">왜 답이 달라질까요?</h4>'+why+'<div class="solve-strip"><h4>풀 때는 이렇게 표시하세요</h4>'+method+'</div><details class="intent-check"><summary><span>이해 확인</span>'+esc(view['check']['question'])+'</summary><p>'+esc(view['check']['answer'])+'</p></details><div class="practice-row"><span>이 방법을 바로 적용하기</span>'+practice+'</div>'+evidence+'</article>')
    return '<div class="intent-selector" aria-label="풀이 유형 선택">'+''.join(tabs)+'</div><p class="intent-status" id="intent-status" aria-live="polite">1 / 8 · 실행 추적</p><div class="intent-panels">'+''.join(cards)+'</div>'
