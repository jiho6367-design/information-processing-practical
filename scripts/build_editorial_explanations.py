from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "exams.json"
EXECUTION_PATH = ROOT / "src" / "data" / "execution-verification.json"
OUTPUT_DIR = ROOT / "src" / "data" / "editorial"

SOURCE = json.loads(DATA_PATH.read_text(encoding="utf-8"))
EXECUTION_RESULTS = (
    json.loads(EXECUTION_PATH.read_text(encoding="utf-8"))
    if EXECUTION_PATH.exists()
    else {}
)
QUESTIONS = {
    question["id"]: question
    for exam in SOURCE["exams"]
    for question in exam["questions"]
}
EDITORIAL: dict[str, dict[str, object]] = {}


def _as_list(value: str | Iterable[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def general(
    question_id: str,
    concept: str,
    steps: Iterable[str],
    *,
    rules: str | Iterable[str],
    distinctions: str | Iterable[str],
    pitfalls: str | Iterable[str],
    takeaway: str,
) -> None:
    question = QUESTIONS[question_id]
    EDITORIAL[question_id] = {
        "status": "authored",
        "kind": "general",
        "answerSummary": question["answer"],
        "concept": concept,
        "rules": _as_list(rules),
        "steps": list(steps),
        "distinctions": _as_list(distinctions),
        "pitfalls": _as_list(pitfalls),
        "takeaway": takeaway,
        "verification": {
            "method": "source-cross-checked",
            "note": "문제의 정의·보기와 정답을 독립적으로 연결한 뒤 PDF 정답과 대조했습니다.",
        },
    }


def code(
    question_id: str,
    concept: str,
    steps: Iterable[str],
    trace_rows: Iterable[Iterable[str]],
    *,
    rules: str | Iterable[str],
    output_moment: str,
    calculation: str,
    pitfalls: str | Iterable[str],
    takeaway: str,
    distinctions: str | Iterable[str] = (),
    object_flow: Iterable[str] = (),
    executed: bool = False,
    status: str = "authored",
    verification_note: str | None = None,
) -> None:
    question = QUESTIONS[question_id]
    language = question.get("language")
    executed = bool(EXECUTION_RESULTS.get(question_id, {}).get("passed"))
    EDITORIAL[question_id] = {
        "status": status,
        "kind": "sql" if language == "SQL" else "code",
        "answerSummary": question["answer"],
        "concept": concept,
        "rules": _as_list(rules),
        "steps": list(steps),
        "distinctions": list(distinctions),
        "trace": {
            "headers": ["단계", "확인한 값", "누적·결과"],
            "rows": [list(row) for row in trace_rows],
        },
        "outputMoment": output_moment,
        "calculation": calculation,
        "objectFlow": list(object_flow),
        "pitfalls": _as_list(pitfalls),
        "takeaway": takeaway,
        "verification": {
            "method": (
                "executed-and-cross-checked"
                if executed
                else "hand-traced-and-cross-checked"
            ),
            "note": (
                verification_note
                or (
                    "안전하게 실행해 출력값을 확인하고 손 계산 및 PDF 정답과 대조했습니다."
                    if executed
                    else "문장을 손으로 추적해 중간 값을 계산하고 PDF 정답과 대조했습니다."
                )
            ),
        },
    }


# 2024년 1회
code(
    "2024-1-01",
    "삼항 연산자의 조건값과 왼쪽 시프트",
    [
        "삼항식 `v1 > v2 ? v2 : v1`의 조건은 `0 > 35`이므로 거짓이고, 식 전체의 값은 v1인 0입니다.",
        "if가 받은 값 0은 거짓이므로 else가 실행되어 v3만 왼쪽으로 2비트 이동합니다.",
        "마지막에 그대로인 v2와 바뀐 v3를 더합니다.",
    ],
    [
        ("초기", "v1=0, v2=35, v3=29", "-"),
        ("삼항식", "조건 거짓 → 값 0", "else 선택"),
        ("시프트", "v3 = 29 << 2", "v3=116"),
        ("출력", "35 + 116", "151"),
    ],
    rules=["C에서 0은 거짓, 0이 아닌 값은 참입니다.", "`x << 2`는 x에 4를 곱한 것과 같습니다."],
    output_moment="printf가 v2+v3을 계산할 때 결과가 확정됩니다.",
    calculation="35 + (29×4) = 151",
    pitfalls="삼항식이 v1에 값을 대입하는 문장이 아니라, if의 조건값을 만드는 식이라는 점을 놓치기 쉽습니다.",
    takeaway="삼항식의 결과가 0이어서 v3만 116으로 바뀌고 최종 출력은 151입니다.",
    executed=True,
)
general(
    "2024-1-02",
    "링크 상태 라우팅 프로토콜 OSPF",
    [
        "‘Dijkstra 최단 경로’와 ‘링크 상태를 실시간 반영’이라는 단서를 먼저 잡습니다.",
        "거리 벡터 방식인 RIP가 아니라 링크 상태 방식이며 대규모망에 적합한 OSPF로 연결합니다.",
    ],
    rules="OSPF는 링크 상태 정보를 공유하고 SPF(Dijkstra) 알고리즘으로 최단 경로를 계산합니다.",
    distinctions="RIP는 홉 수를 기준으로 하는 거리 벡터 방식이고, OSPF는 링크 비용을 사용하는 링크 상태 방식입니다.",
    pitfalls="‘최단 경로’라는 말만 보고 모든 라우팅 프로토콜을 답하지 말고 Dijkstra 단서를 확인해야 합니다.",
    takeaway="Dijkstra·링크 상태·대규모 네트워크가 함께 나오면 OSPF입니다.",
)
general(
    "2024-1-03",
    "이행적 함수 종속을 제거하는 제3정규형",
    [
        "그림에서 기본키가 아닌 속성이 다른 일반 속성을 결정하는지 확인합니다.",
        "기본키 → 일반 속성 → 또 다른 일반 속성처럼 이어지는 이행적 종속을 분해하는 단계는 제3정규형입니다.",
    ],
    rules="제3정규형은 제2정규형을 만족하면서 기본키가 아닌 속성 사이의 이행적 함수 종속을 제거합니다.",
    distinctions="부분 함수 종속 제거는 제2정규형, 결정자가 모두 후보키가 되게 하는 것은 BCNF입니다.",
    pitfalls="부분 종속과 이행 종속을 바꾸어 외우지 않도록 ‘2NF=부분, 3NF=이행’으로 구분합니다.",
    takeaway="일반 속성이 다른 일반 속성을 결정하는 연결을 끊으면 제3정규형입니다.",
)
general(
    "2024-1-04",
    "모듈 응집도의 강한 순서",
    [
        "한 가지 기능만 수행하는 기능적 응집도를 가장 높게 둡니다.",
        "같은 데이터를 다루는 교환적, 같은 시점에 수행되는 시간적, 우연히 모인 우연적 순으로 내려갑니다.",
    ],
    rules="응집도는 모듈 내부 요소가 한 목적에 얼마나 밀접한지를 나타내며 높을수록 좋습니다.",
    distinctions="교환적은 ‘같은 입출력 데이터’, 시간적은 ‘같은 실행 시점’, 우연적은 ‘관련 없음’이 핵심입니다.",
    pitfalls="결합도는 낮을수록 좋지만 응집도는 높을수록 좋다는 방향을 뒤집지 않아야 합니다.",
    takeaway="기능적 > 교환적 > 시간적 > 우연적, 즉 ㉠→㉡→㉣→㉢입니다.",
)
code(
    "2024-1-05",
    "싱글턴 객체가 공유하는 인스턴스 필드",
    [
        "첫 get()에서 Connection 객체를 한 번 만들고 `_inst`에 보관합니다.",
        "이후 conn1, conn2, conn3은 새 객체가 아니라 모두 같은 `_inst`를 가리킵니다.",
        "count()가 총 네 번 호출되므로 그 하나의 객체 안 count가 4가 됩니다.",
    ],
    [
        ("객체 생성", "conn1 → Connection#1", "count=0"),
        ("conn1.count", "Connection#1", "count=1"),
        ("conn2·conn3", "둘 다 Connection#1", "count=3"),
        ("마지막 conn1.count", "Connection#1", "count=4"),
    ],
    rules=["static `_inst`는 클래스 전체에서 하나만 공유됩니다.", "참조 변수가 달라도 같은 객체를 가리킬 수 있습니다."],
    output_moment="conn1.getCount()는 세 참조가 함께 바꾼 단 하나의 count를 읽습니다.",
    calculation="1 + 1 + 1 + 1 = 4회 증가",
    pitfalls="conn1·conn2·conn3마다 count가 따로 있다고 생각하면 안 됩니다.",
    takeaway="싱글턴의 세 참조는 한 객체를 공유하므로 출력은 4입니다.",
    object_flow=["conn1 ─┐", "conn2 ─┼→ Connection#1 { count: 4 }", "conn3 ─┘"],
    executed=True,
)
general(
    "2024-1-06",
    "연관 객체군을 함께 만드는 Abstract Factory",
    [
        "‘구체 클래스에 의존하지 않는다’는 생성 인터페이스 단서를 찾습니다.",
        "서로 연관된 여러 객체를 제품군 단위로 만들고 통째로 교체한다는 설명을 Abstract Factory와 연결합니다.",
    ],
    rules="Abstract Factory는 관련된 객체들의 생성 인터페이스를 제공하는 생성 패턴이며 Kit 패턴이라고도 합니다.",
    distinctions="Factory Method는 한 제품 생성을 하위 클래스에 맡기고, Abstract Factory는 여러 관련 제품군을 함께 만듭니다.",
    pitfalls="이름에 Factory가 들어간 두 패턴을 ‘한 객체’와 ‘제품군’ 기준으로 구분해야 합니다.",
    takeaway="연관된 객체들을 한 묶음으로 생성·교체하면 Abstract Factory입니다.",
)
general(
    "2024-1-07",
    "LRU와 LFU의 페이지 교체 기준",
    [
        "빈 프레임은 처음 등장한 페이지로 채우고, 이미 들어 있는 페이지는 결함 수를 늘리지 않습니다.",
        "LRU는 가장 오래 사용하지 않은 페이지를, LFU는 참조 횟수가 가장 적은 페이지를 내보내며 각 참조를 순서대로 표에 기록합니다.",
        "두 참조열을 각각 끝까지 추적하면 페이지 결함이 모두 6회입니다.",
    ],
    rules=["LRU는 최근 사용 시점, LFU는 사용 빈도를 기준으로 합니다.", "적중(hit)은 페이지 결함에 포함하지 않습니다."],
    distinctions="LRU는 ‘언제 마지막으로 썼나’, LFU는 ‘몇 번 썼나’를 본다는 차이가 있습니다.",
    pitfalls="교체가 일어난 횟수만 세지 말고 비어 있는 프레임에 처음 적재한 경우도 페이지 결함으로 셉니다.",
    takeaway="주어진 두 참조열의 LRU와 LFU 페이지 결함은 각각 6회입니다.",
)
code(
    "2024-1-08",
    "문자열의 두 번째 글자를 이어 붙이는 반복문",
    [
        "str01은 먼저 `S`로 시작합니다.",
        "목록의 각 도시 이름에서 인덱스 1, 즉 두 번째 글자만 꺼내 차례로 덧붙입니다.",
        "모든 문자열을 처리한 뒤 완성된 한 문자열을 출력합니다.",
    ],
    [
        ("초기", "str01='S'", "S"),
        ("Seoul, Kyeonggi", "e, y", "Sey"),
        ("Incheon, Daejeon", "n, a", "Seyna"),
        ("Daegu, Pusan", "a, u", "Seynaau"),
    ],
    rules="Python 문자열 인덱스는 0부터 시작하므로 `i[1]`은 두 번째 문자입니다.",
    output_moment="for문이 끝난 뒤 print(str01)에서 누적 문자열 전체를 출력합니다.",
    calculation="'S'+'e'+'y'+'n'+'a'+'a'+'u' = 'Seynaau'",
    pitfalls="i를 숫자 인덱스로 착각하지 말고, 반복할 때마다 i가 도시 이름 문자열이라는 점을 확인합니다.",
    takeaway="각 도시의 두 번째 문자만 이어 붙여 Seynaau가 됩니다.",
    executed=True,
)
general(
    "2024-1-09",
    "세타 조인에서 자연 조인까지의 포함 관계",
    [
        "비교 연산자로 조건을 만족하는 튜플을 고르는 가장 넓은 개념은 세타 조인입니다.",
        "그중 비교 연산자가 `=`인 경우가 동등 조인입니다.",
        "동등 조인 결과에서 중복된 공통 속성 하나를 제거하면 자연 조인입니다.",
    ],
    rules="세타 조인 ⊃ 동등 조인이며, 자연 조인은 동등 조인의 중복 공통 속성을 제거한 형태입니다.",
    distinctions="동등 조인은 같은 이름의 속성이 결과에 두 번 남을 수 있지만 자연 조인은 하나만 남깁니다.",
    pitfalls="자연 조인과 동등 조인을 모두 등호 조건으로만 기억하면 중복 속성 제거 여부를 놓칩니다.",
    takeaway="① 세타 조인, ② 동등 조인, ③ 자연 조인입니다.",
)
code(
    "2024-1-10",
    "문자열 뒤집기 후 홀수 인덱스 선택",
    [
        "inverse가 양끝 문자를 서로 바꾸며 `ABCDEFGH`를 `HGFEDCBA`로 뒤집습니다.",
        "출력 반복문은 i=1부터 2씩 증가하므로 인덱스 1, 3, 5, 7만 방문합니다.",
        "해당 위치의 G, E, C, A를 붙여 출력합니다.",
    ],
    [
        ("뒤집기 전", "ABCDEFGH", "-"),
        ("뒤집기 후", "HGFEDCBA", "-"),
        ("i=1,3", "G, E", "GE"),
        ("i=5,7", "C, A", "GECA"),
    ],
    rules=["문자열 인덱스는 0부터 시작합니다.", "`i += 2`이므로 선택 위치는 1,3,5,7입니다."],
    output_moment="뒤집힌 배열에서 홀수 인덱스 문자만 printf가 순서대로 내보냅니다.",
    calculation="H[G]F[E]D[C]B[A] → GECA",
    pitfalls="원본 문자열의 홀수 인덱스를 뽑는 것이 아니라 먼저 전체 문자열을 뒤집는다는 순서를 지켜야 합니다.",
    takeaway="뒤집기와 인덱스 선택을 분리하면 출력 GECA를 쉽게 확인할 수 있습니다.",
    executed=True,
)
code(
    "2024-1-11",
    "상속 객체 생성과 오버로딩된 메서드 선택",
    [
        "main의 ⑤에서 시작해 ⑥의 `new Child(10)`을 평가합니다.",
        "자식 생성자 ③에 들어가지만 첫 문장 `super(...)` 때문에 부모 생성자 ①을 먼저 실행합니다.",
        "객체 생성 뒤 ⑦의 `parent.getX()`는 선언형 Parent에 정의된 매개변수 없는 getX ②를 호출합니다.",
    ],
    [
        ("시작", "main", "⑤"),
        ("객체 생성 문장", "new Child(10)", "⑥→③"),
        ("부모 초기화", "super(11,10)", "①"),
        ("호출", "parent.getX()", "⑦→②"),
    ],
    rules=["자식 생성자는 부모 생성자를 먼저 실행합니다.", "매개변수가 다른 getX(int)는 오버라이딩이 아니라 오버로딩입니다."],
    output_moment="⑦에서 매개변수 없는 getX를 호출하므로 부모의 ②가 마지막으로 실행됩니다.",
    calculation="중복 번호 없이 실행 진입 순서를 적으면 ⑤,⑥,③,①,⑦,②",
    pitfalls="③보다 ①이 먼저 ‘완료’되지만, 실행 흐름은 먼저 ③에 진입한 뒤 super로 ①에 들어간다는 문제의 번호 기준을 따라야 합니다.",
    takeaway="생성자 진입과 super 호출, 메서드 시그니처를 구분하면 순서는 ⑤→⑥→③→①→⑦→②입니다.",
    object_flow=["Parent parent → 실제 객체 Child", "Child.getX(int) ≠ Parent.getX()"],
)
code(
    "2024-1-12",
    "IN 부질의로 R1 행을 거르는 과정",
    [
        "안쪽 질의에서 R2의 D가 k인 행만 고르면 C 집합은 x와 y입니다.",
        "바깥 질의는 R1.C가 그 집합에 포함된 행, 즉 C가 x 또는 y인 행을 남깁니다.",
        "남은 두 행의 B 값 a와 b를 B 열 아래에 출력합니다.",
    ],
    [
        ("부질의", "R2.D='k'", "C={x,y}"),
        ("R1 첫 행", "C=x", "포함 → B=a"),
        ("R1 둘째 행", "C=y", "포함 → B=b"),
        ("R1 셋째 행", "C=t", "제외"),
    ],
    rules="IN은 왼쪽 값이 부질의 결과 집합 중 하나와 같으면 참입니다.",
    output_moment="SELECT B가 통과한 두 행에서 B 열만 투영합니다.",
    calculation="결과 열 이름 B, 결과 값 a와 b",
    pitfalls="부질의가 반환하는 것은 D가 아니라 C 열이라는 점을 확인해야 합니다.",
    takeaway="먼저 부질의 집합 {x,y}를 만든 뒤 R1을 대조하면 B/a/b가 나옵니다.",
)
code(
    "2024-1-13",
    "문자 종류별 순환 이동",
    [
        "각 문자를 대문자, 소문자, 숫자, 그 외 문자로 분류합니다.",
        "I는 대문자 규칙 +5로 N, 소문자 t·i·s는 +10으로 d·s·c가 됩니다.",
        "숫자 8은 +3 후 10으로 나눈 나머지 1이 되고 공백은 그대로 복사됩니다.",
    ],
    [
        ("I", "대문자 +5", "N"),
        ("t / i / s", "소문자 +10", "d / s / c"),
        ("공백", "그 외", "공백 유지"),
        ("8", "숫자 (8+3)%10", "1"),
    ],
    rules=["문자 코드를 A 또는 a 또는 0 기준의 0부터 시작하는 값으로 바꾼 뒤 이동합니다.", "공백은 어느 문자 분류에도 속하지 않아 그대로 복사됩니다."],
    output_moment="변환 배열 끝에 널 문자를 넣은 뒤 고정 문구와 문자열을 함께 출력합니다.",
    calculation="`It is 8` → `Nd sc 1`",
    pitfalls=["대문자 식만 `% 25`인 원문을 임의로 `% 26`으로 고치지 않습니다.", "출력 앞의 `변환된 문자열 : `과 공백까지 포함해야 합니다."],
    takeaway="문자별 규칙을 따로 적용한 전체 출력은 `변환된 문자열 : Nd sc 1`입니다.",
)
general(
    "2024-1-14",
    "개별 조건의 독립 효과를 확인하는 MC/DC",
    [
        "모든 결정 결과가 참·거짓이 되는지와 모든 개별 조건이 참·거짓이 되는지 확인합니다.",
        "추가로 한 조건만 바꿨을 때 전체 결정 결과가 바뀌는 독립적 영향까지 요구하므로 MC/DC입니다.",
    ],
    rules="MC/DC는 각 개별 조건이 다른 조건의 영향과 독립적으로 전체 결정 결과에 영향을 줌을 보여야 합니다.",
    distinctions="조건/결정 커버리지는 각 조건과 결정의 참·거짓만 요구하지만 독립 영향까지 보장하지는 않습니다.",
    pitfalls="‘모든 조건 조합’인 다중 조건 커버리지와 ‘각 조건의 독립 영향’인 MC/DC를 구분합니다.",
    takeaway="개별 조건의 독립적인 영향이라는 문장이 나오면 MC/DC입니다.",
)
general(
    "2024-1-15",
    "침입 흔적과 도구를 숨기는 Rootkit",
    [
        "침입 뒤 백도어·권한 획득·흔적 삭제 기능을 묶어 제공한다는 점을 확인합니다.",
        "자신과 공격자의 활동을 시스템에서 보이지 않게 숨긴다는 핵심 단서를 Rootkit과 연결합니다.",
    ],
    rules="Rootkit은 공격자가 관리자 수준 접근을 유지하면서 파일·프로세스·명령 흔적을 은폐하도록 돕는 도구 모음입니다.",
    distinctions="백도어는 우회 접속 통로 하나를 뜻하고, Rootkit은 백도어를 포함한 여러 은폐·유지 기능의 모음입니다.",
    pitfalls="원격 제어 기능만 보고 트로이목마로 답하지 말고 ‘침입 사실 은폐’에 주목합니다.",
    takeaway="권한 유지와 흔적 은폐를 함께 제공하는 도구 모음은 Rootkit입니다.",
)
general(
    "2024-1-16",
    "장기간 표적을 추적하는 APT",
    [
        "불특정 다수가 아니라 특정 기업·조직을 목표로 삼는지 확인합니다.",
        "침투 후 오래 숨어 검색·수집·유출을 단계적으로 수행한다는 특성을 APT와 연결합니다.",
    ],
    rules="APT는 Advanced Persistent Threat의 약자로, 표적형·지속형·조직적 공격입니다.",
    distinctions="일회성 악성코드 감염과 달리 APT는 거점을 확보하고 장기간 목표 정보를 빼냅니다.",
    pitfalls="공격 단계 중 하나만 보고 피싱이나 악성코드로 좁히지 말고 전체 작전의 지속성을 봅니다.",
    takeaway="특정 조직에 오래 잠복해 침투→검색→수집→유출하면 APT입니다.",
)
code(
    "2024-1-17",
    "AND 우선 계산 후 OR 결합",
    [
        "SQL에서 AND를 OR보다 먼저 묶어 각 행에 적용합니다.",
        "EMPNO가 200인 행은 왼쪽 AND 묶음도 참이고 오른쪽 `EMPNO=200`도 참이어서 포함됩니다.",
        "나머지 두 행은 두 조건 묶음 모두 거짓이므로 제외됩니다.",
    ],
    [
        ("100,1500", "왼쪽 거짓 / 오른쪽 거짓", "제외"),
        ("200,3000", "왼쪽 참 / 오른쪽 참", "포함"),
        ("300,2000", "왼쪽 거짓 / 오른쪽 거짓", "제외"),
        ("COUNT", "포함 행 1개", "1"),
    ],
    rules="SQL 논리 연산 우선순위는 일반적으로 AND가 OR보다 높습니다.",
    output_moment="WHERE를 통과한 한 행을 COUNT(*)가 셉니다.",
    calculation="통과 행 {EMPNO 200} → 1",
    pitfalls="조건을 왼쪽부터 단순히 계산하지 말고 `(A AND B) OR C`로 묶어야 합니다.",
    takeaway="AND를 먼저 적용하면 포함되는 행은 EMPNO 200 하나뿐이어서 결과는 1입니다.",
)
code(
    "2024-1-18",
    "오버라이딩된 인스턴스 메서드의 동적 호출",
    [
        "변수 st의 선언형은 firstArea지만 실제로 만든 객체는 secondArea입니다.",
        "secondArea 생성자가 부모 생성자를 호출해 x=10, y=11을 만들고, 자식 필드 bb는 3입니다.",
        "print는 오버라이딩되었으므로 실제 객체 secondArea의 print가 호출되어 bb×bb를 출력합니다.",
    ],
    [
        ("참조", "firstArea st", "실제 객체 secondArea"),
        ("부모 초기화", "x=10, y=11", "-"),
        ("자식 필드", "bb=3", "-"),
        ("동적 호출", "secondArea.print", "3×3=9"),
    ],
    rules="Java의 오버라이딩된 인스턴스 메서드는 참조 변수형이 아니라 실제 객체형으로 선택됩니다.",
    output_moment="st.print()가 secondArea.print()로 동적 바인딩되는 순간 9가 정해집니다.",
    calculation="bb × bb = 3 × 3 = 9",
    pitfalls="부모의 print가 호출되어 x+y=21이 된다고 생각하지 않도록 실제 객체형을 확인합니다.",
    takeaway="부모형 참조라도 실제 객체가 자식이면 오버라이딩된 자식 print가 실행되어 9입니다.",
    object_flow=["firstArea st → secondArea 객체", "호출 대상: secondArea.print()"],
    executed=True,
)

# 2024년 2회
code(
    "2024-2-01",
    "split 결과 배열의 인덱스",
    [
        "문자열을 T 기준으로 나누면 T 자체는 결과에 포함되지 않습니다.",
        "`ITISTESTSTRING`의 조각을 차례로 쓰면 I, IS, ES, S, RING입니다.",
        "인덱스 3은 네 번째 조각 S입니다.",
    ],
    [
        ("원문", "ITISTESTSTRING", "-"),
        ("split(\"T\")", "[I, IS, ES, S, RING]", "-"),
        ("result[3]", "네 번째 조각", "S"),
    ],
    rules="Java 배열 인덱스는 0부터 시작하며 split의 구분 문자는 결과에서 빠집니다.",
    output_moment="System.out.print(result[3])가 네 번째 조각을 출력합니다.",
    calculation="result[3] = \"S\"",
    pitfalls="사람이 세는 ‘3번째’가 아니라 인덱스 3인 ‘4번째’를 골라야 합니다.",
    takeaway="T로 나눈 배열의 네 번째 원소는 S입니다.",
    executed=True,
)
code(
    "2024-2-02",
    "배열 내용이 아닌 참조 동일성 비교",
    [
        "a, b, c는 각각 별도의 new 배열로 만들어집니다.",
        "`x == y`는 배열 요소가 같은지가 아니라 두 변수가 같은 배열 객체를 가리키는지 비교합니다.",
        "세 쌍 모두 서로 다른 객체이므로 매번 N을 출력합니다.",
    ],
    [
        ("check(a,b)", "객체 A ≠ 객체 B", "N"),
        ("check(b,c)", "객체 B ≠ 객체 C", "N"),
        ("check(a,c)", "객체 A ≠ 객체 C", "N"),
    ],
    rules="Java 배열의 `==`는 참조 동일성을 비교하며 내용 비교에는 Arrays.equals가 필요합니다.",
    output_moment="각 check 호출의 else에서 N이 하나씩 이어서 출력됩니다.",
    calculation="N + N + N = NNN",
    pitfalls="a와 b의 요소가 같다는 이유로 O라고 판단하면 안 됩니다.",
    takeaway="세 배열은 내용과 무관하게 서로 다른 객체이므로 NNN입니다.",
    object_flow=["a → int[]#1", "b → int[]#2", "c → int[]#3"],
    executed=True,
)
code(
    "2024-2-03",
    "슬라이딩 부분 문자열의 등장 횟수",
    [
        "cnt는 시작 위치를 한 칸씩 옮기며 p 길이만큼 잘라 비교합니다.",
        "문자열에서 `ca`는 3번, `ab`도 3번 발견됩니다.",
        "f-string의 고정 글자 `ab`, `ca` 뒤에 서로 반대 패턴의 개수가 들어갑니다.",
    ],
    [
        ("cnt(str,\"ca\")", "ca 등장 3회", "첫 자리 ab3"),
        ("cnt(str,\"ab\")", "ab 등장 3회", "둘째 자리 ca3"),
        ("print", "공백 포함", "ab3 ca3"),
    ],
    rules="슬라이스 `str[i:i+len(p)]`는 i에서 시작하는 p 길이의 부분 문자열입니다.",
    output_moment="f-string이 두 호출 결과를 각각 고정 글자 뒤에 끼워 넣습니다.",
    calculation="`ab`+3+공백+`ca`+3 = `ab3 ca3`",
    pitfalls="표시되는 ab 뒤에는 ab의 횟수가 아니라 p1인 ca의 횟수가 들어갑니다.",
    takeaway="두 패턴이 각각 3회라서 출력은 ab3 ca3입니다.",
    executed=True,
)
general(
    "2024-2-04",
    "성능을 위해 정규화 구조를 의도적으로 되돌리는 반정규화",
    [
        "이미 정규화된 모델에 통합·중복·분리를 의도적으로 적용한다는 점을 확인합니다.",
        "조회 성능과 운영 편의는 좋아질 수 있지만 일관성과 정합성 위험이 생긴다는 양면성을 연결합니다.",
    ],
    rules="반정규화는 성능 목적 등으로 정규화 원칙을 의도적으로 위배하는 설계입니다.",
    distinctions="비정규화는 정규화되지 않은 상태를 넓게 말할 수 있고, 반정규화는 정규화된 모델을 의도적으로 조정하는 행위에 초점이 있습니다.",
    pitfalls="정규화와 반대로 보인다고 무조건 좋은 최적화는 아니며 중복 갱신 비용을 함께 봐야 합니다.",
    takeaway="성능을 위해 통합·중복·분리를 의도적으로 적용하면 반정규화입니다.",
)
code(
    "2024-2-05",
    "값 전달 함수와 switch의 fall-through",
    [
        "swap은 a와 b의 복사본만 바꾸므로 main의 a=11, b=19는 그대로입니다.",
        "switch(11)은 case 11부터 시작해 b에 2를 더합니다.",
        "break 전까지 다음 문장에도 내려가 3을 더한 뒤 a-b를 계산합니다.",
    ],
    [
        ("swap 후", "a=11, b=19", "변화 없음"),
        ("case 11", "b += 2", "b=21"),
        ("다음 문장", "b += 3", "b=24"),
        ("출력", "11-24", "-13"),
    ],
    rules=["C의 일반 매개변수는 값 전달입니다.", "case에 break가 없으면 다음 문장으로 계속 실행됩니다."],
    output_moment="printf가 바뀌지 않은 a와 누적된 b의 차를 계산합니다.",
    calculation="11 - (19+2+3) = -13",
    pitfalls="swap이 main 변수를 바꾼다고 생각하거나 case 11 뒤에서 자동으로 멈춘다고 생각하기 쉽습니다.",
    takeaway="값 전달과 fall-through를 함께 적용하면 -13입니다.",
)
code(
    "2024-2-06",
    "포인터로 문자열 복사 후 인덱스 합산",
    [
        "func는 str1의 `first`를 str2 배열에 문자별로 복사하고 끝에 널 문자를 넣습니다.",
        "str2의 유효 길이는 5가 되어 반복 인덱스는 0부터 4까지입니다.",
        "result에 이 인덱스들을 모두 더합니다.",
    ],
    [
        ("복사", "str2=\"first\"", "길이 5"),
        ("i=0,1,2", "인덱스 누적", "3"),
        ("i=3,4", "인덱스 누적", "10"),
    ],
    rules="C 문자열은 널 문자 전까지가 내용이며, 포인터 증가로 다음 문자를 가리킵니다.",
    output_moment="for문 종료 후 result를 출력합니다.",
    calculation="0+1+2+3+4 = 10",
    pitfalls="기존 `teststring` 뒤쪽 문자는 새 널 문자 때문에 문자열로 읽히지 않습니다.",
    takeaway="복사된 first의 인덱스 합은 10입니다.",
    executed=True,
)
code(
    "2024-2-07",
    "논리 조건으로 홀수와 짝수를 나눠 합산",
    [
        "odd가 true이면 첫 조건이 켜져 홀수만 result에 더합니다.",
        "odd가 false이면 두 번째 조건이 켜져 짝수만 더합니다.",
        "1~9의 홀수 합과 짝수 합을 쉼표·공백 형식으로 출력합니다.",
    ],
    [
        ("odd=true", "1+3+5+7+9", "25"),
        ("odd=false", "2+4+6+8", "20"),
        ("출력", "25 + \", \" + 20", "25, 20"),
    ],
    rules="`&&`가 `||`보다 먼저 계산되므로 두 괄호가 홀수 선택과 짝수 선택을 각각 담당합니다.",
    output_moment="두 sum 반환값을 문자열 `, ` 사이에 이어 출력합니다.",
    calculation="홀수합 25, 짝수합 20",
    pitfalls="odd라는 boolean 값 자체를 더하는 것이 아니라 조건에 맞는 배열 원소를 더합니다.",
    takeaway="true는 홀수합 25, false는 짝수합 20을 돌려줍니다.",
    executed=True,
)
code(
    "2024-2-08",
    "재귀 복귀 과정에서 중복 문자를 제거하는 순서",
    [
        "호출은 문자열 끝에서 시작하지만 먼저 index-1 재귀를 끝까지 내려갑니다.",
        "복귀는 왼쪽 문자부터 처리되며 seen에 처음 나온 문자만 기록합니다.",
        "새 문자를 앞에 붙이는 `c + result` 때문에 최종 고유 문자 순서는 거꾸로 쌓입니다.",
    ],
    [
        ("왼쪽부터 복귀", "a 처음", "a"),
        ("b 처음", "b + a", "ba"),
        ("a 중복, c 처음", "c + ba", "cba"),
        ("마지막 d 처음", "d + cba", "dcba"),
    ],
    rules=["재귀 호출 뒤의 코드는 가장 깊은 호출부터 역순으로 복귀합니다.", "seen[c]는 해당 문자를 이미 사용했는지 저장합니다."],
    output_moment="마지막 d가 아직 보이지 않았으므로 기존 cba 앞에 붙어 dcba가 됩니다.",
    calculation="고유 문자 발견 a→b→c→d, 앞붙이기 결과 a→ba→cba→dcba",
    pitfalls="끝에서 호출을 시작했다는 사실만 보고 즉시 d부터 처리한다고 생각하면 안 됩니다. 재귀 호출이 먼저입니다.",
    takeaway="왼쪽부터 고유 문자를 확인하되 앞에 붙이므로 결과는 dcba입니다.",
)
code(
    "2024-2-09",
    "2차원 배열 행 포인터의 역참조",
    [
        "parr[0]은 arr[1] 즉 두 번째 행, parr[1]은 arr[2] 즉 세 번째 행을 가리킵니다.",
        "parr[1][1]은 8, *(parr[1]+2)는 9입니다.",
        "**parr는 parr[0]이 가리키는 행의 첫 값 4입니다.",
    ],
    [
        ("parr[1][1]", "arr[2][1]", "8"),
        ("*(parr[1]+2)", "arr[2][2]", "9"),
        ("**parr", "arr[1][0]", "4"),
        ("합", "8+9+4", "21"),
    ],
    rules="2차원 배열에서 한 행의 이름은 그 행 첫 원소를 가리키는 포인터처럼 사용됩니다.",
    output_moment="printf의 세 피연산자를 모두 읽어 더할 때 21이 됩니다.",
    calculation="8 + 9 + 4 = 21",
    pitfalls="parr의 길이가 2여도 parr[1]이 원본 배열의 세 번째 행을 가리킨다는 매핑을 놓치지 않습니다.",
    takeaway="포인터 식을 arr[행][열]로 바꾸면 8+9+4=21입니다.",
    object_flow=["parr[0] → arr[1] = {4,5,6}", "parr[1] → arr[2] = {7,8,9}"],
    executed=True,
)
code(
    "2024-2-10",
    "INSERT·SELECT·UPDATE의 기본 SQL 문형",
    [
        "직접 나열한 한 행을 INSERT할 때 열 목록 뒤에 VALUES를 둡니다.",
        "조회 결과를 INSERT하려면 VALUES 대신 SELECT를 이어 씁니다.",
        "전체 조회는 SELECT * FROM, 값 변경은 UPDATE 테이블 SET 열=값 문형을 사용합니다.",
    ],
    [
        ("SQL 1", "직접 값 추가", "VALUES"),
        ("SQL 2", "조회 결과 추가", "SELECT"),
        ("SQL 3", "조회 대상 테이블", "FROM"),
        ("SQL 4", "변경할 열 지정", "SET"),
    ],
    rules=["INSERT는 VALUES 또는 SELECT 결과를 받을 수 있습니다.", "UPDATE에서 변경식은 SET 뒤에 씁니다."],
    output_moment="각 요구사항에 맞는 SQL 골격을 완성하면 네 빈칸이 결정됩니다.",
    calculation="① VALUES, ② SELECT, ③ FROM, ④ SET",
    pitfalls="INSERT ... SELECT에는 VALUES를 함께 쓰지 않습니다.",
    takeaway="추가값·조회·대상·변경의 키워드는 VALUES, SELECT, FROM, SET입니다.",
)
general(
    "2024-2-11",
    "튜플 수인 카디널리티와 속성 수인 디그리",
    [
        "회원 테이블의 데이터 행을 세면 5개이므로 카디널리티는 5입니다.",
        "ID·이름·거주지·신청강의 열을 세면 4개이므로 디그리는 4입니다.",
    ],
    rules="카디널리티는 튜플(행)의 수, 디그리는 속성(열)의 수입니다.",
    distinctions="행은 가로 한 건, 열은 세로 항목이라는 방향으로 구분하면 헷갈리지 않습니다.",
    pitfalls="표 머리글을 튜플 수에 포함하거나 카디널리티와 디그리를 반대로 쓰지 않습니다.",
    takeaway="5행 4열이므로 카디널리티 5, 디그리 4입니다.",
)
general(
    "2024-2-12",
    "IP 계층에서 패킷을 보호하는 IPsec",
    [
        "보호 대상이 IP 패킷이며 네트워크 계층에서 동작한다는 단서를 확인합니다.",
        "AH·ESP·SA·IKE 구성 요소를 IPsec과 연결합니다.",
    ],
    rules="IPsec은 인증·무결성·기밀성·재전송 방지를 IP 계층에서 제공합니다.",
    distinctions="SSL/TLS는 주로 전송 계층 위에서 응용 통신을 보호하고, IPsec은 IP 패킷 자체를 보호합니다.",
    pitfalls="구성 요소 AH와 ESP가 함께 나오면 VPN이라는 넓은 용어보다 IPsec을 답해야 합니다.",
    takeaway="AH·ESP·SA·IKE가 보이면 IPsec입니다.",
)
general(
    "2024-2-13",
    "128비트 블록의 대칭키 표준 AES",
    [
        "NIST가 DES의 대체 표준으로 2001년에 발표했다는 단서를 찾습니다.",
        "128비트 블록과 128·192·256비트 키 길이를 AES와 연결합니다.",
    ],
    rules="AES는 같은 키로 암호화·복호화하는 대칭키 블록 암호입니다.",
    distinctions="DES는 64비트 블록과 짧은 키 때문에 한계가 있고, AES는 128비트 블록을 사용합니다.",
    pitfalls="키 길이 128이라는 말과 블록 크기 128을 섞지 말고, AES는 키가 128·192·256 세 종류임을 기억합니다.",
    takeaway="NIST·DES 대체·128비트 블록이면 AES입니다.",
)
general(
    "2024-2-14",
    "연결형 가상 회선과 비연결형 데이터그램",
    [
        "통신 전에 경로를 미리 정하고 논리적으로 고정하면 가상 회선 방식입니다.",
        "접속 절차 없이 각 패킷이 충분한 경로 정보를 가지고 독립적으로 이동하면 데이터그램 방식입니다.",
    ],
    rules="가상 회선은 연결 설정 후 같은 논리 경로를 쓰고, 데이터그램은 패킷마다 독립적으로 전달됩니다.",
    distinctions="가상 회선은 순서 보장이 쉬운 반면, 데이터그램은 패킷마다 경로가 달라질 수 있습니다.",
    pitfalls="물리 회선을 실제로 독점한다는 뜻이 아니라 ‘논리적으로’ 연결된 경로라는 점을 기억합니다.",
    takeaway="경로 사전 설정은 가상 회선, 개별 패킷 전달은 데이터그램입니다.",
)
general(
    "2024-2-15",
    "앞 활동의 출력이 뒤 활동 입력이 되는 순차적 응집도",
    [
        "모듈 내부 활동들이 단순히 같은 순서로 실행되는지만 보지 않습니다.",
        "앞 활동의 출력 데이터가 다음 활동의 입력으로 직접 이어진다는 단서 때문에 순차적 응집도입니다.",
    ],
    rules="순차적 응집도는 한 기능의 출력이 다음 기능의 입력으로 연결됩니다.",
    distinctions="절차적 응집도는 실행 순서만 관련되고, 순차적 응집도는 데이터 흐름까지 이어집니다.",
    pitfalls="‘다음 활동’이라는 말만 보고 절차적으로 고르지 말고 출력→입력 연결을 확인합니다.",
    takeaway="출력이 다음 입력이 되면 순차적 응집도 ㉡입니다.",
)
general(
    "2024-2-16",
    "남은 시간이 가장 짧은 작업을 선점하는 SRT",
    [
        "도착할 때마다 현재 작업의 남은 시간과 새 프로세스 실행 시간을 비교해 간트 차트를 만듭니다.",
        "각 프로세스의 완료시간에서 도착시간과 실행시간을 빼 대기시간을 구합니다.",
        "완료시간은 B=5, D=10, A=17, C=26이고 대기시간은 A=9, B=0, C=15, D=2입니다.",
    ],
    rules="대기시간 = 완료시간 - 도착시간 - 실행시간이며 SRT는 새 작업 도착 시 선점할 수 있습니다.",
    distinctions="SJF는 비선점, SRT는 남은 시간을 비교하는 선점 방식입니다.",
    pitfalls="실행 중인 프로세스의 원래 실행시간이 아니라 현재 남은 시간을 비교해야 합니다.",
    takeaway="간트 차트로 구한 총 대기시간 26을 4로 나누면 평균 6.5입니다.",
)
general(
    "2024-2-17",
    "내부 구조를 숨기고 순차 접근을 제공하는 Iterator",
    [
        "컬렉션의 내부 표현을 공개하지 않는다는 조건을 확인합니다.",
        "서로 다른 자료 구조도 같은 인터페이스로 차례대로 방문하게 한다는 설명을 Iterator와 연결합니다.",
    ],
    rules="Iterator는 집합 객체의 요소에 순차 접근하는 방법을 별도 객체로 캡슐화하는 행위 패턴입니다.",
    distinctions="Observer는 상태 변화 알림, Iterator는 원소 방문 순서를 담당합니다.",
    pitfalls="자료 구조 자체를 만드는 패턴이 아니라 기존 구조를 순회하는 방법을 제공하는 패턴입니다.",
    takeaway="내부 표현을 숨긴 채 동일한 순회 인터페이스를 제공하면 Iterator입니다.",
)
general(
    "2024-2-18",
    "제어 정보를 넘기는 제어 결합도",
    [
        "모듈이 단순 데이터가 아니라 다른 모듈의 처리 방향을 정하는 신호를 넘기는지 확인합니다.",
        "하위 모듈이 상위 모듈에 처리 명령을 내리는 권리 전도까지 언급되므로 제어 결합도입니다.",
    ],
    rules="제어 결합도는 플래그·스위치 같은 제어 요소를 매개변수로 전달합니다.",
    distinctions="자료 결합은 필요한 단순 데이터만 전달하고, 제어 결합은 상대 모듈의 흐름을 결정합니다.",
    pitfalls="전역 데이터를 함께 쓰는 공통 결합과 제어 신호를 전달하는 제어 결합을 구분합니다.",
    takeaway="처리 방향을 지시하는 신호를 넘기면 제어 결합도 ㉢입니다.",
)
code(
    "2024-2-19",
    "연결 리스트의 next 포인터 따라가기",
    [
        "head는 a의 주소를 가리킵니다.",
        "a.Next는 b를 가리키므로 `head->Next`는 b입니다.",
        "그 노드의 data를 읽으면 20입니다.",
    ],
    [
        ("head", "&a", "data=10"),
        ("head->Next", "&b", "data=20"),
        ("출력", "b.data", "20"),
    ],
    rules="`p->field`는 포인터 p가 가리키는 구조체의 field에 접근합니다.",
    output_moment="printf가 head의 다음 노드 data를 읽습니다.",
    calculation="head → a → b, b.data=20",
    pitfalls="두 번 다음으로 가는 식이 아니라 Next는 한 번, 그 뒤 data를 읽는 식입니다.",
    takeaway="head의 바로 다음 노드는 b이므로 출력은 20입니다.",
    object_flow=["head → a(10) → b(20) → c(30)"],
    executed=True,
)
general(
    "2024-2-20",
    "RIP의 링크 가중치 합으로 찾는 최단 경로",
    [
        "그림에서 A에서 F로 갈 수 있는 각 후보 경로를 나열합니다.",
        "각 경로의 링크 가중치를 모두 더해 비교하고 가장 작은 합의 경로를 고릅니다.",
        "그림의 가중치를 합산하면 A→D→C→F가 최소입니다.",
    ],
    rules="문제에서 링크 숫자를 비용으로 제시했으므로 경로별 비용 합을 비교합니다.",
    distinctions="실제 RIP는 홉 수를 메트릭으로 쓰지만, 이 문항은 그림에 제시한 가중치 기준을 따릅니다.",
    pitfalls="중간 링크 하나가 작다는 이유로 고르지 말고 출발부터 도착까지 전체 합을 비교합니다.",
    takeaway="전체 비용이 가장 작은 경로는 A→D→C→F입니다.",
)

# 2024년 3회
code(
    "2024-3-01",
    "문자열 내용 비교와 배열 순회",
    [
        "x[0], x[1], x[2]는 객체 생성 방식은 달라도 문자열 내용이 모두 A입니다.",
        "equals는 참조가 아닌 문자열 내용을 비교하므로 인접한 두 비교가 모두 참입니다.",
        "두 O를 출력한 뒤 향상된 for문으로 A를 세 번 이어 출력합니다.",
    ],
    [
        ("x[0] vs x[1]", "\"A\".equals(\"A\")", "O"),
        ("x[1] vs x[2]", "내용 A와 A", "O"),
        ("배열 순회", "A, A, A", "AAA"),
        ("전체", "OO + AAA", "OOAAA"),
    ],
    rules="String.equals는 내용 비교이고 `==`는 참조 비교입니다.",
    output_moment="첫 for문의 OO 뒤에 두 번째 for문의 AAA가 줄바꿈 없이 붙습니다.",
    calculation="OO + AAA = OOAAA",
    pitfalls="`new String(\"A\")`가 별도 객체라는 이유로 equals 결과를 거짓으로 판단하면 안 됩니다.",
    takeaway="세 문자열 내용이 같으므로 비교 OO와 내용 AAA가 합쳐져 OOAAA입니다.",
    object_flow=["x[0], x[1] → interned \"A\"", "x[2] → 새 String 객체(내용은 \"A\")"],
    executed=True,
)
code(
    "2024-3-02",
    "리스트 제자리 뒤집기와 슬라이스 합",
    [
        "func는 앞뒤 원소를 교환하여 원본 lst 자체를 [6,5,4,3,2,1]로 뒤집습니다.",
        "`lst[::2]`는 인덱스 0,2,4의 6,4,2이고, `lst[1::2]`는 5,3,1입니다.",
        "두 합의 차를 계산합니다.",
    ],
    [
        ("func 후", "[6,5,4,3,2,1]", "-"),
        ("짝수 인덱스", "6+4+2", "12"),
        ("홀수 인덱스", "5+3+1", "9"),
        ("차", "12-9", "3"),
    ],
    rules=["리스트를 함수에 넘기면 같은 가변 객체를 참조합니다.", "슬라이스의 step 2는 인덱스를 두 칸씩 선택합니다."],
    output_moment="두 슬라이스의 sum 결과를 뺄 때 3이 됩니다.",
    calculation="(6+4+2) - (5+3+1) = 3",
    pitfalls="func 안에서 새 리스트를 만드는 것이 아니라 lst의 요소를 직접 교환합니다.",
    takeaway="뒤집힌 리스트의 짝수 인덱스 합 12에서 홀수 인덱스 합 9를 빼면 3입니다.",
    object_flow=["main의 lst ─→ 리스트 객체 ←─ func의 lst"],
    executed=True,
)
code(
    "2024-3-03",
    "중첩 부질의와 중복 project_id 조인",
    [
        "가장 안쪽 GROUP BY에서 직원 수가 2보다 작은 project_id는 20뿐입니다.",
        "project_id 20인 프로젝트 이름은 Beta이므로 중간 부질의 결과는 {Beta}입니다.",
        "바깥 조인 결과 중 프로젝트 이름이 Beta인 행은 Jim과 Beta의 한 행뿐입니다.",
    ],
    [
        ("GROUP BY", "10→2명, 20→1명", "project_id={20}"),
        ("프로젝트 조회", "id 20", "name={Beta}"),
        ("JOIN+WHERE", "Jim ↔ Beta", "1행"),
        ("COUNT", "통과 1행", "1"),
    ],
    rules="중첩 부질의는 가장 안쪽부터 결과 집합을 만들어 바깥 조건에 넣습니다.",
    output_moment="Beta와 조인된 한 행을 COUNT(*)가 셉니다.",
    calculation="{20} → {Beta} → 1행 → 1",
    pitfalls="project_id 10은 project 테이블에 두 행이지만 안쪽 HAVING은 employee의 직원 수를 세는 질의입니다.",
    takeaway="안쪽부터 20→Beta→한 행으로 좁혀져 결과는 1입니다.",
)
general(
    "2024-3-04",
    "가장 오래 참조되지 않은 페이지를 바꾸는 LRU",
    [
        "각 페이지 참조마다 프레임 3칸과 마지막 사용 시점을 함께 기록합니다.",
        "페이지가 이미 있으면 최근 사용 시점만 갱신하고, 없으면 결함을 1 늘립니다.",
        "프레임이 찬 뒤에는 마지막 사용이 가장 오래된 페이지를 교체해 전체 20개 참조를 추적합니다.",
    ],
    rules="초기 적재도 페이지 결함이며, 적중한 페이지는 교체하지 않고 최근 사용 정보만 갱신합니다.",
    distinctions="FIFO는 들어온 시점, LRU는 마지막으로 사용한 시점을 비교합니다.",
    pitfalls="0이나 1처럼 반복 등장하는 페이지의 최근 사용 시점을 갱신하지 않으면 결함 수가 달라집니다.",
    takeaway="참조열을 끝까지 LRU로 추적하면 페이지 결함은 12회입니다.",
)
general(
    "2024-3-05",
    "브로드캐스트 응답을 피해자에게 모으는 Smurf 공격",
    [
        "공격자가 출발지 IP를 피해자 주소로 위조한다는 점을 확인합니다.",
        "브로드캐스트로 여러 호스트에 ICMP 요청을 보내고 모든 응답을 피해자에게 집중시키는 증폭 구조를 찾습니다.",
    ],
    rules="Smurf 공격은 위조된 피해자 주소와 ICMP 브로드캐스트를 이용하는 반사·증폭 DoS입니다.",
    distinctions="SYN Flooding은 TCP 연결 대기열을 고갈시키고, Smurf는 ICMP 브로드캐스트 응답을 증폭합니다.",
    pitfalls="단순히 ICMP를 많이 보낸다는 설명보다 주소 위조와 브로드캐스트 두 단서를 함께 확인합니다.",
    takeaway="ICMP 브로드캐스트 응답이 피해자에게 몰리면 Smurf 공격입니다.",
)
code(
    "2024-3-06",
    "호출 사이에도 값을 유지하는 static 지역 변수",
    [
        "main의 x와 func의 static x는 이름만 같고 서로 다른 변수입니다.",
        "func의 x는 호출마다 초기화되지 않고 2,4,6,8로 누적됩니다.",
        "sum은 이 네 반환값을 차례로 더합니다.",
    ],
    [
        ("1회", "static x=2", "sum=2"),
        ("2회", "static x=4", "sum=6"),
        ("3회", "static x=6", "sum=12"),
        ("4회", "static x=8", "sum=20"),
    ],
    rules="static 지역 변수는 최초 한 번만 초기화되고 함수 호출이 끝나도 값을 유지합니다.",
    output_moment="네 번째 호출값 8까지 sum에 더한 뒤 printf가 20을 출력합니다.",
    calculation="2+4+6+8 = 20",
    pitfalls="main의 x++가 func의 static x를 증가시킨다고 섞어 생각하지 않습니다.",
    takeaway="func의 static x가 2씩 누적되어 반환값 합은 20입니다.",
    executed=True,
)
general(
    "2024-3-07",
    "공중망 위에 만드는 암호화된 사설망 VPN",
    [
        "인터넷 같은 공중 네트워크를 사용하지만 전용 회선처럼 안전하게 이용한다는 점을 잡습니다.",
        "IPsec·SSL로 암호화 터널을 만들고 원격지 사용자를 연결하는 기술을 VPN과 연결합니다.",
    ],
    rules="VPN은 Virtual Private Network의 약자로 공중망 위에 논리적인 사설 통신 경로를 만듭니다.",
    distinctions="전용선은 물리 회선을 임대하고, VPN은 기존 인터넷망에 암호화 터널을 구성합니다.",
    pitfalls="IPsec과 SSL은 VPN을 구현하는 방식이며 문제에서 요구하는 상위 용어는 VPN입니다.",
    takeaway="공중망을 전용선처럼 암호화해 쓰는 3글자 용어는 VPN입니다.",
)
general(
    "2024-3-08",
    "객체 사이의 책임과 상호작용을 정하는 행위 패턴",
    [
        "설명의 초점이 객체를 어떻게 만들거나 조립하는지가 아니라 서로 어떻게 행동하는지에 있는지 확인합니다.",
        "Iterator·Observer·Chain of Responsibility가 속한 분류를 행위 패턴으로 연결합니다.",
    ],
    rules="행위 패턴은 객체·클래스 사이의 알고리즘, 책임 분배, 통신 방법을 다룹니다.",
    distinctions="생성 패턴은 객체 생성, 구조 패턴은 클래스·객체 조합, 행위 패턴은 상호작용을 다룹니다.",
    pitfalls="여러 객체를 ‘분배’한다는 말만 보고 구조 패턴으로 고르지 말고 책임 분배라는 목적을 봅니다.",
    takeaway="Iterator와 Observer가 예시라면 행위(Behavioral) 패턴입니다.",
)
general(
    "2024-3-09",
    "문장·분기·조건 커버리지의 대상",
    [
        "모든 구문을 한 번 이상 실행하는 기준은 문장 커버리지입니다.",
        "전체 조건식 결과가 참과 거짓이 되게 하는 기준은 분기 커버리지입니다.",
        "각 개별 조건식이 참과 거짓이 되게 하는 기준은 조건 커버리지입니다.",
    ],
    rules="문장=실행문, 분기=결정 결과, 조건=결정 안의 개별 조건식을 대상으로 합니다.",
    distinctions="분기는 전체 결정의 True/False, 조건은 A&&B에서 A와 B 각각의 True/False를 봅니다.",
    pitfalls="분기와 조건을 모두 ‘조건문 테스트’로 뭉뚱그리지 말고 평가 단위를 확인합니다.",
    takeaway="① 문장 ㉥, ② 분기 ㉣, ③ 조건 ㉢입니다.",
)
code(
    "2024-3-10",
    "연결 리스트에서 인접 노드 값을 두 개씩 교환",
    [
        "연결 순서는 n1(1)→n3(3)→n2(2)입니다.",
        "func는 현재 노드와 다음 노드의 value만 교환하므로 첫 쌍 1과 3이 바뀝니다.",
        "두 칸 이동하면 n2에 도착하고 다음 노드가 없어 반복이 끝납니다.",
    ],
    [
        ("초기", "n1→n3→n2", "값 1→3→2"),
        ("첫 교환", "n1.value↔n3.value", "3→1→2"),
        ("두 칸 이동", "node=n2", "반복 종료"),
        ("출력 순회", "3,1,2", "312"),
    ],
    rules="노드의 연결(next)은 바뀌지 않고 value 필드만 서로 교환됩니다.",
    output_moment="main이 그대로인 연결을 따라 바뀐 값 3,1,2를 연속 출력합니다.",
    calculation="(1,3) 교환 + 마지막 2 유지 → 312",
    pitfalls="노드 자체의 순서를 교환했다고 생각하지 말고 값 필드만 바뀌는지 확인합니다.",
    takeaway="첫 두 노드의 값만 바뀌어 출력은 312입니다.",
    object_flow=["n1(value 3) → n3(value 1) → n2(value 2)"],
    executed=True,
)
general(
    "2024-3-11",
    "URL의 다섯 구성 요소",
    [
        "URL에서 `://` 앞은 scheme, 호스트·포트 부분은 authority로 찾습니다.",
        "호스트 뒤 `/...`는 path, `?` 뒤는 query, `#` 뒤는 fragment로 구분합니다.",
        "그림의 번호와 대응하면 query 4, path 3, scheme 1, authority 2, fragment 5입니다.",
    ],
    rules="일반 구조는 `scheme://authority/path?query#fragment`입니다.",
    distinctions="query는 서버에 전달할 매개변수이고 fragment는 받은 문서 안의 위치를 가리킵니다.",
    pitfalls="물음표와 샵 뒤 부분을 서로 바꾸지 않습니다.",
    takeaway="구조 순서로 대응하면 ①4, ②3, ③1, ④2, ⑤5입니다.",
)
code(
    "2024-3-12",
    "정확한 type 비교에 따른 분기",
    [
        "문자열 a는 str이므로 길이 5를 반환합니다.",
        "실수 b는 int도 str도 아니므로 else에서 20을 반환합니다.",
        "튜플 c도 int·str이 아니므로 20을 반환합니다.",
    ],
    [
        ("a=\"100.0\"", "str", "len=5"),
        ("b=100.0", "float", "20"),
        ("c=(100,200)", "tuple", "20"),
        ("합", "5+20+20", "45"),
    ],
    rules="`type(value) == type(100)`은 정확히 int인지 비교하며 float 100.0은 int가 아닙니다.",
    output_moment="세 func 반환값을 더해 print가 출력합니다.",
    calculation="5 + 20 + 20 = 45",
    pitfalls="숫자 값이 100처럼 보인다는 이유로 float를 int 분기에 넣지 않습니다.",
    takeaway="문자열 길이 5와 else 두 번의 20을 더해 45입니다.",
    executed=True,
)
general(
    "2024-3-13",
    "UML 관계선의 모양 읽기",
    [
        "실선으로 연결된 일반 참조 관계를 연관으로 판별합니다.",
        "속이 빈 삼각형 화살표가 부모 쪽을 가리키면 일반화입니다.",
        "점선 화살표로 일시적 사용을 나타내면 의존입니다.",
    ],
    rules="UML 관계는 선의 실선·점선 여부와 화살촉·마름모 모양으로 구분합니다.",
    distinctions="일반화는 is-a 상속, 연관은 구조적 연결, 의존은 일시적 사용 관계입니다.",
    pitfalls="집합·포함의 마름모와 일반화의 빈 삼각형을 구분합니다.",
    takeaway="그림의 세 관계는 ① 연관 ㉡, ② 일반화 ㉢, ③ 의존 ㉠입니다.",
)
code(
    "2024-3-14",
    "메서드는 동적 바인딩, 필드는 참조형 기준",
    [
        "a는 B형 참조지만 실제 객체가 D이므로 a.getX()는 D의 메서드를 호출해 21입니다.",
        "필드 접근 a.x는 오버라이딩되지 않아 선언형 B의 x=3을 읽습니다.",
        "b는 D형이므로 b.getX()=21, b.x=7입니다.",
    ],
    [
        ("a.getX()", "D.getX", "7×3=21"),
        ("a.x", "참조형 B의 필드", "3"),
        ("b.getX()", "D.getX", "21"),
        ("b.x", "D의 필드", "7"),
        ("합", "21+3+21+7", "52"),
    ],
    rules=["오버라이딩된 인스턴스 메서드는 실제 객체형으로 선택됩니다.", "필드는 동적 바인딩되지 않고 참조 변수의 선언형으로 선택됩니다."],
    output_moment="네 항을 정수 덧셈으로 모두 계산할 때 52가 됩니다.",
    calculation="21 + 3 + 21 + 7 = 52",
    pitfalls="a.getX와 a.x를 모두 D 기준으로 보지 않아야 합니다.",
    takeaway="메서드와 필드의 선택 기준이 달라 결과는 52입니다.",
    object_flow=["B a → D 객체: 메서드 D, 필드 접근 B", "D b → D 객체: 메서드 D, 필드 접근 D"],
    executed=True,
)
general(
    "2024-3-15",
    "유일성과 최소성으로 구분하는 키",
    [
        "다른 릴레이션 기본키를 참조하면 외래키입니다.",
        "유일성과 최소성을 모두 만족하는 키 후보는 후보키이고, 기본키가 되지 않은 후보키는 대체키입니다.",
        "유일성은 있지만 최소성이 없으면 슈퍼키입니다.",
    ],
    rules="후보키=유일성+최소성, 슈퍼키=유일성, 외래키=다른 기본키 참조입니다.",
    distinctions="기본키는 후보키 중 선택된 하나이고 대체키는 선택되지 않은 나머지 후보키입니다.",
    pitfalls="문항 ②는 ‘기본키로 선택된 키’가 아니라 선택 가능한 부분집합을 묻기 때문에 후보키입니다.",
    takeaway="① 외래키 ㉡, ② 후보키 ㉣, ③ 대체키 ㉢, ④ 슈퍼키 ㉠입니다.",
)
general(
    "2024-3-16",
    "기본키의 NULL·중복을 금지하는 개체 무결성",
    [
        "제약 대상이 기본키인지 확인합니다.",
        "기본키 구성 속성이 NULL도 중복도 가질 수 없다는 규칙을 개체 무결성과 연결합니다.",
    ],
    rules="개체 무결성은 각 튜플을 식별하는 기본키가 NULL 또는 중복이 되지 않도록 보장합니다.",
    distinctions="참조 무결성은 외래키가 참조 대상 기본키 값과 일치하거나 NULL이어야 한다는 규칙입니다.",
    pitfalls="기본키라는 단서가 나오면 참조 무결성이 아니라 개체 무결성입니다.",
    takeaway="기본키의 NULL·중복 금지는 개체(Entity) 무결성입니다.",
)
code(
    "2024-3-17",
    "구체 예외 catch 뒤에도 실행되는 finally",
    [
        "func가 NullPointerException을 즉시 던집니다.",
        "첫 번째 catch가 정확히 이 예외를 잡아 sum에 1을 더합니다.",
        "finally는 예외 처리 여부와 관계없이 실행되어 100을 더합니다.",
    ],
    [
        ("초기", "sum=0", "-"),
        ("예외", "NullPointerException", "첫 catch 선택"),
        ("catch", "sum += 1", "1"),
        ("finally", "sum += 100", "101"),
    ],
    rules="여러 catch 중 처음으로 타입이 맞는 하나만 실행되고 finally는 이어서 실행됩니다.",
    output_moment="finally까지 끝난 sum을 System.out.print가 출력합니다.",
    calculation="0 + 1 + 100 = 101",
    pitfalls="상위 타입 Exception catch도 맞지만 앞의 더 구체적인 catch에서 이미 처리됩니다.",
    takeaway="구체 catch의 1과 finally의 100이 더해져 101입니다.",
    executed=True,
)
code(
    "2024-3-18",
    "제네릭 타입 소거와 오버로딩 선택",
    [
        "`new Collection<>(0)`에서 T는 Integer로 추론되고 value에는 0이 들어갑니다.",
        "하지만 제네릭 클래스의 T는 컴파일 시 타입 소거되어 print 메서드 안 value의 호출 기준 타입이 Object가 됩니다.",
        "오버로딩은 컴파일 시 인수의 선언 타입으로 선택되므로 print(Object)가 호출됩니다.",
    ],
    [
        ("생성", "T=Integer, value=0", "-"),
        ("타입 소거 후", "value의 호출 기준 Object", "-"),
        ("오버로딩 선택", "Printer.print(Object)", "B+0"),
        ("출력", "\"B\" + 0", "B0"),
    ],
    rules=["오버로딩은 컴파일 시 인수의 선언 타입으로 결정됩니다.", "제네릭 T의 상한이 없으면 타입 소거 후 Object로 취급됩니다."],
    output_moment="Printer.print(Object)가 선택되어 접두사 B와 값 0을 출력합니다.",
    calculation="\"B\" + 0 = \"B0\"",
    pitfalls="실제 값이 Integer라는 이유로 print(Integer)가 선택된다고 생각하기 쉽습니다.",
    takeaway="타입 소거 뒤 Object 오버로드가 선택되어 B0입니다.",
    object_flow=["Collection<Integer>.value=0", "호출 시 소거 타입 Object → print(Object)"],
)
code(
    "2024-3-19",
    "이중 포인터로 원본 배열을 직접 수정",
    [
        "pp는 p의 주소이고 p는 arr 첫 원소를 가리키므로 `*(*arr+i)`는 원본 배열 i번째 원소입니다.",
        "각 원소를 `(기존값+i)%5`로 바꿉니다.",
        "인덱스 2의 값은 `(4+2)%5=1`이 되어 num에 대입됩니다.",
    ],
    [
        ("i=0", "(3+0)%5", "arr[0]=3"),
        ("i=1", "(1+1)%5", "arr[1]=2"),
        ("i=2", "(4+2)%5", "arr[2]=1"),
        ("대입", "num=arr[2]", "1"),
    ],
    rules="이중 포인터를 두 번 역참조하면 p가 가리키는 원본 배열에 접근합니다.",
    output_moment="func 뒤 arr[2]를 num에 복사하고 출력합니다.",
    calculation="(4+2) mod 5 = 1",
    pitfalls="함수 매개변수 이름 arr가 main의 배열 자체가 아니라 int**라는 점을 확인합니다.",
    takeaway="원본 배열의 세 번째 값이 1로 바뀌어 출력은 1입니다.",
    object_flow=["pp → p → arr[0]", "*(*pp+2) ↔ arr[2]"],
    executed=True,
)
general(
    "2024-3-20",
    "고정 기반 시설 없이 구성하는 Ad-hoc Network",
    [
        "기지국이나 유선 백본 없이 모바일 호스트만으로 임시 구성되는지 확인합니다.",
        "각 노드가 중계 역할까지 하는 멀티 홉 라우팅 특성을 Ad-hoc Network와 연결합니다.",
    ],
    rules="Ad-hoc 네트워크는 고정 인프라 없이 이동 노드들이 자율적으로 망을 구성합니다.",
    distinctions="Infrastructure Network는 액세스 포인트 같은 고정 기반 시설을 사용합니다.",
    pitfalls="Mesh도 다중 경로를 사용할 수 있지만 재난 현장의 임시 모바일 호스트망이라는 단서는 Ad-hoc입니다.",
    takeaway="고정망 없이 모바일 호스트로 잠시 만드는 멀티 홉 망은 Ad-hoc Network ㉣입니다.",
)

# 2025년 1회
general(
    "2025-1-01",
    "인증된 연결의 세션을 가로채는 세션 하이재킹",
    [
        "공격 시점이 로그인 전이 아니라 상호 인증을 마친 뒤인지 확인합니다.",
        "세션 정보나 TCP 시퀀스 번호를 훔쳐 정상 클라이언트처럼 행동한다는 단서를 연결합니다.",
    ],
    rules="세션 하이재킹은 이미 성립한 세션의 식별·동기화 정보를 탈취해 연결을 가로채는 공격입니다.",
    distinctions="스니핑은 통신 내용을 엿보는 데 초점이 있고, 세션 하이재킹은 탈취한 세션으로 직접 권한을 사용합니다.",
    pitfalls="비밀번호를 훔치지 않아도 인증 후 세션을 탈취할 수 있다는 점을 놓치지 않습니다.",
    takeaway="인증 뒤 세션·시퀀스 번호를 가로채면 세션 하이재킹입니다.",
)
general(
    "2025-1-02",
    "도메인·개체·참조 무결성의 제약 대상",
    [
        "속성이 허용된 값의 범위를 지켜야 하는 제약은 도메인 무결성입니다.",
        "기본키로 튜플을 유일하게 식별하는 제약은 개체 무결성입니다.",
        "외래키가 참조 대상과 일치해야 하는 제약은 참조 무결성입니다.",
    ],
    rules="도메인은 속성 값, 개체는 기본키, 참조는 외래키를 중심으로 봅니다.",
    distinctions="개체 무결성은 한 릴레이션 내부의 기본키, 참조 무결성은 릴레이션 사이의 외래키 관계입니다.",
    pitfalls="제약 조건 개수보다 표의 ‘NULL 값·기본키·외래키’ 행을 먼저 읽으면 대응이 쉽습니다.",
    takeaway="① 도메인, ② 개체, ③ 참조 무결성입니다.",
)
code(
    "2025-1-03",
    "문자 코드 차와 배열 중간 삽입",
    [
        "Data[3]은 E, Data[1]은 A이므로 문자 코드 차는 4입니다.",
        "전역 배열의 다섯 번째 원소는 0으로 초기화되고, C보다 큰 첫 문자 D가 인덱스 2에서 발견됩니다.",
        "그 자리에 C를 넣고 기존 D와 E를 오른쪽으로 차례로 밀어 BACDE를 만듭니다.",
    ],
    [
        ("첫 출력", "'E'-'A'", "4"),
        ("삽입 위치", "Data[2]='D' > 'C'", "i=2"),
        ("C 삽입", "B A C D E", "BACDE"),
        ("전체 출력", "4와 배열", "4 / BACDE"),
    ],
    rules=["C의 char 산술은 문자 코드값으로 계산됩니다.", "전역 배열의 생략된 원소는 0으로 초기화됩니다."],
    output_moment="첫 printf 뒤 배열 문자들이 순서대로 출력됩니다.",
    calculation="'E'(69)-'A'(65)=4, 배열 결과 BACDE",
    pitfalls="PDF 추출의 `n`은 줄바꿈 표기 훼손 가능성이 있으므로 원본 출력 형식과 답안의 두 줄을 함께 확인합니다.",
    takeaway="문자 코드 차는 4이고 C를 삽입한 배열은 BACDE입니다.",
)
general(
    "2025-1-04",
    "다항식 나눗셈으로 오류를 검출하는 CRC",
    [
        "검사 방식이 단순한 1비트 패리티가 아니라 다항식 코드를 사용한다는 단서를 찾습니다.",
        "HDLC의 FCS에 쓰이고 집단 오류 검출률이 높다는 설명을 CRC와 연결합니다.",
    ],
    rules="CRC는 송수신 측이 같은 생성 다항식으로 나눈 나머지를 이용해 오류를 검출합니다.",
    distinctions="패리티는 검사 비트 하나를 더하고, CRC는 다항식 나눗셈의 나머지를 검사값으로 씁니다.",
    pitfalls="오류를 ‘수정’하는 해밍 코드와 오류를 ‘검출’하는 CRC를 구분합니다.",
    takeaway="다항식 코드·FCS·집단 오류 검출이면 CRC입니다.",
)
code(
    "2025-1-05",
    "구체 예외 처리 후 finally 실행",
    [
        "정수 5를 0으로 나누는 순간 ArithmeticException이 발생해 정상 출력은 실행되지 않습니다.",
        "첫 번째 catch가 이 예외를 잡아 `출력1`을 출력합니다.",
        "finally는 항상 실행되어 바로 뒤에 `출력5`를 붙입니다.",
    ],
    [
        ("try", "5/0", "ArithmeticException"),
        ("catch", "ArithmeticException 일치", "출력1"),
        ("finally", "항상 실행", "출력5"),
        ("전체", "줄바꿈 없음", "출력1출력5"),
    ],
    rules="catch는 위에서부터 맞는 예외 하나를 실행하며 finally는 예외 여부와 무관하게 실행됩니다.",
    output_moment="finally의 문자열이 catch 출력 뒤에 공백 없이 이어집니다.",
    calculation="`출력1` + `출력5` = `출력1출력5`",
    pitfalls="0으로 나눌 때 0이 출력되는 것이 아니라 예외가 발생합니다.",
    takeaway="산술 예외 catch와 finally가 차례로 실행되어 출력1출력5입니다.",
    executed=True,
)
code(
    "2025-1-06",
    "내부 조인 뒤 조건으로 행 거르기",
    [
        "emp.id와 sal.id가 같은 행만 먼저 연결합니다.",
        "연결 가능한 1002, 1004, 1008 중 incentive가 500 이상인 행만 남깁니다.",
        "1008의 이름 이순신과 incentive 1000만 SELECT합니다.",
    ],
    [
        ("JOIN", "id 1002", "홍길동,300 → 제외"),
        ("JOIN", "id 1004", "강감찬,400 → 제외"),
        ("JOIN", "id 1008", "이순신,1000 → 포함"),
        ("SELECT", "name,incentive", "이순신 / 1000"),
    ],
    rules="쉼표 조인에서 WHERE의 `emp.id=sal.id`가 내부 조인 조건 역할을 합니다.",
    output_moment="조건을 통과한 한 행에서 name과 incentive 열을 투영합니다.",
    calculation="일치 행 3개 중 incentive≥500은 1008 한 행",
    pitfalls="sal에만 있는 id 1009나 emp에만 있는 1006은 내부 조인 결과에 들어오지 않습니다.",
    takeaway="조인과 금액 조건을 모두 만족하는 결과는 이순신 1000 한 행입니다.",
)
general(
    "2025-1-07",
    "모듈이 공유하는 대상에 따른 결합도 구분",
    [
        "다른 모듈 내부 자료를 직접 건드리면 내용 결합입니다.",
        "배열·레코드 같은 자료 구조 전체를 인터페이스로 넘기면 스탬프 결합입니다.",
        "전역 데이터 영역을 여러 모듈이 함께 사용하면 공통 결합입니다.",
    ],
    rules="결합도는 모듈 사이 의존의 강도를 뜻하며 일반적으로 낮을수록 좋습니다.",
    distinctions="자료 결합은 필요한 단순 값, 스탬프 결합은 구조체 전체, 공통 결합은 전역 데이터 공유입니다.",
    pitfalls="‘자료’라는 단어만 보고 자료 결합을 고르지 말고 전달 단위가 구조 전체인지 확인합니다.",
    takeaway="① 내용 ㉤, ② 스탬프 ㉡, ③ 공통 ㉥입니다.",
)
general(
    "2025-1-08",
    "거짓 보안 경고로 구매를 유도하는 스케어웨어",
    [
        "실제 감염 여부와 무관하게 위협적인 경고로 사용자의 불안을 키우는지 확인합니다.",
        "문제 해결을 핑계로 불필요한 프로그램 결제를 유도한다는 점을 스케어웨어와 연결합니다.",
    ],
    rules="Scareware는 scare(겁주다)와 software가 합쳐진 말로 공포를 이용해 행동·구매를 유도합니다.",
    distinctions="랜섬웨어는 실제 데이터를 잠그고 금전을 요구하지만 스케어웨어는 거짓 경고가 핵심입니다.",
    pitfalls="광고가 보인다는 이유로 애드웨어로 고르지 말고 ‘거짓 감염 경고’에 주목합니다.",
    takeaway="가짜 보안 경고로 구매를 유도하면 스케어웨어입니다.",
)
general(
    "2025-1-09",
    "/22 서브넷의 주소 범위 판정",
    [
        "255.255.252.0은 /22이며 세 번째 옥텟 블록 크기는 256-252=4입니다.",
        "35가 속한 블록은 32~35이므로 네트워크는 192.168.32.0, 브로드캐스트는 192.168.35.255입니다.",
        "보기의 다섯 주소는 모두 이 범위의 사용 가능한 호스트 주소입니다.",
    ],
    rules="/22에서는 세 번째 옥텟이 4단위 블록으로 나뉩니다.",
    distinctions="서브넷 브로드캐스트 192.168.35.255 자체는 호스트로 받을 수 없지만 보기에는 없습니다.",
    pitfalls="현재 IP의 세 번째 옥텟 35만 같은 주소를 고르는 것이 아니라 32~35 전체가 같은 서브넷입니다.",
    takeaway="보기 ㉠~㉤이 모두 192.168.32.0/22 안에 있어 전부 수신할 수 있습니다.",
)
general(
    "2025-1-10",
    "IP와 MAC 주소를 서로 찾는 ARP·RARP",
    [
        "논리 주소 IP를 알고 물리 주소 MAC을 찾는 방향은 ARP입니다.",
        "반대로 MAC을 알고 IP를 찾는 방향은 RARP입니다.",
    ],
    rules="ARP는 IP→MAC, RARP는 MAC→IP의 주소 해석 방향을 가집니다.",
    distinctions="DNS는 도메인 이름과 IP를 대응시키며 MAC 주소 변환과는 다릅니다.",
    pitfalls="Reverse라는 이름이 붙은 RARP의 방향을 ARP와 반대로 정확히 씁니다.",
    takeaway="① ARP(IP→MAC), ② RARP(MAC→IP)입니다.",
)
code(
    "2025-1-11",
    "생성 중에도 적용되는 오버라이딩과 필드 초기화 순서",
    [
        "부모 생성자에서 부모 v가 1→2가 되어 total=2입니다.",
        "부모 생성자가 호출한 show도 실제 객체가 Child이므로 Child.show가 실행되어 total=6이 됩니다.",
        "부모 생성 뒤 자식 v가 10으로 초기화되고, 자식 생성자에서 12를 더해 total=18, 마지막 show에서 54가 됩니다.",
    ],
    [
        ("부모 ++v", "Parent.v 1→2", "total=2"),
        ("부모 안 show", "Child.show", "total=2+4=6"),
        ("자식 v+=2", "Child.v=12", "total=6+12=18"),
        ("자식 show", "Child.show", "total=18+36=54"),
    ],
    rules=["생성자 안의 오버라이딩 메서드도 실제 객체형으로 동적 호출됩니다.", "부모 초기화가 끝난 뒤 자식 인스턴스 필드 초기화가 진행됩니다."],
    output_moment="자식 생성자 마지막 show가 total을 54로 만든 뒤 main이 출력합니다.",
    calculation="2 → 6 → 18 → 54",
    pitfalls="부모 생성자에서 Parent.show가 실행된다고 생각하거나 자식 v가 이미 10이라고 가정하기 쉽습니다.",
    takeaway="동적 호출과 초기화 순서를 따르면 Parent.total은 54입니다.",
    object_flow=["new Child → Parent 초기화 → Child 필드 초기화 → Child 생성자", "show 호출은 두 번 모두 Child.show"],
)
code(
    "2025-1-12",
    "계산된 행·열 인덱스로 배열을 채운 뒤 교대 합",
    [
        "set의 인덱스 식을 i=0부터 8까지 계산하면 배열은 `[9,5,2] [7,4,1] [8,3,6]`이 됩니다.",
        "두 번째 반복문은 평탄화한 인덱스가 짝수면 더하고 홀수면 뺍니다.",
        "아홉 값을 +,-,+ 순서로 계산합니다.",
    ],
    [
        ("set 완료", "9 5 2 / 7 4 1 / 8 3 6", "-"),
        ("앞 3개", "9-5+2", "6"),
        ("중간 3개", "-7+4-1", "누적 2"),
        ("뒤 3개", "+8-3+6", "13"),
    ],
    rules="정수 나눗셈으로 행 인덱스를 계산하고 `%`로 배열 범위를 순환합니다.",
    output_moment="평탄 인덱스 0~8의 교대 부호 합이 끝난 뒤 13을 출력합니다.",
    calculation="9-5+2-7+4-1+8-3+6 = 13",
    pitfalls="data의 원래 순서에 바로 부호를 붙이지 말고 set이 만든 2차원 배치를 먼저 완성해야 합니다.",
    takeaway="배치된 행렬에 교대 부호를 적용하면 합은 13입니다.",
)
general(
    "2025-1-13",
    "호환되지 않는 인터페이스를 변환하는 Adapter",
    [
        "기존 클래스를 다시 작성하지 않고도 다른 인터페이스로 사용하려는 상황인지 확인합니다.",
        "한 인터페이스를 클라이언트가 기대하는 형태로 바꿔 준다는 설명을 Adapter와 연결합니다.",
    ],
    rules="Adapter는 기존 객체를 감싸 인터페이스를 호환되는 형태로 변환하는 구조 패턴입니다.",
    distinctions="Facade는 복잡한 하위 시스템에 단순한 창구를 제공하고, Adapter는 서로 맞지 않는 인터페이스를 맞춥니다.",
    pitfalls="기능을 추가하는 Decorator와 호출 규격을 바꾸는 Adapter를 구분합니다.",
    takeaway="기존 클래스의 인터페이스를 호환되게 바꾸면 Adapter입니다.",
)
general(
    "2025-1-14",
    "순서도 대응과 문장 커버리지 경로",
    [
        "초기화, while 조건, if 조건, 부호 변경, 증가, 반환을 코드의 실행 순서대로 순서도 상자에 대응합니다.",
        "문장 커버리지는 실행 가능한 모든 문장이 최소 한 번 지나가게 하는 경로를 선택합니다.",
        "if 본문의 부호 변경까지 실행한 뒤 반복을 빠져나와 return에 도달하는 경로를 적습니다.",
    ],
    rules="문장 커버리지는 각 실행문을 한 번 이상 수행하면 되며 모든 분기 조합까지 요구하지 않습니다.",
    distinctions="분기 커버리지는 각 결정의 참·거짓을 모두 요구하지만 문장 커버리지는 실행문 방문이 기준입니다.",
    pitfalls="원문의 while 조건이 OR이므로 배열 범위를 벗어날 가능성이 있는 축약 예제입니다. 실제 실행용 코드로 사용하지 않고 제시된 순서도 경로만 판정합니다.",
    takeaway="빈칸은 초기화→while 조건→if 조건→변경→증가→return이며, 제시 답의 경로가 모든 문장을 방문합니다.",
)
general(
    "2025-1-15",
    "릴레이션의 열·행·참조·값 범위 용어",
    [
        "속성 개수는 Degree, 튜플 개수는 Cardinality입니다.",
        "다른 릴레이션 기본키를 참조하는 속성은 Foreign Key입니다.",
        "한 속성이 가질 수 있는 원자값 집합은 Domain입니다.",
    ],
    rules="Degree=열 수, Cardinality=행 수, Foreign=외래키, Domain=허용값 집합입니다.",
    distinctions="Attribute는 개별 열 자체이고 Degree는 그 열의 개수입니다.",
    pitfalls="Cardinality와 Degree를 행·열 방향과 함께 외워 반대로 쓰지 않습니다.",
    takeaway="① ㉢ Degree, ② ㉤ Cardinality, ③ ㉦ Foreign, ④ ㉠ Domain입니다.",
)
code(
    "2025-1-16",
    "첫 호출만 String 오버로드, 재귀는 int 오버로드",
    [
        "`calc(\"5\")`는 String 버전을 선택해 정수 5로 바꿉니다.",
        "String 버전의 재귀식은 인수가 int이므로 이후 호출은 모두 피보나치 형태의 calc(int)입니다.",
        "따라서 calc(4)+calc(2)를 계산합니다.",
    ],
    [
        ("String calc", "value=5", "calc(4)+calc(2)"),
        ("calc(4)", "F4", "3"),
        ("calc(2)", "F2", "1"),
        ("합", "3+1", "4"),
    ],
    rules="오버로딩은 전달 인수 타입으로 선택되며 int 재귀는 `F(n)=F(n-1)+F(n-2)`입니다.",
    output_moment="String 버전이 돌려준 두 int 재귀 결과의 합을 출력합니다.",
    calculation="calc(4)=3, calc(2)=1 → 4",
    pitfalls="String 버전의 `value-3`을 다시 String 버전으로 호출한다고 생각하면 안 됩니다.",
    takeaway="첫 호출만 String이고 내부는 int 피보나치 계산이라 결과는 4입니다.",
)
code(
    "2025-1-17",
    "16진수 비트 AND 결과의 합",
    [
        "dec는 각 점수와 0xA5를 비트별 AND합니다.",
        "Kim의 결과는 0xA0=160, 0xA5=165, 0x81=129로 합 454입니다.",
        "Lee도 0xA0=160, 0xA5=165, 0x81=129로 합 454이며 두 학생을 더합니다.",
    ],
    [
        ("Kim", "160+165+129", "454"),
        ("Lee", "160+165+129", "454"),
        ("전체", "454+454", "908"),
    ],
    rules="비트 AND는 두 비트가 모두 1인 자리만 1로 남깁니다.",
    output_moment="두 Student의 sum 반환값을 result에 누적한 뒤 10진수로 출력합니다.",
    calculation="(0xA0+0xA5+0x81)×2 = 454×2 = 908",
    pitfalls="16진수 표기값을 10진수 숫자 160·165·129로 바꿔 합산해야 합니다.",
    takeaway="각 학생의 마스킹 합이 454라서 전체는 908입니다.",
)
code(
    "2025-1-18",
    "구간 중앙값을 더하며 더 큰 재귀 가지 선택",
    [
        "전체 0~4 구간의 mid는 2이고 a[2]=8입니다.",
        "왼쪽 0~2 재귀 결과는 8, 오른쪽 3~4 재귀 결과는 12입니다.",
        "Math.max가 오른쪽 12를 선택해 루트의 8과 더합니다.",
    ],
    [
        ("func(0,2)", "5 + max(3,0)", "8"),
        ("func(3,4)", "12 + max(0,0)", "12"),
        ("func(0,4)", "8 + max(8,12)", "20"),
    ],
    rules="st>=end인 한 원소 구간은 그 원소를 더하지 않고 0을 반환합니다.",
    output_moment="최상위 호출이 중앙값 8과 더 큰 하위 결과 12를 더합니다.",
    calculation="8 + max(8,12) = 20",
    pitfalls="양쪽 재귀 결과를 모두 더하는 것이 아니라 Math.max로 하나만 고릅니다.",
    takeaway="각 구간 중앙을 따라 더 큰 가지를 선택한 합은 20입니다.",
)
code(
    "2025-1-19",
    "완전 이진 트리의 홀수 레벨 값 합",
    [
        "리스트를 배열 인덱스 규칙으로 연결하면 루트 3의 자식은 5와 8입니다.",
        "calc는 level이 홀수일 때만 현재 노드 값을 더합니다.",
        "레벨 1의 5와 8만 더하고 레벨 0·2 값은 0으로 처리합니다.",
    ],
    [
        ("레벨 0", "노드 3", "더하지 않음"),
        ("레벨 1", "노드 5,8", "5+8=13"),
        ("레벨 2", "12,15,18,21", "더하지 않음"),
        ("합", "홀수 레벨", "13"),
    ],
    rules="배열 기반 완전 이진 트리에서 i번째 노드의 부모 인덱스는 `(i-1)//2`입니다.",
    output_moment="모든 자식 재귀 합이 루트로 돌아오면 홀수 레벨 합 13이 됩니다.",
    calculation="5 + 8 = 13",
    pitfalls="홀수 ‘값’을 더하는 것이 아니라 홀수 ‘레벨’의 모든 값을 더합니다.",
    takeaway="레벨 1의 5와 8만 포함되어 결과는 13입니다.",
    object_flow=["level 0: 3", "level 1: 5, 8", "level 2: 12, 15, 18, 21"],
    executed=True,
)
code(
    "2025-1-20",
    "머리 삽입 후 특정 노드를 맨 앞으로 이동",
    [
        "1부터 5까지 매번 머리에 삽입하므로 초기 리스트는 5→4→3→2→1입니다.",
        "reconnect가 값 3의 이전 노드 4를 찾고 4.next를 2로 연결해 3을 떼어냅니다.",
        "3.next를 기존 head 5로 연결하고 3을 새 head로 만듭니다.",
    ],
    [
        ("삽입 완료", "5→4→3→2→1", "-"),
        ("3 분리", "5→4→2→1", "curr=3"),
        ("머리 연결", "3→5→4→2→1", "-"),
        ("출력", "공백 없이 순회", "35421"),
    ],
    rules="머리 삽입은 입력 순서를 뒤집고, 연결 변경은 이전·현재·다음 포인터를 잃지 않는 순서로 해야 합니다.",
    output_moment="새 head 3부터 next를 따라 값을 붙여 출력합니다.",
    calculation="3,5,4,2,1 → 35421",
    pitfalls="값 3을 복사하는 것이 아니라 기존 노드의 연결을 바꾸는 과정입니다.",
    takeaway="역순 리스트에서 3을 맨 앞으로 옮기면 35421입니다.",
    object_flow=["before: head→5→4→3→2→1", "after: head→3→5→4→2→1"],
)

# 2025년 2회
general(
    "2025-2-01",
    "값과 레코드 주소를 연결하는 색인 파일",
    [
        "파일 구조의 세 분류가 순차·색인·해싱이라는 기본 구성을 떠올립니다.",
        "검색 키 값과 실제 레코드 주소의 쌍을 별도 구조로 두어 접근한다는 설명을 색인과 연결합니다.",
    ],
    rules="색인은 `<키 값, 레코드 주소>` 항목을 이용해 원하는 레코드 위치를 빠르게 찾습니다.",
    distinctions="순차 파일은 물리적 순서로 읽고, 해싱은 해시 함수로 주소를 계산하며, 색인은 별도 인덱스를 탐색합니다.",
    pitfalls="데이터 레코드 자체와 레코드를 가리키는 색인 항목을 같은 것으로 보지 않습니다.",
    takeaway="값과 주소의 쌍으로 접근하는 구조는 색인(Index) 파일입니다.",
)
general(
    "2025-2-02",
    "암호화된 원격 접속 프로토콜 SSH",
    [
        "원격 로그인·명령 실행·파일 복사를 한 보안 프로토콜이 지원하는지 확인합니다.",
        "공개키 인증과 기본 22번 포트라는 결정적 단서를 SSH와 연결합니다.",
    ],
    rules="SSH는 암호화된 채널에서 원격 셸과 터널링·파일 전송 기능을 제공합니다.",
    distinctions="Telnet도 원격 로그인이지만 기본 통신이 평문이고 일반적으로 23번 포트를 씁니다.",
    pitfalls="파일 복사 기능만 보고 FTP로 답하지 말고 22번 포트와 원격 셸을 함께 봅니다.",
    takeaway="22번 포트·공개키 인증·안전한 원격 명령이면 SSH입니다.",
)
general(
    "2025-2-03",
    "릴레이션의 열이자 개체 특성인 Attribute",
    [
        "데이터베이스의 가장 작은 논리 단위가 릴레이션에서 열에 해당하는지 확인합니다.",
        "개체의 특성을 기술하는 항목이라는 설명을 Attribute와 연결합니다.",
    ],
    rules="Attribute는 릴레이션의 열이며 파일 관점에서는 데이터 필드에 대응합니다.",
    distinctions="Tuple은 한 행, Entity는 표현 대상 개체, Domain은 속성이 가질 수 있는 값의 집합입니다.",
    pitfalls="속성의 개수인 Degree와 개별 속성 Attribute를 구분합니다.",
    takeaway="열·필드·개체 특성을 뜻하는 용어는 Attribute ㉢입니다.",
)
code(
    "2025-2-04",
    "배열 원소 변경과 문자열 참조의 값 전달",
    [
        "data 매개변수는 호출자와 같은 배열 객체를 가리키므로 data[0]을 B로 바꾸면 main에서도 보입니다.",
        "s 매개변수에는 문자열 참조값이 복사됩니다.",
        "함수 안에서 s를 Z로 다시 대입해도 main의 s는 여전히 B를 가리킵니다.",
    ],
    [
        ("호출 전", "data[0]=A, s=B", "-"),
        ("data[0]=s", "배열 원소=B", "main에도 반영"),
        ("s=\"Z\"", "지역 매개변수만 변경", "main s=B"),
        ("출력", "B+B", "BB"),
    ],
    rules="Java는 참조도 값으로 전달합니다. 같은 객체의 내부 변경은 보이지만 매개변수 재대입은 호출자 변수를 바꾸지 않습니다.",
    output_moment="main이 변경된 data[0]과 그대로인 s를 이어 출력합니다.",
    calculation="data[0]=\"B\", s=\"B\" → \"BB\"",
    pitfalls="s=\"Z\"가 main의 s까지 Z로 바꾼다고 생각하지 않습니다.",
    takeaway="배열은 수정되지만 지역 참조 재대입은 전달되지 않아 BB입니다.",
    object_flow=["main data ─┬→ String[] {\"B\"}", "change data ─┘", "main s→\"B\", change s→\"Z\"(지역)"],
    executed=True,
)
code(
    "2025-2-05",
    "재설정된 단일 연결 리스트 따라가기",
    [
        "처음 a→b→c로 만들지만 뒤의 대입이 최종 연결을 다시 정합니다.",
        "최종적으로 c.next=a, a.next=b, b.next=NULL이고 head는 c입니다.",
        "head에서 data를 읽으며 두 번 next를 따라갑니다.",
    ],
    [
        ("최종 head", "c", "3"),
        ("head->n", "a", "1"),
        ("head->n->n", "b", "2"),
        ("출력", "3 1 2", "3 1 2"),
    ],
    rules="포인터 대입은 앞에서 만든 연결을 덮어쓸 수 있으므로 마지막 상태만 그립니다.",
    output_moment="printf가 c, a, b의 p 값을 공백 사이에 출력합니다.",
    calculation="c.p=3, a.p=1, b.p=2",
    pitfalls="초기 a→b→c만 보고 1 2 3이라고 답하지 말고 뒤의 재연결을 반영합니다.",
    takeaway="최종 연결은 c→a→b라서 3 1 2입니다.",
    object_flow=["head → c(3) → a(1) → b(2) → NULL"],
    executed=True,
)
general(
    "2025-2-06",
    "비선점 SJF와 선점 SRT",
    [
        "대기 중 실행시간이 가장 짧은 작업을 골라 끝까지 수행하면 SJF입니다.",
        "새 프로세스가 올 때마다 현재 남은 시간과 비교해 더 짧은 쪽으로 바꾸면 SRT입니다.",
    ],
    rules="SJF는 Shortest Job First, SRT는 Shortest Remaining Time입니다.",
    distinctions="SJF는 일반적으로 비선점이고 SRT는 SJF의 선점형으로 볼 수 있습니다.",
    pitfalls="둘 다 짧은 작업을 우선하지만 비교 대상이 전체 실행시간인지 남은 시간인지 구분합니다.",
    takeaway="① SJF, ② SRT입니다.",
)
general(
    "2025-2-07",
    "프로젝션이 남기는 열과 중복 제거",
    [
        "관계대수 πTTL은 EMPLOYEE에서 TTL 속성 하나만 선택합니다.",
        "프로젝션 결과의 열 이름은 TTL입니다.",
        "원본 TTL 값 부장·대리·과장·차장을 뽑고 관계이므로 중복 값은 하나로 정리합니다.",
    ],
    rules="프로젝션 π는 지정한 열만 남기며 관계대수 결과에서는 중복 튜플을 제거합니다.",
    distinctions="셀렉션 σ는 조건에 맞는 행을 고르고 프로젝션 π는 열을 고릅니다.",
    pitfalls="INDEX나 AGE 값을 결과에 함께 적지 않습니다.",
    takeaway="① TTL, 이어지는 값은 ② 부장 ③ 대리 ④ 과장 ⑤ 차장입니다.",
)
general(
    "2025-2-08",
    "/26 네트워크 주소와 사용 가능한 호스트 수",
    [
        "255.255.255.192는 /26이고 마지막 옥텟 블록 크기는 256-192=64입니다.",
        "132가 속한 블록은 128~191이므로 네트워크 주소 마지막 값은 128입니다.",
        "호스트 비트 6개에서 네트워크·브로드캐스트 2개를 빼면 62개입니다.",
    ],
    rules="/26의 한 서브넷은 64개 주소를 가지며 사용 가능한 호스트는 2^6-2입니다.",
    distinctions="128은 네트워크 주소, 191은 브로드캐스트 주소, 129~190이 호스트 범위입니다.",
    pitfalls="주소 총수 64와 사용 가능한 호스트 수 62를 구분합니다.",
    takeaway="네트워크는 223.13.234.128이고 사용 가능한 호스트는 62개입니다.",
)
code(
    "2025-2-09",
    "람다 예외를 run이 반환값으로 바꾸는 과정",
    [
        "첫 람다는 x=3에서 x>2가 참이므로 예외를 던지고 run의 catch가 7을 반환합니다.",
        "두 번째 람다는 n+9를 정상 반환하므로 3+9=12입니다.",
        "main은 두 run 결과를 더합니다.",
    ],
    [
        ("run(f)", "3>2 → 예외", "catch 반환 7"),
        ("run(n→n+9)", "3+9", "12"),
        ("합", "7+12", "19"),
    ],
    rules="람다가 던진 Exception은 run 내부 try-catch에서 처리되어 7이라는 정상 반환값으로 바뀝니다.",
    output_moment="두 run 호출이 각각 7과 12를 반환한 뒤 덧셈합니다.",
    calculation="7 + 12 = 19",
    pitfalls="첫 람다의 원래 `x*2`는 예외 뒤에는 실행되지 않습니다.",
    takeaway="예외 경로 7과 정상 경로 12를 더해 19입니다.",
    executed=True,
)
code(
    "2025-2-10",
    "원형 큐 상태와 C 인수 평가 순서의 함정",
    [
        "enq 1, enq 2, deq 뒤 큐의 논리적 내용은 2입니다.",
        "enq 3 뒤 논리적 제거 순서는 2 다음 3입니다.",
        "하지만 한 printf 호출의 두 deq 인수 중 어느 것을 먼저 평가할지는 C 표준이 정하지 않습니다.",
    ],
    [
        ("초기 연산 후", "front=1, rear=0", "큐: 2,3"),
        ("왼쪽 인수 먼저라면", "deq→2, 다음→3", "2 그리고 3"),
        ("오른쪽 인수 먼저라면", "오른쪽→2, 왼쪽→3", "3 그리고 2"),
        ("PDF 자료 내부", "답안 3 그리고 2 / 해설 결과 2 그리고 3", "서로 불일치"),
        ("GCC 실행", "C17, 최적화 O0·O2", "3 그리고 2"),
    ],
    rules="C 함수 인수의 평가 순서는 지정되어 있지 않으므로 두 인수가 같은 큐 상태를 바꾸면 결과가 구현에 따라 달라질 수 있습니다.",
    output_moment="두 deq의 평가 순서가 출력 위치에 들어갈 값을 결정합니다.",
    calculation="논리적 dequeue 순서는 2→3이지만 인수 평가 위치 때문에 2·3 또는 3·2가 가능합니다.",
    pitfalls="deq의 논리적 반환 순서가 2→3이라고 해서 함수 인수도 항상 왼쪽부터 평가된다고 단정하면 안 됩니다.",
    takeaway="대표 답은 2 그리고 3이며, 표준 C에서는 평가 순서가 미지정이므로 3 그리고 2도 가능한 답으로 함께 인정합니다.",
    status="needs-review",
    verification_note="큐를 손으로 추적하고 GCC(C17, O0·O2)에서 3 그리고 2가 출력됨을 확인했습니다. PDF의 답안은 3 그리고 2, 해설 결과는 2 그리고 3으로 서로 다르며, C 표준의 미지정 인수 평가 순서 때문에 두 결과를 모두 인정합니다.",
)
general(
    "2025-2-11",
    "페이지 일부만 비동기로 갱신하는 AJAX",
    [
        "브라우저의 JavaScript가 서버와 비동기로 통신한다는 점을 확인합니다.",
        "전체 페이지 새로고침 없이 일부 영역만 바꾼다는 사용자 경험을 AJAX와 연결합니다.",
    ],
    rules="AJAX는 Asynchronous JavaScript and XML의 약자이며 XML 외에 JSON도 흔히 사용합니다.",
    distinctions="AJAX는 특정 프로그래밍 언어가 아니라 비동기 웹 통신 기법의 묶음입니다.",
    pitfalls="이름에 XML이 있어도 데이터 형식을 XML로만 제한하는 기술은 아닙니다.",
    takeaway="비동기 요청으로 페이지 일부만 갱신하면 AJAX입니다.",
)
general(
    "2025-2-12",
    "실제 객체 대신 접근을 중개하는 Proxy",
    [
        "클라이언트가 실제 객체에 직접 접근하지 않고 대리 객체를 거치는지 확인합니다.",
        "복잡한 내부 관계나 세부 구현을 숨기면서 접근을 제어한다는 설명을 Proxy와 연결합니다.",
    ],
    rules="Proxy는 실제 객체와 같은 인터페이스를 제공하며 접근 제어·지연 생성·원격 접근 등을 중개합니다.",
    distinctions="Facade는 하위 시스템 전체에 단순 창구를 제공하고 Proxy는 특정 실제 객체를 대신합니다.",
    pitfalls="‘숨긴다’는 말만 보고 Facade로 고르지 말고 대리자라는 직접 단서를 봅니다.",
    takeaway="실제 객체를 대신하는 대리자는 Proxy입니다.",
)
general(
    "2025-2-13",
    "반쪽 연결을 쌓아 대기열을 고갈시키는 SYN Flooding",
    [
        "TCP 3-way handshake의 시작 SYN을 대량으로 보내는 상황을 떠올립니다.",
        "마지막 ACK를 완료하지 않아 서버가 연결 대기 상태를 계속 보관하게 만드는 공격을 찾습니다.",
    ],
    rules="SYN Flooding은 다수의 half-open connection으로 서버의 연결 자원을 소모시키는 DoS입니다.",
    distinctions="Smurf는 ICMP 증폭, SYN Flooding은 TCP 연결 설정 절차를 악용합니다.",
    pitfalls="3-way handshake에 끼어 세션을 탈취하는 세션 하이재킹과, 완료하지 않아 자원을 고갈시키는 공격을 구분합니다.",
    takeaway="TCP 연결을 반쯤 열어 대기열을 채우면 SYN Flooding입니다.",
)
general(
    "2025-2-14",
    "각 결정의 참·거짓을 모두 지나는 분기 커버리지",
    [
        "순서도의 각 조건 노드에서 참 경로와 거짓 경로가 적어도 한 번씩 포함되는지 확인합니다.",
        "한 경로로 모든 결과를 덮을 수 없으면 여러 경로를 한 테스트 묶음으로 작성합니다.",
        "제시 답의 두 경로 조합이 반복 진입·탈출과 내부 분기의 양쪽을 모두 통과합니다.",
    ],
    rules="분기 커버리지는 모든 결정 결과 True와 False를 최소 한 번 수행해야 합니다.",
    distinctions="문장 커버리지는 모든 문장 실행, 경로 커버리지는 가능한 모든 경로 실행을 목표로 합니다.",
    pitfalls="긴 경로 하나만 썼다고 자동으로 분기 커버리지가 되지 않으며 각 조건의 양쪽을 표시해야 합니다.",
    takeaway="제시된 두 경로 중 하나의 조합으로 모든 분기의 참·거짓을 덮습니다.",
)
general(
    "2025-2-15",
    "시간 할당량 4인 Round Robin 대기시간",
    [
        "도착한 프로세스를 준비 큐 뒤에 넣고 한 번에 최대 4초만 실행하는 간트 차트를 만듭니다.",
        "프로세스가 끝나지 않으면 남은 실행시간과 함께 큐 뒤로 보냅니다.",
        "각 완료시간에서 도착시간과 총 실행시간을 빼고 네 대기시간의 평균을 계산합니다.",
    ],
    rules="RR 대기시간은 완료시간-도착시간-실행시간이며, time slice 만료 시 미완료 프로세스는 큐 뒤로 갑니다.",
    distinctions="FCFS는 한 번 잡은 CPU를 끝까지 쓰지만 RR은 정해진 시간만큼 순환합니다.",
    pitfalls="같은 시각의 새 도착과 재큐잉 순서는 문제에서 전제한 일반적인 큐 규칙을 일관되게 적용합니다.",
    takeaway="Time Slice 4로 간트 차트를 완성하면 평균 대기시간은 11.75초입니다.",
)
code(
    "2025-2-16",
    "구조체 배열 원소 전체 복사",
    [
        "ptr은 구조체 배열 a의 첫 원소를 가리키고 pptr은 ptr의 주소입니다.",
        "`(*pptr)[2]`는 a[2]인 {5,6}입니다.",
        "이를 `(*pptr)[1]`, 즉 a[1] 전체에 대입해 x와 y가 함께 복사됩니다.",
    ],
    [
        ("매핑", "*pptr = ptr = &a[0]", "-"),
        ("오른쪽", "(*pptr)[2]", "{5,6}"),
        ("대입", "a[1]={5,6}", "-"),
        ("출력", "a[1].x, a[1].y", "5 그리고 6"),
    ],
    rules="같은 구조체 타입끼리 대입하면 모든 멤버 값이 복사됩니다.",
    output_moment="변경된 a[1]의 두 필드를 printf가 읽습니다.",
    calculation="{3,4} ← {5,6}",
    pitfalls="pptr의 별표 수에 겁먹지 말고 `(*pptr)[index]`를 `a[index]`로 바꿔 읽습니다.",
    takeaway="세 번째 구조체가 두 번째 자리에 복사되어 5 그리고 6입니다.",
    object_flow=["pptr → ptr → a[0]", "(*pptr)[1] ↔ a[1], (*pptr)[2] ↔ a[2]"],
    executed=True,
)
code(
    "2025-2-17",
    "딕셔너리 값 집합과 교집합",
    [
        "초기 dst 값은 {2,4,6}이고 이를 복사해 집합 s={2,4,6}을 만듭니다.",
        "lst[0]=99는 이미 만들어진 dst에 영향을 주지 않습니다.",
        "dst[2]=7로 dst 값 집합은 {2,7,6}, s.add(99)로 s는 {2,4,6,99}가 됩니다.",
    ],
    [
        ("초기", "dst values={2,4,6}", "s={2,4,6}"),
        ("변경 후", "dst values={2,7,6}", "s={2,4,6,99}"),
        ("교집합", "{2,6}", "길이 2"),
    ],
    rules="집합 생성 시 딕셔너리 값이 복사되므로 이후 딕셔너리 변경이 기존 집합에 자동 반영되지 않습니다.",
    output_moment="교집합 {2,6}의 len을 출력합니다.",
    calculation="|{2,4,6,99} ∩ {2,7,6}| = |{2,6}| = 2",
    pitfalls="s가 dst.values의 실시간 뷰라고 생각하면 안 됩니다.",
    takeaway="최종 두 값 집합의 공통 원소가 2와 6이라 결과는 2입니다.",
    object_flow=["dst.values() --생성 시 복사→ s", "이후 dst와 s는 별도로 변경"],
    executed=True,
)
code(
    "2025-2-18",
    "인스턴스 메서드 오버라이딩과 static 메서드 숨김",
    [
        "ref의 선언형은 Parent지만 실제 객체는 Child입니다.",
        "인스턴스 메서드 x(int)는 오버라이딩되어 Child.x가 실행되므로 2+3=5입니다.",
        "static id는 동적 호출되지 않고 참조형 Parent 기준으로 Parent.id가 선택되어 P입니다.",
    ],
    [
        ("ref.x(2)", "Child.x(int)", "5"),
        ("ref.id()", "Parent.id() static", "P"),
        ("결합", "5 + \"P\"", "5P"),
    ],
    rules=["인스턴스 메서드는 실제 객체형으로 동적 바인딩됩니다.", "static 메서드는 숨김이며 참조 변수의 선언형으로 선택됩니다."],
    output_moment="정수 5가 문자열 P와 결합될 때 5P가 됩니다.",
    calculation="(2+3) + \"P\" = \"5P\"",
    pitfalls="둘 다 Child 기준으로 보아 5C라고 답하지 않습니다.",
    takeaway="인스턴스 메서드는 Child, static 메서드는 Parent가 선택되어 5P입니다.",
    object_flow=["Parent ref → Child 객체", "x: Child / id: Parent(static)"],
    executed=True,
)
code(
    "2025-2-19",
    "배열 참조 교환과 공유 객체 필드 변경",
    [
        "arr[0]과 arr[2]의 참조를 바꾸면 배열은 c,b,a 순서지만 변수 a,b,c 자체는 그대로 각 객체를 가리킵니다.",
        "arr[1]은 b 객체, arr[0]은 c 객체입니다.",
        "`arr[1].v = arr[0].v`로 b.v가 c.v와 같은 3이 됩니다.",
    ],
    [
        ("초기", "arr=[a(1),b(2),c(3)]", "-"),
        ("교환", "arr=[c(3),b(2),a(1)]", "-"),
        ("필드 대입", "b.v=c.v", "b.v=3"),
        ("출력 변수", "a.v=1,b.v=3,c.v=3", "1a3b3"),
    ],
    rules="배열 칸에는 객체 자체가 아니라 참조가 들어 있으며 참조 교환은 객체 필드를 바꾸지 않습니다.",
    output_moment="원래 변수 a,b,c의 현재 필드를 문자열 사이에 이어 출력합니다.",
    calculation="1 + \"a\" + 3 + \"b\" + 3 = 1a3b3",
    pitfalls="배열 순서가 c,b,a가 되었다고 변수 a와 c의 정체까지 바뀌는 것은 아닙니다.",
    takeaway="참조는 교환되고 b의 값만 3으로 바뀌어 1a3b3입니다.",
    object_flow=["a→BO#1(v=1)", "b→BO#2(v=3)", "c→BO#3(v=3)", "arr=[BO#3, BO#2, BO#1]"],
    executed=True,
)
code(
    "2025-2-20",
    "머리 삽입으로 문자열을 뒤집는 연결 리스트",
    [
        "문자열 BEST를 왼쪽부터 읽지만 새 노드를 매번 현재 head 앞에 붙입니다.",
        "B 뒤 E를 앞에, S를 다시 앞에, T를 다시 앞에 붙여 리스트가 T→S→E→B가 됩니다.",
        "head부터 순회하며 문자를 출력하고 노드를 해제합니다.",
    ],
    [
        ("B", "B", "B"),
        ("E", "E→B", "EB"),
        ("S", "S→E→B", "SEB"),
        ("T", "T→S→E→B", "TSEB"),
    ],
    rules="단일 연결 리스트의 머리 삽입은 입력 순서를 역순으로 만듭니다.",
    output_moment="완성된 리스트 head에서 next를 따라 T,S,E,B를 출력합니다.",
    calculation="BEST의 머리 삽입 결과 = TSEB",
    pitfalls="입력 포인터 s의 진행 방향과 리스트의 연결 방향이 반대가 된다는 점을 기억합니다.",
    takeaway="BEST를 머리에 차례로 삽입하면 TSEB로 뒤집힙니다.",
    object_flow=["head → T → S → E → B → NULL"],
    executed=True,
)

# 2025년 3회
general(
    "2025-3-01",
    "관련 UML 요소를 묶는 패키지 다이어그램",
    [
        "유스케이스·클래스 같은 여러 모델 요소를 상위 묶음으로 그룹화한다는 점을 확인합니다.",
        "대규모 시스템에서 묶음 사이 의존 관계를 표현하는 정적 다이어그램을 패키지 다이어그램과 연결합니다.",
    ],
    rules="UML 패키지는 관련 모델 요소를 네임스페이스 단위로 묶고 패키지 간 의존성을 표현합니다.",
    distinctions="클래스 다이어그램은 클래스 구조를, 패키지 다이어그램은 더 큰 요소 묶음과 그 의존을 보여줍니다.",
    pitfalls="‘그룹화’라는 일반 표현보다 UML 정적 모델과 의존 관계라는 단서를 함께 봅니다.",
    takeaway="관련 UML 요소를 묶어 의존성을 보이는 것은 패키지 다이어그램입니다.",
)
general(
    "2025-3-02",
    "UNIX 경로·목록·이동·복사 명령",
    [
        "현재 작업 경로 출력은 print working directory의 약자 pwd입니다.",
        "파일 목록은 list의 ls, 디렉터리 변경은 change directory의 cd입니다.",
        "파일 복사는 copy의 cp입니다.",
    ],
    rules="명령 이름을 영어 동작의 약자와 연결하면 pwd·ls·cd·cp를 구분하기 쉽습니다.",
    distinctions="cat은 파일 내용 출력, chmod는 권한 변경, ps는 프로세스 목록입니다.",
    pitfalls="현재 위치를 ‘이동’하는 cd와 현재 위치를 ‘표시’하는 pwd를 바꾸지 않습니다.",
    takeaway="① pwd, ② ls, ③ cd, ④ cp입니다.",
)
general(
    "2025-3-03",
    "개별 조건식의 참·거짓을 확인하는 조건 커버리지",
    [
        "테스트 대상이 조건문 전체의 결과인지 그 안의 개별 조건식인지 구분합니다.",
        "각 개별 조건식이 True와 False를 한 번 이상 가져야 하므로 조건 커버리지입니다.",
    ],
    rules="조건 커버리지는 결정문 안의 원자 조건 각각의 참·거짓을 검사합니다.",
    distinctions="분기 커버리지는 전체 결정 결과의 참·거짓을 검사합니다.",
    pitfalls="‘조건문’이라는 말만 보고 분기 커버리지로 답하지 말고 ‘개별 조건식’을 확인합니다.",
    takeaway="개별 조건의 True·False를 모두 수행하는 기준은 조건 커버리지입니다.",
)
general(
    "2025-3-04",
    "전진 오류 수정과 재전송 방식의 오류 제어",
    [
        "수신 측이 재전송 없이 스스로 수정하는 방식은 FEC이고 대표 코드는 해밍 코드입니다.",
        "오류가 나면 송신 측에 재전송을 요구하는 방식은 BEC입니다.",
        "한 비트 검사 방식은 패리티, 다항식 방식은 CRC입니다.",
    ],
    rules="FEC는 정정 정보를 함께 보내고, BEC는 검출 뒤 재전송을 요청합니다.",
    distinctions="해밍 코드는 오류 검출·수정, 패리티와 CRC는 주로 오류 검출에 사용됩니다.",
    pitfalls="CRC를 오류 수정 코드로 분류하지 않습니다.",
    takeaway="① 해밍 ㉧, ② FEC ㉡, ③ BEC ㉢, ④ 패리티 ㉤, ⑤ CRC ㉠입니다.",
)
code(
    "2025-3-05",
    "문자열 포인터에 오프셋 더하기",
    [
        "p는 test[1]을 가리키므로 p->g는 문자열 `DC`, p->i는 2입니다.",
        "오프셋 `(p->i-1)`은 1입니다.",
        "`p->g + 1`은 문자열의 두 번째 문자 C를 가리키고 `%s`는 거기서부터 출력합니다.",
    ],
    [
        ("p", "test[1]", "i=2, g=\"DC\""),
        ("오프셋", "2-1", "1"),
        ("문자열 시작", "\"DC\"+1", "\"C\""),
        ("출력", "%s", "C"),
    ],
    rules="문자열 포인터에 n을 더하면 n번째 문자 주소로 이동하고 `%s`는 널 문자까지 출력합니다.",
    output_moment="printf가 C 위치부터 문자열 끝까지 출력합니다.",
    calculation="\"DC\"의 인덱스 1부터 = \"C\"",
    pitfalls="문자 C의 코드값을 계산하는 식이 아니라 포인터 시작 위치를 옮기는 식입니다.",
    takeaway="DC에서 한 칸 이동한 문자열은 C입니다.",
    executed=True,
)
code(
    "2025-3-06",
    "enum 배열 순서와 name 길이",
    [
        "`Tri.A.name()`은 열거 상수 이름 문자열 A이고 길이는 1입니다.",
        "`Tri.values()[1]`은 선언 순서 두 번째인 Tri.B입니다.",
        "B의 code 필드는 생성자에서 AB로 저장되었습니다.",
    ],
    [
        ("A.name()", "\"A\"", "length=1"),
        ("values()[1]", "[A,B,C]의 두 번째", "Tri.B"),
        ("B.code()", "저장 문자열", "AB"),
    ],
    rules="enum의 values 배열은 선언 순서를 유지하고 배열 인덱스는 0부터 시작합니다.",
    output_moment="선택된 Tri.B의 code() 반환값을 출력합니다.",
    calculation="index 1 → B → \"AB\"",
    pitfalls="A의 code 길이를 쓰는 것이 아니라 A의 name 길이로 다른 상수를 고릅니다.",
    takeaway="A 이름 길이 1이 B를 선택하므로 출력은 AB입니다.",
    executed=True,
)
code(
    "2025-3-07",
    "CROSS JOIN의 모든 조합에 LIKE 적용",
    [
        "A의 각 이름과 B의 각 패턴을 CROSS JOIN해 모든 이름×규칙 조합을 만듭니다.",
        "S%는 S로 시작하는 Smith와 Scott에 맞습니다.",
        "%T%는 T가 포함된 Smith와 Scott에 맞아 총 네 조합입니다.",
    ],
    [
        ("Smith", "S% 참, %T% 참", "2"),
        ("Allen", "둘 다 거짓", "0"),
        ("Scott", "S% 참, %T% 참", "2"),
        ("COUNT", "2+0+2", "4"),
    ],
    rules=["CROSS JOIN은 두 테이블 모든 행의 곱을 만듭니다.", "LIKE에서 `%`는 길이 0 이상의 임의 문자열입니다."],
    output_moment="WHERE를 통과한 이름·규칙 조합 네 개를 COUNT(*)가 셉니다.",
    calculation="Smith 2개 + Scott 2개 = 4",
    pitfalls="이름 행을 세는 것이 아니라 패턴별로 성립한 조합 행을 셉니다.",
    takeaway="두 이름이 두 규칙에 각각 맞아 조합 수는 4입니다.",
)
general(
    "2025-3-08",
    "비밀번호를 넘기지 않고 권한을 위임하는 OAuth",
    [
        "외부 앱에 사용자의 비밀번호 자체를 제공하지 않는다는 점을 확인합니다.",
        "사용자가 제한된 접근 권한을 부여하고 토큰으로 API를 사용하게 하는 표준을 OAuth와 연결합니다.",
    ],
    rules="OAuth는 인증 자격 증명을 공유하지 않고 액세스 토큰으로 권한을 위임하는 표준입니다.",
    distinctions="OpenID/OIDC는 사용자 신원 인증에 초점, OAuth는 자원 접근 권한 위임에 초점이 있습니다.",
    pitfalls="문제 문구가 ‘사용자 인증’이라고 표현해도 핵심 동작은 비밀번호 없는 권한 위임입니다.",
    takeaway="비밀번호 대신 토큰으로 외부 앱에 권한을 주면 OAuth입니다.",
)
general(
    "2025-3-09",
    "한 번만 사용하는 일회용 비밀번호 OTP",
    [
        "요청할 때마다 새 비밀번호가 생성되는지 확인합니다.",
        "한 번 사용한 값은 폐기되어 재사용할 수 없다는 특성을 OTP와 연결합니다.",
    ],
    rules="OTP는 One-Time Password의 약자로 시간·횟수·도전값 등에 따라 일회용 인증값을 만듭니다.",
    distinctions="고정 비밀번호와 달리 유출된 이전 OTP는 다음 인증에 재사용할 수 없습니다.",
    pitfalls="인증 앱이라는 제품명이 아니라 일회용 비밀번호 방식 자체를 답합니다.",
    takeaway="매번 새로 만들고 한 번 쓰면 폐기하는 비밀번호는 OTP입니다.",
)
code(
    "2025-3-10",
    "클래스의 인터페이스 구현 선언",
    [
        "Cals는 클래스가 아니라 interface로 선언되어 있습니다.",
        "클래스 Test가 이 인터페이스의 get 메서드를 구현하려면 클래스 이름 뒤에 implements를 씁니다.",
        "완성 형태는 `class Test implements Cals`입니다.",
    ],
    [
        ("대상", "Cals = interface", "-"),
        ("클래스 관계", "Test가 Cals 구현", "implements"),
        ("완성", "class Test implements Cals", "-"),
    ],
    rules="Java에서 클래스 상속은 extends, 인터페이스 구현은 implements입니다.",
    output_moment="괄호에 implements를 넣으면 Test를 Cals 참조로 생성할 수 있습니다.",
    calculation="class + interface 관계 → implements",
    pitfalls="인터페이스끼리 확장할 때의 extends와 클래스가 구현할 때의 implements를 구분합니다.",
    takeaway="Test가 Cals를 구현하므로 빈칸은 implements입니다.",
)
code(
    "2025-3-11",
    "각 리스트의 합과 길이를 튜플로 저장",
    [
        "enumerate는 각 내부 리스트에 인덱스 0~3을 붙입니다.",
        "각 리스트마다 sum과 len을 따로 계산합니다.",
        "result[index]에 `(합, 길이)` 튜플을 저장합니다.",
    ],
    [
        ("index 0", "3+5+2+4+1, 길이5", "(15,5)"),
        ("index 1", "4+5+1, 길이3", "(10,3)"),
        ("index 2", "4+4+1+5+4, 길이5", "(18,5)"),
        ("index 3", "4+5, 길이2", "(9,2)"),
    ],
    rules="딕셔너리 값은 `(list_sum, list_len)` 순서의 튜플입니다.",
    output_moment="네 튜플이 모두 저장된 result를 print합니다.",
    calculation="①15 ②5 ③10 ④3 ⑤18 ⑥5 ⑦9 ⑧2",
    pitfalls="합과 길이의 순서를 바꾸거나 딕셔너리 키를 1부터 센다고 생각하지 않습니다.",
    takeaway="각 행을 합·길이 순서로 계산하면 (15,5),(10,3),(18,5),(9,2)입니다.",
    executed=True,
)
general(
    "2025-3-12",
    "나눗셈 R÷S의 ‘모든 값’ 조건",
    [
        "S에 있는 B 값 전체를 먼저 집합으로 만듭니다.",
        "R에서 A별로 연결된 B 집합을 모읍니다.",
        "S의 모든 B 값을 빠짐없이 가진 A만 남기면 a1입니다.",
    ],
    rules="관계 나눗셈 R(A,B)÷S(B)는 S의 모든 B와 짝을 이루는 A를 반환합니다.",
    distinctions="조인은 조건에 맞는 쌍을 늘리고, 나눗셈은 ‘모든 요구 항목을 만족한 대상’을 찾습니다.",
    pitfalls="S의 B 중 하나만 가진 A가 아니라 전부 가진 A를 골라야 합니다.",
    takeaway="S의 모든 B와 짝을 이루는 A는 a1 하나입니다.",
)
general(
    "2025-3-13",
    "권한 결정 주체로 구분하는 MAC·RBAC·DAC",
    [
        "보안 등급을 시스템이 강제로 비교하면 MAC입니다.",
        "중앙 관리자가 역할별 권한을 관리하면 RBAC입니다.",
        "객체 소유자가 사용자별 권한을 정하면 DAC입니다.",
    ],
    rules="MAC=등급·시스템, RBAC=역할·관리자, DAC=신원·소유자입니다.",
    distinctions="RBAC는 개인마다 직접 권한을 붙이기보다 역할에 권한을 묶어 사용자를 배정합니다.",
    pitfalls="중앙 관리라는 말만 보고 MAC으로 고르지 말고 역할 기준인지 등급 기준인지 봅니다.",
    takeaway="① MAC, ② RBAC, ③ DAC입니다.",
)
general(
    "2025-3-14",
    "테스트 케이스의 조건·입력·기대값",
    [
        "테스트를 시작하기 위한 상황이나 전제는 테스트 조건입니다.",
        "아이디·비밀번호처럼 실제로 넣는 값은 테스트 데이터입니다.",
        "로그인 성공·실패처럼 실행 후 기대하는 상태는 예상 결과입니다.",
    ],
    rules="테스트 케이스는 무엇을 어떤 입력으로 시험해 어떤 결과를 기대하는지 구분해 기록합니다.",
    distinctions="성공/실패 기준은 판정 규칙이고 예상 결과는 해당 케이스에서 실제로 기대한 구체 결과입니다.",
    pitfalls="사용자 초기 화면 같은 사전 상태와 아이디·비밀번호 입력값을 같은 열에 넣지 않습니다.",
    takeaway="① 테스트 조건, ② 테스트 데이터, ③ 예상 결과입니다.",
)
general(
    "2025-3-15",
    "행·현재 데이터 집합·행 개수 용어",
    [
        "릴레이션의 한 행은 튜플입니다.",
        "스키마에 실제 데이터 값들이 채워진 현재 상태는 릴레이션 인스턴스입니다.",
        "그 튜플의 개수는 카디널리티입니다.",
    ],
    rules="스키마는 구조 정의, 인스턴스는 특정 시점의 실제 데이터입니다.",
    distinctions="튜플은 한 행이고 릴레이션 인스턴스는 여러 튜플로 이루어진 현재 전체 상태입니다.",
    pitfalls="릴레이션 스키마와 릴레이션 인스턴스를 ‘테이블’이라는 말 하나로 섞지 않습니다.",
    takeaway="① 튜플, ② 릴레이션 인스턴스, ③ 카디널리티입니다.",
)
code(
    "2025-3-16",
    "널 문자를 세어 얻은 길이로 뒤에서 두 번째 문자 선택",
    [
        "while문이 널 문자 전까지 a를 증가시켜 문자열 길이를 구합니다.",
        "`REPUBLICOFKOREA`의 길이는 15이므로 a는 15가 됩니다.",
        "`str[a-2]`는 인덱스 13, 끝에서 두 번째 문자 E입니다.",
    ],
    [
        ("반복 종료", "a=15", "str[15]='\\0'"),
        ("인덱스", "a-2=13", "-"),
        ("문자", "str[13]", "E"),
    ],
    rules="C 문자열 길이에는 마지막 널 문자가 포함되지 않으며 마지막 문자는 index length-1입니다.",
    output_moment="putchar가 끝에서 두 번째 위치의 E를 출력합니다.",
    calculation="length 15 → index 13 → E",
    pitfalls="a-2를 ‘끝에서 세 번째’로 착각하지 않습니다. 마지막 인덱스가 a-1이므로 a-2는 끝에서 두 번째입니다.",
    takeaway="문자열 끝에서 두 번째 문자는 E입니다.",
    executed=True,
)
code(
    "2025-3-17",
    "삼항식과 비트 시프트의 우선 순서",
    [
        "`y%3`은 1이고 1<3이 참이므로 첫 삼항식에서 z=2입니다.",
        "`z >> 1`은 1이고 `2 & 1`은 0이므로 z=0이 됩니다.",
        "x>5와 z<=3이 모두 참이라 마지막 삼항식은 z*x를 선택하지만 0×7은 0입니다.",
    ],
    [
        ("첫 삼항", "4%3=1<3", "z=2"),
        ("비트식", "2 & (2>>1=1)", "z=0"),
        ("조건식", "7>5 && 0<=3", "참"),
        ("곱셈", "0×7", "0"),
    ],
    rules=["시프트한 값과 원래 값을 비트 AND합니다.", "&&의 두 조건이 모두 참일 때 삼항식 앞 값을 선택합니다."],
    output_moment="마지막 삼항식이 0을 다시 z에 대입한 뒤 출력합니다.",
    calculation="2(10₂) & 1(01₂)=0 → 0×7=0",
    pitfalls="조건이 참이면 x 자체를 출력하는 것이 아니라 `z*x`를 계산합니다.",
    takeaway="비트 AND에서 이미 z가 0이 되어 최종 출력도 0입니다.",
    executed=True,
)
code(
    "2025-3-18",
    "자식 생성자에서 부모 생성자 호출",
    [
        "Square는 Rectangle을 상속하지만 Rectangle에 매개변수 없는 생성자가 없습니다.",
        "Square 생성자의 첫 문장에서 부모 생성자 Rectangle(a,a)를 명시적으로 호출해야 합니다.",
        "부모 생성자 호출 키워드는 super입니다.",
    ],
    [
        ("부모 생성자", "Rectangle(int,int)", "-"),
        ("자식 인수", "a,a", "-"),
        ("완성", "super(a,a)", "x=a,y=a"),
    ],
    rules="Java 자식 생성자에서 부모 생성자 호출은 `super(...)`이며 반드시 첫 문장이어야 합니다.",
    output_moment="super(a,a)가 부모 필드 x와 y를 초기화해 정사각형 넓이 계산을 가능하게 합니다.",
    calculation="빈칸 + (a,a) → super(a,a)",
    pitfalls="부모 멤버 접근 키워드 super와 현재 객체 생성자 this를 바꾸지 않습니다.",
    takeaway="부모 생성자를 부르는 빈칸은 super입니다.",
)
code(
    "2025-3-19",
    "연결 리스트 누적식과 비트 XOR",
    [
        "리스트 순서는 t3(11)→t2(7)→t1(5)입니다.",
        "각 노드에서 `sum=sum*3+x`를 적용하면 11, 40, 125가 됩니다.",
        "125와 42를 XOR한 87에 100을 더합니다.",
    ],
    [
        ("t3", "0×3+11", "11"),
        ("t2", "11×3+7", "40"),
        ("t1", "40×3+5", "125"),
        ("XOR+100", "125^42=87", "187"),
    ],
    rules="XOR는 두 비트가 서로 다를 때 1이며 연결 리스트 순서대로 누적식을 적용합니다.",
    output_moment="리스트 순회 후 `(sum ^ 42u)+100u`가 최종값을 만듭니다.",
    calculation="((11×3+7)×3+5)=125, 125^42=87, 87+100=187",
    pitfalls="노드 값의 단순 합 23을 구하는 문제가 아닙니다.",
    takeaway="3진법처럼 누적한 125를 XOR하고 100을 더해 187입니다.",
    object_flow=["curr: t3(11) → t2(7) → t1(5) → NULL"],
    executed=True,
)
code(
    "2025-3-20",
    "WHERE의 OR 조건과 COUNT(열)의 NULL 제외",
    [
        "각 행에서 COL1이 2·3인지 또는 COL2가 3·5인지 검사하면 다섯 행이 모두 조건을 통과합니다.",
        "하지만 COUNT(COL2)는 통과 행 수가 아니라 COL2가 NULL이 아닌 값만 셉니다.",
        "첫 행의 COL2만 NULL이므로 나머지 네 값을 셉니다.",
    ],
    [
        ("2,NULL", "COL1 조건 참", "COL2 NULL → 미집계"),
        ("3,6 / 2,3", "조건 참", "2개 집계"),
        ("NULL,3 / 4,5", "COL2 조건 참", "2개 집계"),
        ("COUNT(COL2)", "NULL 제외", "4"),
    ],
    rules="COUNT(*)는 행을 세지만 COUNT(열)은 그 열의 NULL을 제외합니다.",
    output_moment="WHERE 통과 후 COL2의 비NULL 값 네 개를 집계합니다.",
    calculation="통과 5행 - COL2 NULL 1행 = 4",
    pitfalls="OR 조건 때문에 모든 행이 통과해도 COUNT(COL2)가 5가 되지는 않습니다.",
    takeaway="조건은 5행이 통과하지만 NULL을 빼서 결과는 4입니다.",
)

# 2026년 1회
general(
    "2026-1-01",
    "추상과 구현을 분리하는 Bridge, 상태 변화를 알리는 Observer",
    [
        "기능의 추상층과 구현부를 별도 계층으로 나누어 각각 확장한다는 설명은 Bridge입니다.",
        "한 객체 상태가 바뀔 때 의존하는 여러 객체에 알리는 일대다 구조는 Observer입니다.",
    ],
    rules="Bridge는 구조 패턴, Observer는 발행·구독 관계를 만드는 행위 패턴입니다.",
    distinctions="Adapter는 이미 맞지 않는 인터페이스를 변환하고, Bridge는 처음부터 추상과 구현을 분리해 확장합니다.",
    pitfalls="Observer 설명의 ‘상속된 객체’라는 표현보다 일대다 상태 알림과 Publish/Subscribe 단서를 우선합니다.",
    takeaway="① Bridge, ② Observer입니다.",
)
general(
    "2026-1-02",
    "비기능 요구사항의 운영·자원·성능 분류",
    [
        "여러 운영체제에서 동작해야 한다는 환경 제약은 운영요구사항입니다.",
        "메모리 사용량을 제한하는 것은 자원요구사항입니다.",
        "1초 이내 응답처럼 측정 가능한 속도 기준은 성능요구사항입니다.",
    ],
    rules="비기능 요구사항은 무엇을 하는가보다 어떤 품질·환경·제약 아래 동작하는가를 정의합니다.",
    distinctions="자원은 CPU·메모리·저장공간 사용량, 성능은 응답시간·처리량 같은 결과 지표입니다.",
    pitfalls="‘시스템이 동작해야 한다’는 공통 문구보다 OS·메모리·1초라는 측정 대상을 봅니다.",
    takeaway="① 운영, ② 자원, ③ 성능요구사항입니다.",
)
code(
    "2026-1-03",
    "배열 표기와 포인터 표기의 같은 평균 계산",
    [
        "arr1의 p[i]와 arr2의 *(p+i)는 같은 배열 원소를 읽는 두 표기입니다.",
        "열 값의 합은 530이고 길이 10이므로 각 함수의 평균은 53.0입니다.",
        "두 평균을 더한 106을 소수 둘째 자리 형식으로 출력합니다.",
    ],
    [
        ("배열 합", "70+50+…+25", "530"),
        ("arr1", "530/10", "53.0"),
        ("arr2", "530/10", "53.0"),
        ("합과 형식", "106.0, %.2f", "106.00"),
    ],
    rules="배열 매개변수 `int p[]`와 포인터 매개변수 `int *p`는 이 사용에서 같은 원소열을 가리킵니다.",
    output_moment="두 double 평균을 더한 뒤 `%.2f`가 소수 둘째 자리까지 표시합니다.",
    calculation="53.00 + 53.00 = 106.00",
    pitfalls="두 함수가 서로 다른 배열을 계산한다고 생각하거나 출력 형식의 .00을 빼먹지 않습니다.",
    takeaway="두 표기는 같은 평균 53을 계산하므로 합은 106.00입니다.",
    executed=True,
)
code(
    "2026-1-04",
    "이름 있는 외래키 제약조건 CREATE 문법",
    [
        "제약조건에 TEAM_TF라는 이름을 붙이므로 `CONSTRAINT TEAM_TF`로 시작합니다.",
        "PLAYER에서 외래키가 될 열은 `FOREIGN KEY (TEAM_ID)`로 지정합니다.",
        "참조 대상은 `REFERENCES TEAM (TEAM_ID2)`로 씁니다.",
    ],
    [
        ("제약 이름", "CONSTRAINT TEAM_TF", "① CONSTRAINT"),
        ("외래키", "FOREIGN KEY (TEAM_ID)", "② FOREIGN / ③ TEAM_ID"),
        ("참조", "REFERENCES TEAM (TEAM_ID2)", "④ REFERENCES / ⑤ TEAM_ID2"),
    ],
    rules="외래키 구문은 `CONSTRAINT 이름 FOREIGN KEY (자식열) REFERENCES 부모테이블 (부모열)` 순서입니다.",
    output_moment="문법 골격과 문제에 지정된 열 이름을 대응하면 다섯 빈칸이 완성됩니다.",
    calculation="CONSTRAINT → FOREIGN → TEAM_ID → REFERENCES → TEAM_ID2",
    pitfalls="자식 테이블 열 TEAM_ID와 부모 테이블 참조 열 TEAM_ID2의 위치를 바꾸지 않습니다.",
    takeaway="완성 구문은 `CONSTRAINT TEAM_TF FOREIGN KEY (TEAM_ID) REFERENCES TEAM (TEAM_ID2)`입니다.",
)
code(
    "2026-1-05",
    "역방향 슬라이스에서 두 칸씩 선택",
    [
        "`range(10)`은 0부터 9까지의 리스트를 만듭니다.",
        "`lst[::-2]`는 끝 9에서 시작해 왼쪽으로 두 칸씩 이동하여 9,7,5,3,1을 만듭니다.",
        "각 숫자 뒤에 A를 붙이고 줄바꿈 없이 출력한 뒤 마지막 print가 줄을 바꿉니다.",
    ],
    [
        ("원본", "0,1,2,3,4,5,6,7,8,9", "-"),
        ("슬라이스", "9,7,5,3,1", "-"),
        ("반복 출력", "각 값 + A", "9A7A5A3A1A"),
    ],
    rules="슬라이스 step이 음수면 오른쪽에서 왼쪽으로 이동하며 시작·끝을 생략하면 끝 원소부터 시작합니다.",
    output_moment="for문의 다섯 print가 같은 줄에 이어진 뒤 빈 print가 줄바꿈합니다.",
    calculation="9A + 7A + 5A + 3A + 1A",
    pitfalls="range(10)에 10이 포함된다고 생각하거나 step -2를 값에서 2를 빼는 별도 연산으로 보지 않습니다.",
    takeaway="9부터 홀수만 역순으로 골라 9A7A5A3A1A가 됩니다.",
    executed=True,
)
code(
    "2026-1-06",
    "오버로딩은 컴파일 시, 오버라이딩은 실행 시",
    [
        "a.g()는 A에 정의된 g를 실행하고 그 안에서 `f(\"a\")`를 호출합니다.",
        "A.g를 컴파일할 때 보이는 후보는 A.f(Object)이므로 호출 시그니처는 f(Object)로 고정됩니다.",
        "실제 객체 B가 이 시그니처를 오버라이딩했으므로 B.f(Object)가 실행되어 2를 반환합니다.",
    ],
    [
        ("a.g()", "A.g 실행", "f(\"a\") 호출"),
        ("오버로딩 선택", "A에서 f(Object)", "시그니처 고정"),
        ("동적 바인딩", "B.f(Object)", "\"2\""),
        ("출력", "반환 문자열", "2"),
    ],
    rules=["오버로딩 후보 선택은 컴파일 시 선언된 타입 범위에서 이뤄집니다.", "선택된 시그니처의 오버라이딩 구현은 실제 객체형으로 결정됩니다."],
    output_moment="B.f(Object)가 문자열 2를 g에 반환하고 println이 출력합니다.",
    calculation="A.g → 선택 f(Object) → 실제 B.f(Object) → \"2\"",
    pitfalls="인수가 문자열이라는 이유로 B.f(String)이 나중에 선택된다고 생각하면 안 됩니다.",
    takeaway="시그니처는 A의 f(Object), 구현은 B의 f(Object)라서 2입니다.",
    object_flow=["A a → B 객체", "A.g() → f(Object) → B.f(Object)"],
    executed=True,
)
general(
    "2026-1-07",
    "조직의 정보보호를 통합 관리하는 ISMS",
    [
        "개별 보안 제품이 아니라 정책·위험·대책을 조직 차원에서 지속 관리하는 체계인지 확인합니다.",
        "KISA가 평가·인증하는 정보보호 관리 체계라는 표현을 ISMS와 연결합니다.",
    ],
    rules="ISMS는 Information Security Management System의 약자로 관리적·기술적·물리적 보호조치를 체계화합니다.",
    distinctions="ISO 27001도 정보보호 경영시스템 국제표준이지만 문제의 KISA 인증 명칭은 ISMS입니다.",
    pitfalls="보안 시스템 한 종류가 아니라 조직 전체의 관리 체계라는 범위를 놓치지 않습니다.",
    takeaway="KISA가 인증하는 정보보호 관리 체계는 ISMS입니다.",
)
general(
    "2026-1-08",
    "/23 네트워크 주소의 2단위 블록",
    [
        "255.255.254.0은 /23이며 세 번째 옥텟의 블록 크기는 256-254=2입니다.",
        "A의 11은 10~11 블록에 있어 네트워크가 192.168.10.0/23입니다.",
        "B의 12는 12~13 블록에 있어 네트워크가 192.168.12.0/23입니다.",
    ],
    rules="/23은 세 번째 옥텟이 짝수부터 두 개씩 한 네트워크를 이룹니다.",
    distinctions="호스트 IP를 그대로 /23로 적는 것이 아니라 호스트 비트를 모두 0으로 만든 네트워크 주소를 적습니다.",
    pitfalls="11을 단순히 1 빼고 12는 그대로 두는 암기 대신 2단위 블록 경계를 계산합니다.",
    takeaway="A는 192.168.10.0/23, B는 192.168.12.0/23입니다.",
)
general(
    "2026-1-09",
    "표적이 자주 가는 사이트를 미리 감염시키는 Watering Hole",
    [
        "공격자가 피해자에게 직접 링크를 보내는 대신 목표 조직의 방문 습관을 조사하는지 확인합니다.",
        "자주 방문하는 정상 사이트를 먼저 감염시켜 방문자를 노리는 방식을 Watering Hole과 연결합니다.",
    ],
    rules="Watering Hole은 먹잇감이 모이는 물웅덩이를 기다리듯 표적 집단의 방문 사이트를 감염시키는 공격입니다.",
    distinctions="Drive-by Download는 방문만으로 감염되는 전달 방식이고, Watering Hole은 특정 표적이 자주 찾는 사이트를 골라 함정을 놓는 전략입니다.",
    pitfalls="웹 방문 감염이라는 공통점만 보지 말고 사전 표적 조사 여부를 확인합니다.",
    takeaway="목표 조직이 자주 가는 사이트를 선감염하면 Watering Hole입니다.",
)
general(
    "2026-1-10",
    "요구 분석에서 구현까지의 데이터베이스 설계 단계",
    [
        "먼저 사용자의 데이터·처리 요구를 수집하고 분석합니다.",
        "현실 세계를 개념 모델로 만들고, DBMS에 맞는 논리 구조로 바꾼 뒤 저장 구조를 물리적으로 정합니다.",
        "정해진 스키마를 실제 DBMS에 생성하고 데이터를 적재하는 구현으로 마칩니다.",
    ],
    rules="일반 순서는 요구 조건 분석→개념적 설계→논리적 설계→물리적 설계→구현입니다.",
    distinctions="개념적 설계는 DBMS 독립적, 논리적 설계는 데이터 모델·DBMS 관점, 물리적 설계는 저장·접근 경로 관점입니다.",
    pitfalls="논리 스키마 설계는 논리적 설계의 세부 활동이며 보기의 전체 단계명과 혼동하지 않습니다.",
    takeaway="① 요구 조건 분석, ② 개념적, ③ 논리적, ④ 물리적 설계, ⑤ 데이터베이스 구현입니다.",
)
code(
    "2026-1-11",
    "평균보다 큰 부서 예산으로 조인 행 거르기",
    [
        "DEPT 예산 평균은 (3000+5000+7000+9000)/4=6000입니다.",
        "평균보다 큰 부서는 D03의 7000과 D04의 9000입니다.",
        "EMPLOYEE에서 이 부서와 조인되는 직원 E03과 E04 두 명을 셉니다.",
    ],
    [
        ("AVG", "총 24000 / 4", "6000"),
        ("부서 필터", "D03=7000, D04=9000", "2개"),
        ("직원 조인", "E03, E04", "2행"),
        ("COUNT", "2행", "2"),
    ],
    rules="스칼라 부질의 AVG 결과를 먼저 한 값으로 계산한 뒤 바깥 WHERE의 각 조인 행과 비교합니다.",
    output_moment="예산 6000 초과 부서의 직원 두 행을 COUNT(*)가 셉니다.",
    calculation="AVG=6000, 조건 만족 7000·9000 → 2",
    pitfalls="평균 이상(>=)이 아니라 평균 초과(>)이므로 같은 값이 있다면 제외해야 합니다.",
    takeaway="평균 예산 6000보다 큰 부서 직원은 두 명이라 결과는 2입니다.",
)
general(
    "2026-1-12",
    "절차적·교환적·기능적 응집도의 단서",
    [
        "기능 관련성은 약하지만 정해진 순서로 실행되면 절차적 응집도입니다.",
        "서로 다른 기능이 같은 입력·출력 데이터를 사용하면 교환적 응집도입니다.",
        "모든 요소가 하나의 기능에 밀접하면 기능적 응집도입니다.",
    ],
    rules="절차적=실행 순서, 교환적=공통 데이터, 기능적=하나의 목적입니다.",
    distinctions="순차적 응집도는 앞 출력이 다음 입력이 되는 데이터 흐름까지 필요합니다.",
    pitfalls="‘순차적으로 실행’이라는 표현을 순차적 응집도로 바로 고르지 말고 출력→입력 연결이 있는지 봅니다.",
    takeaway="① 절차적 ㉣, ② 교환적 ㉢, ③ 기능적 ㉠입니다.",
)
general(
    "2026-1-13",
    "통합 테스트에서 없는 모듈을 대신하는 스텁과 드라이버",
    [
        "하향식에서는 아직 붙지 않은 하위 모듈의 반환 동작을 스텁이 대신합니다.",
        "상향식에서는 아직 없는 상위 모듈처럼 하위 클러스터를 호출하는 드라이버를 만듭니다.",
    ],
    rules="스텁은 호출받는 가짜 하위 모듈, 드라이버는 테스트 대상을 호출하는 가짜 상위 모듈입니다.",
    distinctions="Top-down=Stub, Bottom-up=Driver로 방향과 역할을 함께 외웁니다.",
    pitfalls="자동차의 위·아래 이미지보다 ‘누가 누구를 호출하는가’로 구분하면 덜 헷갈립니다.",
    takeaway="① 스텁, ② 드라이버입니다.",
)
general(
    "2026-1-14",
    "경로를 저장하는 심볼릭 링크와 링크 교체 공격",
    [
        "원본 파일 내용·inode를 공유하는 것이 아니라 대상 경로 정보를 담는 별도 링크 파일인지 확인합니다.",
        "공격자가 임시 파일 자리에 같은 이름의 링크를 만들어 중요 파일을 가리키게 하는 레이스 조건을 따라갑니다.",
    ],
    rules="심볼릭 링크는 대상 경로를 저장하며 대상이 없어지면 끊어진 링크가 될 수 있습니다.",
    distinctions="하드 링크는 같은 inode를 가리키고 심볼릭 링크는 다른 파일의 경로를 가리킵니다.",
    pitfalls="임시 파일은 이름만 믿지 말고 생성·검사·열기를 원자적으로 처리해 링크 교체 시간을 주지 않아야 합니다.",
    takeaway="경로를 가리키며 임시 파일 레이스 공격에 악용될 수 있는 것은 심볼릭 링크입니다.",
)
code(
    "2026-1-15",
    "함수 포인터 반환 주소와 16진수 출력",
    [
        "mine.fn은 int 포인터를 받아 int 포인터를 돌려주는 dummy를 가리킵니다.",
        "dummy(n)은 `n+1`을 반환하므로 배열의 두 번째 원소 32의 주소입니다.",
        "역참조 값 32를 `%x`로 출력하면 16진수 20입니다.",
    ],
    [
        ("함수 포인터", "mine.fn=dummy", "-"),
        ("dummy(n)", "n+1", "&n[1]"),
        ("역참조", "*(&n[1])", "32"),
        ("형식 변환", "32 decimal → hex", "20"),
    ],
    rules=["포인터에 1을 더하면 다음 배열 원소 주소로 이동합니다.", "`%x`는 정수를 16진수 소문자로 표시합니다."],
    output_moment="32라는 값이 printf의 %x 형식으로 변환될 때 화면에는 20이 나옵니다.",
    calculation="n[1]=32₁₀=20₁₆",
    pitfalls="배열 값 32를 그대로 쓰거나 0x20처럼 접두사를 붙이지 않습니다.",
    takeaway="두 번째 값 32를 16진수로 출력하므로 20입니다.",
    executed=True,
)
code(
    "2026-1-16",
    "문자열 역순 뒤 특정 문자 제거",
    [
        "입력 HumanDev에는 공백이 없어 split과 join 뒤에도 HumanDev입니다.",
        "역순은 veDnamuH입니다.",
        "역순 문자 중 o, n, g에 속하는 문자를 버리므로 n 하나가 제거됩니다.",
    ],
    [
        ("입력 정리", "HumanDev", "HumanDev"),
        ("역순", "veDnamuH", "-"),
        ("o/n/g 제거", "n 제거", "veDamuH"),
    ],
    rules="조건 `c not in 'ong'`는 부분 문자열 ong를 지우는 것이 아니라 문자 o·n·g 각각을 제외합니다.",
    output_moment="제너레이터가 남긴 문자를 join한 z를 출력합니다.",
    calculation="reverse(HumanDev)=veDnamuH → n 제거 = veDamuH",
    pitfalls="대소문자를 구분하므로 대문자 G가 있었다면 소문자 g와 같지 않습니다.",
    takeaway="뒤집은 뒤 n을 빼서 veDamuH가 됩니다.",
    executed=True,
)
general(
    "2026-1-17",
    "HDLC 프레임 종류와 두 비동기 동작 모드",
    [
        "사용자 데이터를 전달하는 I 프레임은 정보 프레임입니다.",
        "흐름·오류 제어를 담당하는 S 프레임은 감독 프레임, 링크 관리를 담당하는 U 프레임은 비번호 프레임입니다.",
        "복합국끼리 대등하게 통신하면 비동기 균형 모드, 종국이 주국 허락 없이 전송하면 비동기 응답 모드입니다.",
    ],
    rules="HDLC 프레임은 I(Information), S(Supervisory), U(Unnumbered)로 구분합니다.",
    distinctions="ABM은 복합국 간 대등 구조, ARM은 주국·종국 구조에서 종국이 허락 없이 전송 가능한 모드입니다.",
    pitfalls="S를 ‘동기’가 아니라 Supervisory의 감독으로, U를 Unnumbered의 비번호로 풉니다.",
    takeaway="① 정보, ② 감독, ③ 비번호, ④ 비동기 균형, ⑤ 비동기 응답 모드입니다.",
)
code(
    "2026-1-18",
    "DISTINCT와 COUNT(DISTINCT)의 결과 행 수",
    [
        "DISTINCT 없는 첫 SELECT는 학생 200명의 DEPT 값을 모두 반환하므로 200행입니다.",
        "DISTINCT DEPT는 세 학과 이름만 남겨 3행입니다.",
        "전산과로 제한한 뒤 COUNT(DISTINCT DEPT)는 서로 다른 학과 값 하나를 셉니다.",
    ],
    [
        ("① SELECT DEPT", "50+100+50명", "200행"),
        ("② DISTINCT DEPT", "전기/전산/전자", "3행"),
        ("③ WHERE 전산과", "서로 다른 DEPT={전산과}", "1"),
    ],
    rules="DISTINCT는 중복 행을 제거하고 COUNT(DISTINCT 열)은 서로 다른 비NULL 값의 수를 반환합니다.",
    output_moment="각 질의가 반환하는 튜플 수를 따로 세면 200,3,1입니다.",
    calculation="①200 ②3 ③1",
    pitfalls="세 번째 질의가 전산과 학생 100명을 세는 것이 아니라 서로 다른 DEPT 값의 개수를 셉니다.",
    takeaway="중복 제거 범위에 따라 결과 튜플 수는 200, 3, 1입니다.",
)
code(
    "2026-1-19",
    "오버로딩 선택과 문자열 결합 시작점",
    [
        "cc(5,4)는 int 버전으로 9를 반환합니다.",
        "cc('c','a')는 char 두 개 버전으로 문자 코드 차 2를 반환하고 cc('3')은 문자 3을 반환합니다.",
        "a+b는 문자열을 만나기 전이라 정수 덧셈 11이고, 그 뒤 \"2\"와 문자 3이 차례로 붙습니다.",
    ],
    [
        ("a", "5+4", "9"),
        ("b", "'c'-'a'", "2"),
        ("c", "cc('3')", "'3'"),
        ("표현식", "9+2+\"2\"+'3'", "1123"),
    ],
    rules="Java `+`는 문자열을 만나기 전까지 숫자 덧셈을 하고, 문자열을 만난 뒤에는 왼쪽부터 문자열 결합을 합니다.",
    output_moment="정수 합 11이 문자열 \"2\"를 만나는 순간 \"112\"가 되고 문자 3이 붙습니다.",
    calculation="9+2=11 → \"11\"+\"2\"+\"3\" = \"1123\"",
    pitfalls="9,2를 처음부터 각각 문자열로 붙여 9223이라고 계산하지 않습니다.",
    takeaway="숫자 합 11 뒤에 2와 3이 문자열로 붙어 1123입니다.",
    executed=True,
)
code(
    "2026-1-20",
    "얕은 복사된 바깥 리스트와 공유되는 안쪽 리스트",
    [
        "m은 `[1] [2] [3] [4]`라는 네 개의 안쪽 리스트를 만들고, `b=m[:]`는 바깥 리스트만 복사합니다.",
        "b의 각 칸은 m과 같은 안쪽 리스트를 가리키므로 `+=`가 그 리스트를 제자리에서 늘리면 m에도 보입니다.",
        "안쪽 리스트 길이는 차례로 1,2,3,4가 되어 합이 10입니다.",
    ],
    [
        ("초기", "m 길이 [1,1,1,1]", "-"),
        ("i=0", "b[1]+=[1]", "길이 [1,2,1,1]"),
        ("i=1", "b[2]+=[2,1]", "길이 [1,2,3,1]"),
        ("i=2", "b[3]+=[3,2,1]", "길이 [1,2,3,4]"),
        ("합", "1+2+3+4", "10"),
    ],
    rules=["`m[:]`는 바깥 리스트의 얕은 복사입니다.", "리스트의 `+=`는 새 리스트 대입이 아니라 기존 리스트를 제자리 확장합니다."],
    output_moment="공유된 안쪽 리스트들의 최종 길이를 sum할 때 10이 됩니다.",
    calculation="1 + 2 + 3 + 4 = 10",
    pitfalls="b를 완전한 깊은 복사로 생각하면 m의 길이가 모두 1이라 잘못 계산합니다.",
    takeaway="바깥만 복사되어 안쪽 변경을 공유하므로 최종 길이 합은 10입니다.",
    object_flow=["m[0] ─┬→ [1] ←┬─ b[0]", "m[1] ─┬→ [2,1] ←┬─ b[1]", "나머지 칸도 같은 안쪽 객체 공유"],
    executed=True,
)


def main() -> None:
    expected_ids = set(QUESTIONS)
    authored_ids = set(EDITORIAL)
    missing = sorted(expected_ids - authored_ids)
    extra = sorted(authored_ids - expected_ids)
    if missing or extra:
        raise SystemExit(
            f"Editorial coverage mismatch: missing={missing}, extra={extra}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    by_exam: dict[str, dict[str, object]] = {}
    for question_id, explanation in EDITORIAL.items():
        exam_id = question_id.rsplit("-", 1)[0]
        by_exam.setdefault(exam_id, {})[question_id] = explanation
    for exam_id, explanations in sorted(by_exam.items()):
        path = OUTPUT_DIR / f"{exam_id}.json"
        path.write_text(
            json.dumps(explanations, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Built {len(EDITORIAL)} authored explanations in {len(by_exam)} files.")


if __name__ == "__main__":
    main()
