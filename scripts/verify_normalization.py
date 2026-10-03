"""Verify the rendered normalization examples without reading PDF explanations."""
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'study-materials' / 'exam-guide'


class Relations(HTMLParser):
    def __init__(self, include_hidden=False):
        super().__init__()
        self.tables = {}
        self.current = None
        self.headers = []
        self.rows = []
        self.row = []
        self.cell = None
        self.header_row = False
        self.hidden_row = False
        self.include_hidden = include_hidden

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and attrs.get('data-norm-relation'):
            assert self.current is None
            self.current = attrs['data-norm-relation']
            assert self.current not in self.tables
            self.headers, self.rows = [], []
        if not self.current:
            return
        if tag == 'tr':
            self.row = []
            self.header_row = False
            self.hidden_row = 'hidden' in attrs and not self.include_hidden
        if tag in ('td', 'th'):
            self.cell = ''
            self.header_row |= tag == 'th'

    def handle_data(self, text):
        if self.cell is not None:
            self.cell += text

    def handle_endtag(self, tag):
        if not self.current:
            return
        if tag in ('td', 'th'):
            self.row.append(self.cell.strip())
            self.cell = None
        if tag == 'tr':
            if self.header_row:
                self.headers = self.row
            elif not self.hidden_row:
                assert len(self.row) == len(self.headers), self.current
                self.rows.append(dict(zip(self.headers, self.row)))
        if tag == 'table':
            self.tables[self.current] = self.rows
            self.current = None


def canonical(rows):
    return {tuple(sorted(row.items())) for row in rows}


def project(rows, columns):
    return canonical([{column: row[column] for column in columns} for row in rows])


def join(left, right):
    return [a | b for a in left for b in right
            if all(a[column] == b[column] for column in a.keys() & b.keys())]


def dependency(rows, left, right):
    seen = {}
    for row in rows:
        key = tuple(row[column] for column in left)
        value = tuple(row[column] for column in right)
        if key in seen and seen[key] != value:
            return False
        seen[key] = value
    return True


def closure(attributes, dependencies):
    found = set(attributes)
    while True:
        previous = found.copy()
        for left, right in dependencies:
            if set(left) <= found:
                found.update(right)
        if previous == found:
            return found


def keys(attributes, dependencies):
    result = []
    for size in range(1, len(attributes) + 1):
        for group in combinations(attributes, size):
            group = frozenset(group)
            if not any(key <= group for key in result) and closure(group, dependencies) >= set(attributes):
                result.append(group)
    return set(result)


markup = (BASE / 'normalization.html').read_text(encoding='utf-8')
parser = Relations()
parser.feed(markup)
tables = parser.tables
assert len(tables) == 18
enrollment = tables['enrollment-1nf']
assert canonical(enrollment) == canonical(tables['enrollment-before-2nf'])
fds = [(['학번'], ['학생이름']), (['과목'], ['강사번호']),
       (['강사번호'], ['강사전화']), (['학번', '과목'], ['성적'])]
assert all(dependency(enrollment, left, right) for left, right in fds)
assert keys(list(enrollment[0]), fds) == {frozenset(['학번', '과목'])}
for name, columns in [('student-2nf', ['학번', '학생이름']),
                      ('course-2nf', ['과목', '강사번호', '강사전화']),
                      ('enrollment-2nf', ['학번', '과목', '성적'])]:
    assert project(enrollment, columns) == canonical(tables[name]), name
assert canonical(join(join(tables['student-2nf'], tables['course-2nf']), tables['enrollment-2nf'])) == canonical(enrollment)
assert canonical(tables['course-2nf']) == canonical(tables['course-before-3nf'])
assert canonical(join(tables['course-3nf'], tables['instructor-3nf'])) == canonical(tables['course-2nf'])
assert canonical(join(join(join(tables['student-2nf'], tables['enrollment-2nf']), tables['course-3nf']), tables['instructor-3nf'])) == canonical(enrollment)

assignment = tables['assignment-before-bcnf']
fds = [(['강사번호'], ['과목']), (['학번', '과목'], ['강사번호'])]
assert all(dependency(assignment, left, right) for left, right in fds)
candidate_keys = keys(list(assignment[0]), fds)
assert candidate_keys == {frozenset(['학번', '과목']), frozenset(['학번', '강사번호'])}
prime = set().union(*candidate_keys)
assert prime == set(assignment[0])  # Every right-hand attribute is prime: satisfies 3NF.
assert closure(['강사번호'], fds) == {'강사번호', '과목'}  # Not a superkey: violates BCNF.
assert canonical(join(tables['instructor-bcnf'], tables['assignment-bcnf'])) == canonical(assignment)

profile = tables['profile-before-4nf']
assert len(profile) == 4
assert canonical(join(tables['hobby-4nf'], tables['language-4nf'])) == canonical(profile)
added = Relations(include_hidden=True)
added.feed(markup)
assert len(added.tables['profile-before-4nf']) == 6
assert len(added.tables['hobby-4nf']) == 3
assert canonical(join(added.tables['hobby-4nf'], added.tables['language-4nf'])) == canonical(added.tables['profile-before-4nf'])

delivery = tables['delivery-before-5nf']
sp, sj, pj = [tables[name] for name in ('supplier-part-5nf', 'supplier-project-5nf', 'part-project-5nf')]
for pairs in (sp, sj, pj):
    assert project(delivery, list(pairs[0])) == canonical(pairs)
assert canonical(join(join(sp, sj), pj)) == canonical(delivery)
assert canonical(join(sp, sj)) != canonical(delivery)  # Omitting the third condition creates spurious rows.
assert {'공급사': 'S1', '부품': 'P2', '현장': 'J2'} in join(sp, sj)
for group in ('공급사', '부품', '현장'):
    others = [column for column in delivery[0] if column != group]
    # There is no independent-list two-table decomposition for any single column.
    assert canonical(join([dict(row) for row in project(delivery, [group, others[0]])],
                          [dict(row) for row in project(delivery, [group, others[1]])])) != canonical(delivery)
print(json.dumps({'relation_tables': len(tables), 'candidate_keys': 'pass',
                  'lossless_2nf_3nf_bcnf_4nf_5nf': 'pass', 'independent_lists': 'pass',
                  'three_way_join_and_spurious_rows': 'pass'}, ensure_ascii=False))
