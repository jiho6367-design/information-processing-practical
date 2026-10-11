"""Build the offline TOP10 study room from reviewed local exam data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMS = json.loads((ROOT / 'src/data/exams.json').read_text(encoding='utf-8'))['exams']

def part(label, answer, *aliases):
    return dict(label=label, answer=answer, acceptedAnswers=[answer, *aliases])

def custom(prompt, answers, steps, code=None):
    blocks = [dict(type='prose', text=prompt)]
    if code:
        blocks.append(dict(type='code', text=code))
    return dict(promptBlocks=blocks, answerParts=answers, steps=steps)

def source(exam, number):
    q = next(q for e in EXAMS if e['id'] == exam for q in e['questions'] if q['number'] == number)
    return dict(promptBlocks=q['promptBlocks'], answerParts=q['answerParts'], steps=q['friendlyExplanation']['steps'], trace=q['friendlyExplanation'].get('trace'), source=f'보관 PDF {exam} · {number}번 · {q["sourcePage"]}쪽')

concepts = [
 ('구조체와 문자열 포인터', ['p->i는 p가 가리키는 구조체의 i입니다. 배열 인덱스는 0부터 셉니다.', '문자열 주소 + k는 시작 위치를 k칸 옮깁니다. %s는 그 위치부터 널 문자 전까지 출력합니다.'], '"HELLO" + 2 → LLO', '문자 하나만 출력하는 %c와 문자열 끝까지 출력하는 %s를 구분하세요.'),
 ('얕은 복사와 +=', ['m[:]는 바깥 리스트만 새로 만들고 내부 객체의 참조는 공유합니다.', '리스트의 +=는 기존 내부 리스트를 늘립니다. +로 새 리스트를 만들어 대입하면 참조를 바꿉니다.'], 'm[0] ─┐\n       ├→ 같은 내부 리스트\nb[0] ─┘', '값보다 객체가 같은지를 먼저 추적하세요.'),
 ('HDLC 프레임', ['I(정보): 사용자 데이터 전달. S(감독): 흐름·오류 제어. U(비번호): 링크 설정·관리.', '제어부 시작 패턴은 I=0, S=10, U=11입니다. ABM은 대등한 복합국, ARM은 주국·종국 구조입니다.'], '데이터 I  →  흐름·오류 S  →  링크 관리 U', '프레임 종류와 통신 동작 모드는 서로 다른 분류입니다.'),
 ('함수 포인터와 출력 형식', ['int* (*fn)(int*)는 int*를 받아 int*를 반환하는 함수의 포인터입니다.', '함수 호출 → 반환 주소 → 역참조 값 → printf 출력 형식 순서로 추적합니다.'], '48(십진수) → %x → 30(16진수)', '주소를 옮기는 것과 값을 출력하는 것을 구분하고 마지막에 %d/%x를 확인하세요.'),
 ('외래키 제약조건', ['CONSTRAINT는 제약 이름, FOREIGN KEY는 현재 테이블의 열을 지정합니다.', 'REFERENCES 뒤에는 참조할 부모 테이블과 부모 열을 씁니다.'], 'CONSTRAINT 이름\nFOREIGN KEY (자식열)\nREFERENCES 부모테이블 (부모열)', '자식열과 부모열의 이름이 같아야 하는 것은 아닙니다.'),
 ('enumerate·sum·len', ['enumerate는 기본적으로 0부터 인덱스와 요소를 함께 줍니다.', 'sum은 원소의 합, len은 원소의 개수입니다. 튜플에 넣는 순서를 확인하세요.'], '[2, 7, 2] → (합, 길이) = (11, 3)', '중복된 값도 각각 원소 한 개로 셉니다.'),
 ('Java 생성자와 오버라이딩', ['부모 필드 초기화·부모 생성자 → 자식 필드 초기화·자식 생성자 순서입니다.', '인스턴스 메서드는 실제 객체형에 따라 호출됩니다. 같은 이름의 필드는 각각 존재하며 static 필드는 공유됩니다.'], 'new Child → Parent 생성 → Child 초기화 → Child 생성', '부모 생성자 안에서도 오버라이딩된 자식 메서드가 호출될 수 있습니다.'),
 ('E-R 다이어그램', ['사각형은 개체, 마름모는 관계, 타원은 속성입니다. 연결은 선으로 나타냅니다.', '이중 타원은 다중값 속성, 점선 타원은 유도 속성, 밑줄은 키 속성입니다.'], '□ 개체 ─ ◇ 관계 ─ □ 개체\n    │\n   ○ 속성', '관계 자체도 속성을 가질 수 있습니다.'),
 ('ARP와 ARP 스푸핑', ['ARP는 로컬 네트워크에서 IP 주소에 대응하는 MAC 주소를 찾습니다.', 'ARP 스푸핑은 거짓 IP–MAC 대응을 믿게 만들어 통신이 공격자를 거치도록 유도합니다.'], '정상: 게이트웨이 IP → 게이트웨이 MAC\n변조: 게이트웨이 IP → 공격자 MAC', '공격 이름을 묻는 문제에는 ARP만 쓰지 않고 스푸핑까지 쓰세요.'),
 ('SOAP와 웹 서비스', ['SOAP는 XML로 구조화한 메시지를 교환하는 프로토콜입니다.', 'Envelope는 전체 메시지, 선택적인 Header는 부가 정보, Body는 실제 내용을 담습니다.'], 'Envelope\n ├ Header (선택)\n └ Body (필수)', 'SOAP, 서비스 기술 언어 WSDL, 서비스 검색 UDDI를 구분하세요.'),
]

orig = [source('2025-3',5), source('2026-1',20),
 custom('HDLC는 비트 중심 데이터 링크 제어 프로토콜입니다. 각 설명에 맞는 프레임 종류의 이름을 쓰세요.\n① 실제 사용자 데이터를 전송하는 프레임\n② 흐름 제어와 오류 제어를 수행하는 프레임\n③ 링크 설정 및 관리를 수행하는 프레임', [part('①','정보','정보 프레임','I','I 프레임','Information','Information frame'),part('②','감독','감독 프레임','S','S 프레임','Supervisory','Supervisory frame'),part('③','비번호','비번호 프레임','U','U 프레임','Unnumbered','Unnumbered frame')], ['데이터 전달은 I(정보)입니다.', '흐름·오류 제어는 S(감독)입니다.', '링크 설정·관리는 U(비번호)입니다.']),
 source('2026-1',15), source('2026-1',4), source('2025-3',11), source('2025-1',11),
 custom('E-R 다이어그램에서 각 설명에 해당하는 기호의 명칭을 쓰세요.\n① 개체 집합과 관계 집합을 연결하는 기호\n② 개체 집합을 나타내는 기호\n③ 관계 집합을 나타내는 기호\n④ 속성을 나타내는 기호', [part('①','선','연결선','직선','line'),part('②','사각형','직사각형','rectangle'),part('③','마름모','diamond'),part('④','타원','타원형','ellipse','oval')], ['연결은 선으로 나타냅니다.', '개체는 사각형, 관계는 마름모입니다.', '속성은 타원으로 나타냅니다.']),
 custom('근거리 통신망(LAN)에서 주소 변환 프로토콜 메시지를 조작해 거짓 IP–MAC 대응 정보를 전달하고, 상대방의 데이터 패킷을 중간에서 가로채는 네트워크 공격 기법의 명칭을 쓰세요.', [part('공격 기법','ARP 스푸핑','ARP spoofing','ARP스푸핑(ARP spoofing)','ARP poisoning','ARP cache poisoning','ARP 포이즈닝')], ['IP 주소와 MAC 주소의 대응을 다루는 프로토콜은 ARP입니다.', '거짓 대응 정보를 이용해 통신을 가로채는 공격은 ARP 스푸핑입니다.', 'ARP만 적으면 프로토콜 이름이므로 공격 기법 답으로는 부족합니다.']),
 custom('HTTP, HTTPS, SMTP 등을 통해 XML 기반의 메시지를 교환하고, 메시지를 Envelope·Header·Body 구조로 구성하는 웹 서비스 프로토콜의 명칭을 쓰세요.', [part('프로토콜','SOAP','Simple Object Access Protocol','SOAP(Simple Object Access Protocol)')], ['XML 메시지 교환과 Envelope 구조가 SOAP를 가리킵니다.', 'HTTP 등은 메시지를 운반하는 하위 프로토콜이고, 답은 SOAP입니다.'])
]
orig[2]['source']='2026-1 PDF 17번의 프레임 3종 설명을 목록의 범위에 맞춰 재구성했습니다. PDF의 동작 모드 2칸은 응용 개념에서 다룹니다.'
orig[4]['promptBlocks']=[dict(type='prose', text='PLAYER.TEAM_ID가 TEAM.TEAM_ID2를 참조하도록 아래 ①~⑤를 채우세요. 제약 이름은 TEAM_TF입니다.'),dict(type='code',text='CREATE TABLE PLAYER (\n  PLAYER_ID CHAR(7) NOT NULL,\n  PLAYER_NAME VARCHAR2(20) NOT NULL,\n  TEAM_ID CHAR(3) NOT NULL,\n  PRIMARY KEY (PLAYER_ID),\n  (①) TEAM_TF (②) KEY ((③)) (④) TEAM ((⑤))\n);')]
orig[7]['source']='보관 PDF 2022-3 · 18번 · 12쪽: 같은 E-R 개념. 보내주신 설명 범위에 맞춘 명칭형 재구성(원문은 도형 기호 선택형).'
orig[8]['source']='보관 PDF 2021-3 · 2번 · 2쪽: 같은 ARP 스푸핑 개념. 원문은 “( ) 스푸핑”의 빈칸형이며 여기서는 공격 전체 이름을 묻습니다.'
orig[9]['source']='보관 PDF 2020-2 · 13번 · 5쪽의 SOAP 설명을 재구성했습니다.'

apps = [
 custom('아래 C 코드의 출력값을 쓰세요.',[part('출력','LLO')],['p는 t[1]을 가리켜 i=3, g="HELLO"입니다.','오프셋 3-1=2를 더하면 세 번째 문자 L부터 출력합니다.','%s는 문자열 끝까지 출력하므로 LLO입니다.'], '#include <stdio.h>\nstruct Test { int i; const char *g; };\nint main(void) {\n  struct Test t[] = {{1, "CODE"}, {3, "HELLO"}};\n  struct Test *p = &t[1];\n  printf("%s", p->g + p->i - 1);\n}'),
 custom('+=를 +와 대입으로 바꾸었습니다. 두 출력값을 순서대로 쓰세요.',[part('① m의 길이 합','3'),part('② b의 길이 합','6')],['b=m[:]에서 내부 리스트는 처음에는 공유됩니다.','b[i+1] = b[i+1] + b[i]는 새 리스트를 만들어 b의 참조만 바꿉니다.','m의 길이는 1,1,1로 합 3입니다. b의 길이는 1,2,3으로 합 6입니다.'], 'm = [[1], [2], [3]]\nb = m[:]\nfor i in range(len(b) - 1):\n    b[i+1] = b[i+1] + b[i]\nprint(sum(len(x) for x in m))\nprint(sum(len(x) for x in b))'),
 custom('HDLC 제어부 시작 패턴으로 프레임 이름을 쓰세요.\n① 11: 링크 관리\n② 0: 사용자 데이터\n③ 10: 흐름·오류 제어', [part('①','비번호','U','U 프레임','비번호 프레임','Unnumbered'),part('②','정보','I','I 프레임','정보 프레임','Information'),part('③','감독','S','S 프레임','감독 프레임','Supervisory')],['11은 U(비번호), 0은 I(정보), 10은 S(감독)입니다.','기출의 순서를 외우기보다 기능과 프레임을 연결하세요.']),
 custom('함수 포인터로 고른 값을 %x로 출력합니다. 출력값을 쓰세요.',[part('출력','3f')],['pick(n)은 n+2를 반환해 n[2]의 주소를 가리킵니다.','역참조 값은 63입니다.','63 = 3×16+15이므로 소문자 16진수로 3f입니다.'], '#include <stdio.h>\nstruct fns { int* (*fn)(int*); };\nint* pick(int* p) { return p + 2; }\nint main(void) {\n  int n[] = {16, 32, 63};\n  struct fns f = {pick};\n  printf("%x", (unsigned int)*f.fn(n));\n}'),
 custom('ENROLL.STUDENT_NO가 STUDENT.ID를 참조하게 하세요. 제약 이름은 ENROLL_FK입니다. 빈칸을 채우세요.',[part('①','CONSTRAINT'),part('②','FOREIGN'),part('③','STUDENT_NO'),part('④','REFERENCES'),part('⑤','ID')],['이름은 CONSTRAINT ENROLL_FK로 지정합니다.','FOREIGN KEY에는 자식 열 STUDENT_NO가 들어갑니다.','REFERENCES STUDENT (ID)에서 부모 열은 ID입니다.'], 'CREATE TABLE ENROLL (\n  ENROLL_ID INTEGER PRIMARY KEY,\n  STUDENT_NO INTEGER,\n  (①) ENROLL_FK (②) KEY ((③))\n  (④) STUDENT ((⑤))\n);'),
 custom('딕셔너리의 각 튜플에 들어갈 합과 길이를 쓰세요.\n출력: {1: (①, ②), 2: (③, ④), 3: (⑤, ⑥)}',[part('①','8'),part('②','3'),part('③','10'),part('④','2'),part('⑤','0'),part('⑥','0')],['enumerate의 start=1이므로 키는 1,2,3입니다.','[2,2,4]의 합은 8, 길이는 3입니다.','[7,3]의 합은 10, 길이는 2입니다. 빈 리스트의 합과 길이는 모두 0입니다.'], 'data = [[2, 2, 4], [7, 3], []]\nresult = {}\nfor index, lis in enumerate(data, start=1):\n    result[index] = (sum(lis), len(lis))\nprint(result)'),
 custom('자식 메서드에서 자식 필드를 사용합니다. 출력값을 쓰세요.',[part('출력','7')],['부모 생성자 실행 시 Child.v는 아직 기본값 0입니다.','첫 show()는 Child.show()를 호출해 total에 0을 더합니다.','이후 Child.v=7로 초기화됩니다. 자식 생성자의 show()가 7을 더하므로 출력은 7입니다.'], 'class Parent {\n  static int total = 0;\n  Parent() { show(); }\n  void show() { total += 100; }\n}\nclass Child extends Parent {\n  int v = 7;\n  Child() { show(); }\n  @Override void show() { total += v; }\n}\npublic class Main {\n  public static void main(String[] args) {\n    new Child();\n    System.out.println(Parent.total);\n  }\n}'),
 custom('E-R 다이어그램에서 다음 표현의 명칭을 쓰세요.\n① 한 사람이 여러 전화번호를 가질 때의 속성 도형\n② 생년월일에서 계산한 나이를 나타내는 속성 도형\n③ 학번 같은 키 속성 이름에 붙이는 표시', [part('①','이중 타원','이중타원형','double ellipse','double oval'),part('②','점선 타원','점선타원형','dashed ellipse','dashed oval'),part('③','밑줄','underline')],['여러 값을 가질 수 있는 속성은 다중값 속성으로 이중 타원을 씁니다.','다른 속성에서 계산한 유도 속성은 점선 타원입니다.','키 속성의 이름에는 밑줄을 붙입니다.']),
 custom('각 설명에 맞는 용어를 쓰세요.\n① LAN에서 IP 주소에 대응하는 MAC 주소를 찾는 프로토콜\n② 위 프로토콜의 거짓 응답으로 피해자의 게이트웨이 MAC을 공격자 MAC으로 믿게 하는 공격', [part('①','ARP','Address Resolution Protocol','주소 결정 프로토콜','주소 변환 프로토콜'),part('②','ARP 스푸핑','ARP spoofing','ARP poisoning','ARP cache poisoning','ARP 포이즈닝')],['정상 주소 변환 기능은 ARP입니다.','거짓 IP–MAC 대응을 전달하는 공격은 ARP 스푸핑입니다.','프로토콜과 공격 이름을 분리해서 답하세요.']),
 custom('각 설명에 맞는 웹 서비스 용어를 쓰세요.\n① XML 기반 Envelope로 메시지를 교환하는 프로토콜\n② 웹 서비스의 인터페이스·연산·접근 방법을 기술하는 언어\n③ 웹 서비스를 등록하고 검색하는 디렉터리 규격', [part('①','SOAP','Simple Object Access Protocol'),part('②','WSDL','Web Services Description Language'),part('③','UDDI','Universal Description Discovery and Integration','Universal Description, Discovery and Integration')],['메시지 교환은 SOAP, 서비스 설명은 WSDL입니다.','서비스 등록·검색은 UDDI입니다.','XML이라는 공통 특징보다 각각 무엇을 하는지를 확인하세요.'])
]
labels=['2025년 3회 20번','2026년 1회 20번','2026년 1회 5번','2026년 1회 17번','2026년 1회 7번','2025년 3회 15번','2025년 1회 18번','2022년 3회 13번','2021년 3회 2번','2020년 2회 14번']
rates=[69,61,60,60,59,59,58,56,55,None]
items=[]
for i, (title,rules,diagram,pitfall) in enumerate(concepts):
    items.append(dict(rank=i+1,label=labels[i],rate=rates[i],title=title,rules=rules,diagram=diagram,pitfall=pitfall,original=orig[i],application=apps[i]))

template=(ROOT/'study-materials/source/top10.template.html').read_text(encoding='utf-8')
html=template.replace('__DATA__',json.dumps(items,ensure_ascii=False).replace('</','<\\/'))
for output in [ROOT/'study-materials/top10.html', ROOT/'public/top10.html']:
    output.parent.mkdir(exist_ok=True)
    output.write_text(html,encoding='utf-8')
print('Built TOP10: 10 concepts, 10 original/reconstructed questions, 10 applications.')
