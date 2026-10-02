"""Extract question pages only; never expose answer/explanation bodies."""
from pathlib import Path
import hashlib
import json
import re
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'tmp' / 'exam-analysis' / 'questions-only'
CACHE.mkdir(parents=True, exist_ok=True)
manifest = []
for path in sorted((ROOT / 'pdf').glob('*.pdf')):
    match = re.match(r'(\d{4})년\s+([\d,]+)회', path.name)
    exam = f'{match[1]}-{match[2]}'
    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc):
        header = page.get_text(clip=pymupdf.Rect(0, 0, page.rect.width, 150))
        if re.search(r'정답\s*및\s*해설', header):
            break
        pages.append({'page': i+1, 'text': page.get_text(sort=True)})
    text = '\n'.join(f'\n=== PDF PAGE {p["page"]} ===\n{p["text"]}' for p in pages)
    (CACHE / f'{exam}.txt').write_text(text, encoding='utf-8')
    matches = list(re.finditer(r'(?m)^\s*문제\s+(\d{1,2})(?!\d)',text))
    questions=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        page=int(re.findall(r'=== PDF PAGE (\d+) ===',text[:m.start()])[-1])
        questions.append({'number':int(m[1]),'page':page,'text':text[m.start():end]})
    (CACHE/f'{exam}.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest.append({'exam':exam,'year':int(match[1]),'file':path.name,
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'total_pages':len(doc),'question_pages':len(pages),
                     'detected_questions':[q['number'] for q in questions]})
    print(exam, len(pages), 'question pages', len(questions), 'questions')
(CACHE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
