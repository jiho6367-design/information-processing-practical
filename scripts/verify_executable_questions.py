from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "exams.json"
OUTPUT_PATH = ROOT / "src" / "data" / "execution-verification.json"

EXPECTED_OUTPUTS = {
    "2024-1-05": "4",
    "2024-1-08": "Seynaau",
    "2024-1-18": "9",
    "2024-2-01": "S",
    "2024-2-02": "NNN",
    "2024-2-03": "ab3 ca3",
    "2024-2-07": "25, 20",
    "2024-2-08": "dcba",
    "2024-3-01": "OOAAA",
    "2024-3-02": "3",
    "2024-3-12": "45",
    "2024-3-14": "52",
    "2024-3-17": "101",
    "2024-3-18": "B0",
    "2025-1-05": "출력1출력5",
    "2025-1-11": "54",
    "2025-1-16": "4",
    "2025-1-18": "20",
    "2025-1-19": "13",
    "2025-2-04": "BB",
    "2025-2-09": "19",
    "2025-2-17": "2",
    "2025-2-18": "5P",
    "2025-2-19": "1a3b3",
    "2025-3-06": "AB",
    "2025-3-10": "100",
    "2025-3-11": "{0: (15, 5), 1: (10, 3), 2: (18, 5), 3: (9, 2)}",
    "2025-3-18": "100",
    "2026-1-05": "9A7A5A3A1A",
    "2026-1-06": "2",
    "2026-1-16": "veDamuH",
    "2026-1-19": "1123",
    "2026-1-20": "10",
}

PYTHON_INPUTS = {"2026-1-16": "HumanDev\n"}
PYTHON_SOURCES = {
    "2024-1-08": """
a = ['Seoul', 'Kyeonggi', 'Incheon', 'Daejeon', 'Daegu', 'Pusan']
str01 = 'S'
for i in a:
    str01 = str01 + i[1]
print(str01)
""",
    "2024-2-03": """
def cnt(string, p):
    result = 0
    for i in range(len(string)):
        sub = string[i:i+len(p)]
        if sub == p:
            result += 1
    return result
string = "abdcabcabca"
p1 = "ca"
p2 = "ab"
print(f'ab{cnt(string, p1)} ca{cnt(string, p2)}')
""",
    "2024-3-02": """
def func(lst):
    for i in range(len(lst) // 2):
        lst[i], lst[-i-1] = lst[-i-1], lst[i]
lst = [1,2,3,4,5,6]
func(lst)
print(sum(lst[::2]) - sum(lst[1::2]))
""",
    "2024-3-12": """
def func(value):
    if type(value) == type(100):
        return 100
    elif type(value) == type(""):
        return len(value)
    return 20
a = "100.0"
b = 100.0
c = (100, 200)
print(func(a) + func(b) + func(c))
""",
    "2025-1-19": """
class Node:
    def __init__(self, value):
        self.value = value
        self.children = []
def tree(li):
    nodes = [Node(i) for i in li]
    for i in range(1, len(li)):
        nodes[(i - 1) // 2].children.append(nodes[i])
    return nodes[0]
def calc(node, level=0):
    if node is None:
        return 0
    return (node.value if level % 2 == 1 else 0) + sum(
        calc(n, level + 1) for n in node.children
    )
li = [3, 5, 8, 12, 15, 18, 21]
print(calc(tree(li)))
""",
    "2025-2-17": """
lst = [1,2,3]
dst = {i: i*2 for i in lst}
s = set(dst.values())
lst[0] = 99
dst[2] = 7
s.add(99)
print(len(s & set(dst.values())))
""",
    "2025-3-11": """
data = [[3,5,2,4,1], [4,5,1], [4,4,1,5,4], [4,5]]
result = {}
for index, lis in enumerate(data):
    result[index] = (sum(lis), len(lis))
print(result)
""",
    "2026-1-05": """
lst = list(range(10))
for c in lst[::-2]:
    print(c, end='A')
print()
""",
    "2026-1-16": """
i = input()
x = []
for word in i.split():
    x.append(word)
y = ' '.join(x)
z = ''.join(c for c in y[::-1] if c not in 'ong')
print(z)
""",
    "2026-1-20": """
def f(a):
    m = [[x] for x in a]
    b = m[:]
    for i in range(len(b) - 1):
        b[i+1] += b[i]
    return sum(len(x) for x in m)
print(f([1, 2, 3, 4]))
""",
}
JAVA_REPAIRS = {
    "2025-3-10": [(r"class\s+Test\s*\(\s*\)\s*Cals", "class Test implements Cals")],
    "2025-3-18": [(r"\(\s*\)\s*\(a,\s*a\);", "super(a, a);")],
}


def normalize_output(value: str) -> str:
    return value.replace("\r\n", "\n").strip()


def code_text(question: dict[str, object]) -> str:
    for block in question["promptBlocks"]:
        if block["type"] == "code":
            return str(block["text"])
    raise ValueError(f"{question['id']}: code block not found")


def run_python(question: dict[str, object]) -> tuple[bool, str]:
    question_id = str(question["id"])
    completed = subprocess.run(
        [sys.executable, "-c", PYTHON_SOURCES[question_id]],
        input=PYTHON_INPUTS.get(question_id, ""),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        return False, completed.stderr.strip()
    actual = normalize_output(completed.stdout)
    expected = EXPECTED_OUTPUTS[question_id]
    return actual == expected, actual


def run_java(question: dict[str, object], javac: str, java: str) -> tuple[bool, str]:
    question_id = str(question["id"])
    source = code_text(question)
    for pattern, replacement in JAVA_REPAIRS.get(question_id, []):
        source = re.sub(pattern, replacement, source)
    class_match = re.search(r"public\s+class\s+(\w+)", source)
    if not class_match:
        class_match = re.search(r"\bclass\s+(Main)\b", source)
    if not class_match:
        return False, "main class not found"
    class_name = class_match.group(1)
    with tempfile.TemporaryDirectory(prefix="practical-java-") as temp_dir:
        source_path = Path(temp_dir) / f"{class_name}.java"
        source_path.write_text(source, encoding="utf-8")
        compiled = subprocess.run(
            [javac, "-encoding", "UTF-8", str(source_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
        if compiled.returncode != 0:
            return False, compiled.stderr.strip()
        completed = subprocess.run(
            [
                java,
                "-Dfile.encoding=UTF-8",
                "-Dsun.stdout.encoding=UTF-8",
                "-Dstdout.encoding=UTF-8",
                "-cp",
                temp_dir,
                class_name,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    if completed.returncode != 0:
        return False, completed.stderr.strip()
    actual = normalize_output(completed.stdout)
    expected = EXPECTED_OUTPUTS[question_id]
    return actual == expected, actual


def verify_sql(question_id: str) -> tuple[bool, str]:
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    try:
        if question_id == "2024-1-12":
            cursor.executescript(
                """
                CREATE TABLE R1(A INTEGER, B TEXT, C TEXT);
                CREATE TABLE R2(C TEXT, D TEXT, E TEXT);
                INSERT INTO R1 VALUES (1,'a','x'),(2,'b','y'),(3,'c','t');
                INSERT INTO R2 VALUES ('x','k','k'),('y','k','t'),('z','p','k');
                """
            )
            result = cursor.execute(
                "SELECT B FROM R1 WHERE C IN (SELECT C FROM R2 WHERE D='k')"
            ).fetchall()
            actual = repr(result)
            return result == [("a",), ("b",)], actual
        if question_id == "2024-1-17":
            cursor.executescript(
                "CREATE TABLE EMP_TBL(EMPNO INTEGER, SAL INTEGER);"
                "INSERT INTO EMP_TBL VALUES (100,1500),(200,3000),(300,2000);"
            )
            result = cursor.execute(
                "SELECT COUNT(*) FROM EMP_TBL "
                "WHERE EMPNO > 100 AND SAL >= 3000 OR EMPNO = 200"
            ).fetchone()[0]
            return result == 1, str(result)
        if question_id == "2024-2-10":
            cursor.executescript(
                """
                CREATE TABLE 학부(학번 INTEGER PRIMARY KEY, 이름 TEXT, 주소 TEXT, 나이 INTEGER);
                CREATE TABLE 학생(학번 INTEGER PRIMARY KEY, 이름 TEXT, 나이 INTEGER, 학과 TEXT);
                INSERT INTO 학부(학번,이름,주소,나이) VALUES (240912,'최재균','서울',20);
                INSERT INTO 학생(학번,이름,나이,학과)
                  SELECT 학번,이름,나이,'컴퓨터공학' FROM 학부 WHERE 이름='최재균';
                UPDATE 학생 SET 학과='휴학' WHERE 학번=240912;
                """
            )
            result = cursor.execute("SELECT 학과 FROM 학생").fetchone()[0]
            return result == "휴학", result
        if question_id == "2024-3-03":
            cursor.executescript(
                """
                CREATE TABLE employee(no INTEGER, first_name TEXT, last_name TEXT, project_id INTEGER);
                CREATE TABLE project(project_id INTEGER, name TEXT);
                INSERT INTO employee VALUES
                  (1,'John','Doe',10),(2,'Jim','Carry',20),(3,'Rachel','Redmond',10);
                INSERT INTO project VALUES (10,'Alpha'),(20,'Beta'),(10,'Gamma');
                """
            )
            result = cursor.execute(
                """
                SELECT count(*) FROM employee AS e
                JOIN project AS p ON e.project_id=p.project_id
                WHERE p.name IN (
                  SELECT name FROM project WHERE project_id IN (
                    SELECT project_id FROM employee
                    GROUP BY project_id HAVING count(*) < 2
                  )
                )
                """
            ).fetchone()[0]
            return result == 1, str(result)
        if question_id == "2025-1-06":
            cursor.executescript(
                """
                CREATE TABLE emp(id INTEGER, name TEXT);
                CREATE TABLE sal(id INTEGER, incentive INTEGER);
                INSERT INTO emp VALUES (1002,'홍길동'),(1004,'강감찬'),(1006,'김유신'),(1008,'이순신');
                INSERT INTO sal VALUES (1002,300),(1004,400),(1008,1000),(1009,500);
                """
            )
            result = cursor.execute(
                "SELECT name,incentive FROM emp,sal "
                "WHERE emp.id=sal.id AND incentive>=500"
            ).fetchall()
            return result == [("이순신", 1000)], repr(result)
        if question_id == "2025-3-07":
            cursor.executescript(
                """
                CREATE TABLE A(NAME TEXT);
                CREATE TABLE B(RULE TEXT);
                INSERT INTO A VALUES ('Smith'),('Allen'),('Scott');
                INSERT INTO B VALUES ('S%'),('%T%');
                """
            )
            result = cursor.execute(
                "SELECT COUNT(*) FROM A CROSS JOIN B WHERE A.NAME LIKE B.RULE"
            ).fetchone()[0]
            return result == 4, str(result)
        if question_id == "2025-3-20":
            cursor.executescript(
                """
                CREATE TABLE A(COL1 INTEGER, COL2 INTEGER);
                INSERT INTO A VALUES (2,NULL),(3,6),(2,3),(NULL,3),(4,5);
                """
            )
            result = cursor.execute(
                "SELECT COUNT(COL2) FROM A "
                "WHERE COL1 IN (2,3) OR COL2 IN (3,5)"
            ).fetchone()[0]
            return result == 4, str(result)
        if question_id == "2026-1-04":
            cursor.executescript(
                """
                PRAGMA foreign_keys=ON;
                CREATE TABLE TEAM(TEAM_ID2 CHAR(3) PRIMARY KEY);
                CREATE TABLE PLAYER(
                  PLAYER_ID CHAR(7) NOT NULL,
                  PLAYER_NAME VARCHAR(20) NOT NULL,
                  TEAM_ID CHAR(3) NOT NULL,
                  PRIMARY KEY(PLAYER_ID),
                  CONSTRAINT TEAM_TF FOREIGN KEY(TEAM_ID) REFERENCES TEAM(TEAM_ID2)
                );
                """
            )
            return True, "CREATE TABLE accepted"
        if question_id == "2026-1-11":
            cursor.executescript(
                """
                CREATE TABLE EMPLOYEE(emp_id TEXT, emp_name TEXT, dep_id TEXT);
                CREATE TABLE DEPT(dep_id TEXT, dep_name TEXT, budget INTEGER);
                INSERT INTO EMPLOYEE VALUES
                  ('E01','김은소','D01'),('E02','강동준','D02'),
                  ('E03','고회식','D03'),('E04','황진주','D04');
                INSERT INTO DEPT VALUES
                  ('D01','총무부',3000),('D02','인사부',5000),
                  ('D03','개발부',7000),('D04','영업부',9000);
                """
            )
            result = cursor.execute(
                """
                SELECT COUNT(*) FROM EMPLOYEE e JOIN DEPT d ON e.dep_id=d.dep_id
                WHERE d.budget > (SELECT AVG(budget) FROM DEPT)
                """
            ).fetchone()[0]
            return result == 2, str(result)
        if question_id == "2026-1-18":
            cursor.execute("CREATE TABLE STUDENT(DEPT TEXT)")
            cursor.executemany(
                "INSERT INTO STUDENT VALUES (?)",
                [("전기과",)] * 50 + [("전산과",)] * 100 + [("전자과",)] * 50,
            )
            results = (
                len(cursor.execute("SELECT DEPT FROM STUDENT").fetchall()),
                len(cursor.execute("SELECT DISTINCT DEPT FROM STUDENT").fetchall()),
                cursor.execute(
                    "SELECT COUNT(DISTINCT DEPT) FROM STUDENT WHERE DEPT='전산과'"
                ).fetchone()[0],
            )
            return results == (200, 3, 1), repr(results)
    finally:
        connection.close()
    return False, "SQL verifier not implemented"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    questions = {
        question["id"]: question
        for exam in data["exams"]
        for question in exam["questions"]
    }
    javac = shutil.which("javac")
    java = str(Path(javac).with_name("java.exe")) if javac else ""
    results: dict[str, dict[str, object]] = {}

    for question_id, expected in EXPECTED_OUTPUTS.items():
        question = questions[question_id]
        language = question["language"]
        if language == "Python":
            passed, actual = run_python(question)
        elif language == "Java":
            if not javac or not Path(java).exists():
                passed, actual = False, "JDK not found"
            else:
                passed, actual = run_java(question, javac, java)
        else:
            passed, actual = False, f"unsupported execution language: {language}"
        results[question_id] = {
            "passed": passed,
            "language": language,
            "expected": expected,
            "actual": actual,
        }

    sql_ids = sorted(
        question_id
        for question_id, question in questions.items()
        if question["language"] == "SQL"
    )
    for question_id in sql_ids:
        passed, actual = verify_sql(question_id)
        results[question_id] = {
            "passed": passed,
            "language": "SQL",
            "expected": questions[question_id]["answer"],
            "actual": actual,
        }

    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = {
        question_id: result
        for question_id, result in results.items()
        if not result["passed"]
    }
    if failed:
        for question_id, result in failed.items():
            print(f"{question_id}: {result['actual']}")
        raise SystemExit(f"Execution verification failed: {len(failed)}")
    print(
        f"Execution verification passed: {len(results)} questions "
        f"({sum(r['language'] == 'Java' for r in results.values())} Java, "
        f"{sum(r['language'] == 'Python' for r in results.values())} Python, "
        f"{sum(r['language'] == 'SQL' for r in results.values())} SQL)."
    )


if __name__ == "__main__":
    main()
