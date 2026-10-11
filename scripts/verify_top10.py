"""Execute code exercises and check the offline content contract."""
import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = (root / 'public/top10.html').read_text(encoding='utf-8')
data = json.loads(re.search(r'<script id="study-data" type="application/json">(.*?)</script>', html, re.S)[1])
assert len(data) == 10
assert (root / 'study-materials/top10.html').read_text(encoding='utf-8') == html
assert data[-1]['rate'] is None
executed = 0
with tempfile.TemporaryDirectory(prefix='top10-verify-') as tmp:
    folder = Path(tmp)
    for i, item in enumerate(data):
        for stage in ['original', 'application']:
            q = item[stage]
            assert q['answerParts'] and q['steps']
            assert all(p['answer'] in p['acceptedAnswers'] for p in q['answerParts'])
            if i not in [0, 1, 3, 5, 6]:
                continue
            code = '\n'.join(b['text'] for b in q['promptBlocks'] if b['type'] == 'code')
            if '#include' in code:
                f = folder / 'test.c'
                f.write_text(code, encoding='utf-8')
                exe = folder / 'test.exe'
                subprocess.run(['gcc', str(f), '-o', str(exe)], check=True, capture_output=True)
                command = [str(exe)]
            elif 'public class Main' in code:
                f = folder / 'Main.java'
                f.write_text(code, encoding='utf-8')
                subprocess.run(['javac', str(f)], check=True, capture_output=True)
                command = ['java', '-cp', str(folder), 'Main']
            else:
                f = folder / 'test.py'
                f.write_text(code, encoding='utf-8')
                command = [sys.executable, str(f)]
            actual = subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()
            answers = [p['answer'] for p in q['answerParts']]
            if actual.startswith('{'):
                actual_values = [str(v) for pair in ast.literal_eval(actual).values() for v in pair]
            else:
                actual_values = actual.splitlines()
            assert actual_values == answers, (item['title'], stage, actual_values, answers)
            executed += 1
    # Test the exact normalizer used by the page without browser side effects.
    fn = re.search(r'function normalize\(x\)\{.*?\}\n', html)[0]
    js = fn + """
const assert = (condition) => { if (!condition) throw new Error('Grading regression'); };
assert(normalize(' \\"c\\" ') === normalize('C'));
assert(normalize('ＡＲＰ spoofing') === normalize('arp spoofing'));
assert(normalize('3F') === normalize('3f'));
assert(normalize('32') !== normalize('20'));
assert(normalize('TEAM_ID') !== normalize('TEAM_ID2'));
assert(normalize('') !== normalize('0'));
"""
    f = folder / 'grading.cjs'
    f.write_text(js, encoding='utf-8')
    subprocess.run(['node', str(f)], check=True)
print(f'PASS: {executed} C/Java/Python executions; 20 question schemas; grading format and negative cases.')
