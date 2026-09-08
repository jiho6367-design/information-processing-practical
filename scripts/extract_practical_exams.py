from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "exams.json"
PUBLIC_DATA_PATH = ROOT / "public" / "data" / "exams.json"
EDITORIAL_DIR = ROOT / "src" / "data" / "editorial"
PROMPT_STRUCTURE_PATH = ROOT / "src" / "data" / "prompt-structure-overrides.json"
ANSWER_ALIAS_PATH = ROOT / "src" / "data" / "answer-alias-overrides.json"
ANSWER_OVERRIDE_PATH = ROOT / "src" / "data" / "answer-overrides.json"
SOURCE_DIR = ROOT / "public" / "sources"
PAGE_IMAGE_DIR = ROOT / "public" / "page-images"
TARGET_YEARS = {2024, 2025, 2026}

PDF_NAME_RE = re.compile(
    r"^(?P<year>20\d{2})년\s*(?P<session>\d)회\s*정보처리기사\s*실기\s*기출문제\.pdf$"
)
QUESTION_RE = re.compile(r"(?m)^[ \t\f]*문제\s*(?P<number>\d{1,2})\s+")
SOLUTION_RE = re.compile(r"(?m)^[ \t\f]*\[문제\s*(?P<number>\d{1,2})\]\s*$")
SOLUTION_START_RE = re.compile(r"기출문제\s*정답\s*및\s*해설")
ANSWER_CUT_RE = re.compile(r"(?m)^\s*답\s*(?::|：|$)")
FOOTER_RE = re.compile(r"^\s*-\s*\d+\s*-\s*$")
SOURCE_NOTICE_RE = re.compile(r"^\s*이 문제는 .*제공하는 .*기출문제입니다\.\s*$")


@dataclass(frozen=True)
class PdfExam:
    path: Path
    year: int
    session: int

    @property
    def exam_id(self) -> str:
        return f"{self.year}-{self.session}"

    @property
    def title(self) -> str:
        return f"{self.year}년 {self.session}회"


def discover_exams() -> list[PdfExam]:
    exams: list[PdfExam] = []
    for path in sorted(ROOT.glob("*.pdf")):
        match = PDF_NAME_RE.match(path.name)
        if not match:
            continue
        year = int(match["year"])
        if year not in TARGET_YEARS:
            continue
        exams.append(PdfExam(path, year, int(match["session"])))
    return exams


def extract_layout_text(path: Path) -> str:
    completed = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")


def strip_noise(text: str) -> str:
    kept: list[str] = []
    skip_exercise_note = False
    for raw_line in text.replace("\x0c", "\n").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if FOOTER_RE.match(stripped) or SOURCE_NOTICE_RE.match(stripped):
            continue
        if stripped == "연 습 란":
            skip_exercise_note = True
            continue
        if skip_exercise_note and stripped.startswith("※ 다음 여백은 연습란"):
            skip_exercise_note = False
            continue
        if stripped in {"기출문제", "기출문제 정답 및 해설"}:
            continue
        kept.append(line)

    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n[ \t]+\n", "\n\n", cleaned)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    return cleaned.strip()


def split_blocks(
    text: str, pattern: re.Pattern[str]
) -> list[tuple[int, str, int]]:
    matches = list(pattern.finditer(text))
    blocks: list[tuple[int, str, int]] = []
    for index, match in enumerate(matches):
        number = int(match["number"])
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        page = text[: match.start()].count("\x0c") + 1
        block = text[match.end() : end]
        blocks.append((number, block, page))
    return blocks


def clean_problem(block: str) -> str:
    answer_cut = ANSWER_CUT_RE.search(block)
    if answer_cut:
        block = block[: answer_cut.start()]
    block = re.split(
        r"(?m)^\s*※?\s*\[?문제\s*\d+\]?(?:와|과).*복원",
        block,
        maxsplit=1,
    )[0]
    return strip_noise(block)


def clean_solution(block: str) -> str:
    return strip_noise(block)


def answer_from_solution(solution: str) -> tuple[str, str]:
    parts = re.split(r"(?m)^\s*\[(?:해설|풀이)\]\s*$", solution, maxsplit=1)
    answer_section = parts[0].strip()
    explanation = parts[1].strip() if len(parts) > 1 else ""
    answer_section = re.split(
        r"(?m)^\s*(?:\[답안\s*작성\s*시\s*주의\s*사항\]|※\s*답안\s*작성\s*시\s*주의\s*사항)",
        answer_section,
        maxsplit=1,
    )[0].strip()

    answer_lines: list[str] = []
    for line in answer_section.splitlines():
        stripped = line.strip()
        if not stripped:
            if answer_lines:
                break
            continue
        if stripped.startswith("※ 다음 중 하나를 쓰면 됩니다"):
            continue
        if stripped.startswith("※ ") and not answer_lines:
            continue
        if FOOTER_RE.match(stripped):
            continue
        answer_lines.append(stripped)
        if len(answer_lines) >= 12:
            break

    answer = "\n".join(answer_lines).strip()
    return answer, explanation


def parenthetical_term_aliases(value: str) -> list[str]:
    """Split a written term such as '한글명(English Name)' into safe aliases."""
    if "\n" in value:
        return []

    match = re.fullmatch(r"\s*(.+?)\s*[\(（]\s*([^()（）]+?)\s*[\)）]\s*", value)
    if not match:
        return []

    outside, inside = (item.strip() for item in match.groups())
    # Do not turn code-like answers such as func(3) into partial answers.
    if not all(re.search(r"[A-Za-z가-힣]", item) for item in (outside, inside)):
        return []
    return [outside, inside]


def tabular_result_aliases(value: str) -> list[str]:
    """Allow SQL/result-table data rows without requiring the printed headers."""
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) < 2:
        return []

    header_cells = [
        cell.strip() for cell in re.split(r"\s{2,}|\t+", lines[0]) if cell.strip()
    ]
    if not header_cells or not all(
        re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cell) for cell in header_cells
    ):
        return []

    data_rows = [
        [cell.strip() for cell in re.split(r"\s{2,}|\t+", line) if cell.strip()]
        for line in lines[1:]
    ]
    if not data_rows or any(len(row) != len(header_cells) for row in data_rows):
        return []

    data_cells = [cell for row in data_rows for cell in row]
    all_cells = header_cells + data_cells
    return [
        "\n".join(" ".join(row) for row in data_rows),
        " ".join(data_cells),
        ", ".join(data_cells),
        ",".join(data_cells),
        ", ".join(all_cells),
    ]


def accepted_answers(answer: str) -> list[str]:
    if not answer:
        return []
    answers = [answer]
    single_line = " ".join(answer.splitlines()).strip()
    if single_line != answer:
        answers.append(single_line)

    # "OSPF, Open Shortest Path First protocol"처럼 하나만 쓰면 되는 동의어.
    if (
        "\n" not in answer
        and "," in answer
        and not re.search(r"[①②③④⑤㉠㉡㉢㉣]", answer)
        and len(answer.split(",")) <= 6
    ):
        alternatives = [item.strip() for item in answer.split(",") if item.strip()]
        looks_like_sequence = all(
            re.fullmatch(r"[-+]?\d+(?:\.\d+)?|[A-Z]?", item, re.IGNORECASE)
            for item in alternatives
        )
        if (
            not looks_like_sequence
            and all(1 <= len(item.split()) <= 8 for item in alternatives)
        ):
            answers.extend(alternatives)

    # PDF answers often write the Korean term and English term together. Each name is
    # independently correct, while the complete notation remains accepted as well.
    for candidate in list(answers):
        answers.extend(parenthetical_term_aliases(candidate))
    answers.extend(tabular_result_aliases(answer))

    deduplicated: list[str] = []
    seen: set[str] = set()
    for item in answers:
        key = normalize_answer(item)
        if key and key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


def split_answer_parts(answer: str) -> list[dict[str, object]]:
    if not answer:
        return []
    marker_re = re.compile(r"([①②③④⑤⑥⑦⑧⑨⑩])\s*")
    matches = list(marker_re.finditer(answer))
    if len(matches) >= 2 and matches[0].start() <= 2:
        parts: list[dict[str, object]] = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
            value = answer[match.end() : end].strip(" \n,")
            if value:
                parts.append(
                    {
                        "label": match.group(1),
                        "answer": value,
                        "acceptedAnswers": accepted_answers(value),
                    }
                )
        if parts:
            return parts
    return [
        {
            "label": "답",
            "answer": answer,
            "acceptedAnswers": accepted_answers(answer),
        }
    ]


def answer_parts_for_question(
    question_id: str, answer: str
) -> list[dict[str, object]]:
    parts = split_answer_parts(answer)
    if question_id == "2025-1-14":
        parts.append(
            {
                "label": "문장 커버리지 경로 (① → ② 다음)",
                "answer": "③ → ④ → ⑤ → ② → ⑥",
                "acceptedAnswers": [
                    "③ → ④ → ⑤ → ② → ⑥",
                    "③, ④, ⑤, ②, ⑥",
                    "③ ④ ⑤ ② ⑥",
                ],
            }
        )
    return parts


def apply_answer_aliases(
    question_id: str,
    parts: list[dict[str, object]],
    alias_overrides: dict[str, dict[str, list[str]]],
) -> list[dict[str, object]]:
    """Merge reviewed term aliases without making every answer fuzzily match."""
    question_aliases = alias_overrides.get(question_id, {})
    for part in parts:
        label = str(part.get("label", ""))
        accepted = list(part.get("acceptedAnswers") or [])
        seen = {normalize_answer(str(item)) for item in accepted}
        for alias in question_aliases.get(label, []):
            key = normalize_answer(alias)
            if key and key not in seen:
                seen.add(key)
                accepted.append(alias)
        part["acceptedAnswers"] = accepted
    return parts


def normalize_answer(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).casefold()


PROSE_FIXES = {
    "준 수하시오": "준수하시오",
    "준수 하시오": "준수하시오",
    "준수하 시오": "준수하시오",
    "마시 오": "마시오",
    "쓰 시오": "쓰시오",
    "작성 하시오": "작성하시오",
    "결 함": "결함",
    "조 인": "조인",
    "의 미한다": "의미한다",
    "에 서": "에서",
    "구 조적": "구조적",
    "접 근할": "접근할",
    "프로그 램": "프로그램",
    "일반 적으로": "일반적으로",
    "설 치한다": "설치한다",
    "의도적으 로": "의도적으로",
    "요구사 항": "요구사항",
    "논리 적으로": "논리적으로",
    "결합 도이다": "결합도이다",
    "결합도이 다": "결합도이다",
    "출 력": "출력",
    "결 과": "결과",
    "모 든": "모든",
    "집중 적으로": "집중적으로",
    "수행되도 록": "수행되도록",
    "수행되 도록": "수행되도록",
    "서 식": "서식",
    "규 정": "규정",
    "골 라": "골라",
    "변 환": "변환",
    "밖 에": "밖에",
    "프 로토콜": "프로토콜",
    "프로로톨": "프로토콜",
    "순 차": "순차",
    "활용하 여": "활용하여",
    "네트 워크": "네트워크",
    "못 하게": "못하게",
    "시 스템": "시스템",
    "의 존": "의존",
    "구현되었 다": "구현되었다",
    "사 용자": "사용자",
    "기 능": "기능",
    "정 보보호": "정보보호",
    "악 성": "악성",
    "만드 는": "만드는",
    "깊 이": "깊이",
    "대체한다 는": "대체한다는",
    "하 위": "하위",
    "과정에 서": "과정에서",
    "파일 을": "파일을",
    "아 닌": "아닌",
    "다양 한": "다양한",
    "사용하 여": "사용하여",
    "위 해": "위해",
    "관리 를": "관리를",
    "불 균형": "불균형",
    "주국 의": "주국의",
    "의한미 다": "의미한다",
    "패턴 으로": "패턴으로",
    "5 점": "5점",
    "마련 한": "마련한",
    "저하 될": "저하될",
    "테이블 에": "테이블에",
    "출발지 에서": "출발지에서",
    "못한 다": "못한다",
    "프로토콜에 대한 관한": "프로토콜에 관한",
    "먼 저": "먼저",
    "시간 이": "시간이",
    "오버헤드 가": "오버헤드가",
    "세부 적인": "세부적인",
    "복잡도 를": "복잡도를",
    "오류 를": "오류를",
    "부 문에서": "부문에서",
    "열 을": "열을",
    "요구사 항": "요구사항",
    "출 력": "출력",
    "입 력": "입력",
    "기 능": "기능",
    "구 조적": "구조적",
    "논리 적": "논리적",
    "물리 적": "물리적",
    "정 보": "정보",
    "악 성": "악성",
    "네트 워크": "네트워크",
    "프로세 스": "프로세스",
    "데이터베 이스": "데이터베이스",
    "조 인": "조인",
    "의 미": "의미",
    "하 시오": "하시오",
    "쓰 시오": "쓰시오",
    "나타내 시오": "나타내시오",
    "이 다.": "이다.",
    "됩 니다": "됩니다",
}


def reflow_prose(value: str) -> str:
    text = re.sub(r"\s*\n\s*", " ", value.strip())
    text = re.sub(r"[ \t]{2,}", " ", text)
    for broken, repaired in PROSE_FIXES.items():
        text = text.replace(broken, repaired)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    return text.strip()


def normalize_braced_code_indentation(value: str) -> str:
    lines = value.splitlines()
    normalized: list[str] = []
    brace_level = 0
    pending_single_indent: int | None = None
    case_level: int | None = None

    for line in lines:
        if not line.strip():
            normalized.append("")
            continue

        stripped = line.strip()
        marker_match = re.match(r"^([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)$", stripped)
        marker = marker_match.group(1) if marker_match else ""
        syntax = marker_match.group(2) if marker_match else stripped
        clean = re.sub(
            r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
            "",
            syntax,
        )
        leading_closes = len(clean) - len(clean.lstrip("}"))
        base_indent = max(0, brace_level - leading_closes)
        is_case = bool(re.match(r"^(?:case\b.*:|default\s*:)", syntax))

        indent_level = base_indent
        if case_level is not None and base_indent == case_level and not is_case:
            indent_level += 1
        if pending_single_indent is not None:
            indent_level = max(indent_level, pending_single_indent)
            pending_single_indent = None

        rendered = f"{marker} {syntax}" if marker else syntax
        normalized.append(" " * (indent_level * 4) + rendered)

        if is_case:
            case_level = base_indent
        elif case_level is not None and base_indent < case_level:
            case_level = None

        opens = clean.count("{")
        closes = clean.count("}")
        brace_level = max(0, brace_level + opens - closes)

        control_without_braces = (
            not syntax.endswith(";")
            and "{" not in clean
            and bool(
                re.match(
                    r"^(?:if\s*\(.*\)|else|for\s*\(.*\)|while\s*\(.*\)|do)$",
                    syntax,
                )
            )
        )
        if control_without_braces:
            pending_single_indent = indent_level + 1

    return "\n".join(normalized).strip()


def compact_code_blank_lines(value: str) -> str:
    compacted: list[str] = []
    previous_blank = False
    for line in value.splitlines():
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        compacted.append(line.rstrip())
        previous_blank = is_blank
    return "\n".join(compacted).strip()


def normalize_code_indentation(value: str, language: str | None) -> str:
    """Map PDF horizontal offsets to stable four-space indentation levels."""
    lines = value.splitlines()
    indents = sorted(
        {
            len(line) - len(line.lstrip(" "))
            for line in lines
            if line.strip()
        }
    )
    if not indents:
        return value.strip()

    # Hand-authored overrides already use canonical four-space indentation.
    if all(indent % 4 == 0 for indent in indents):
        return compact_code_blank_lines("\n".join(line.rstrip() for line in lines))

    # PDF extraction shifts later top-level lines by roughly five spaces.
    # Treat 0-5 as one level and group nearby offsets from the same column.
    band_starts: list[int] = []
    for indent in (value for value in indents if value > 5):
        if not band_starts or indent > band_starts[-1] + 2:
            band_starts.append(indent)

    def logical_level(indent: int) -> int:
        if indent <= 5:
            return 0
        for index, start in enumerate(band_starts):
            if indent <= start + 2:
                return index + 1
        return len(band_starts)

    normalized: list[str] = []
    for line in lines:
        if not line.strip():
            normalized.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        normalized.append(" " * (logical_level(indent) * 4) + line.lstrip())
    result = "\n".join(normalized).strip()
    if language in {"C", "Java"}:
        result = normalize_braced_code_indentation(result)
    return compact_code_blank_lines(result)


def looks_like_code(block: str, language: str | None) -> bool:
    if not language:
        return False
    signals = (
        "#include",
        "public class",
        "class ",
        "interface ",
        "enum ",
        "def ",
        "for ",
        "while ",
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "CREATE ",
        "ALTER ",
        "printf(",
        "System.out.",
        "print(",
    )
    signal_count = sum(signal.casefold() in block.casefold() for signal in signals)
    punctuation_count = sum(block.count(token) for token in ("{", "}", ";", "->"))
    return signal_count >= 1 and (punctuation_count >= 2 or "\n" in block)


def apply_prompt_structure_overrides(
    question_id: str, blocks: list[dict[str, object]]
) -> list[dict[str, object]]:
    if not PROMPT_STRUCTURE_PATH.exists():
        return blocks
    overrides = json.loads(PROMPT_STRUCTURE_PATH.read_text(encoding="utf-8"))
    replacements = overrides.get(question_id)
    if replacements is None:
        return blocks
    if isinstance(replacements, dict) and "full" in replacements:
        return replacements["full"]

    replacement_index = 0
    structured: list[dict[str, object]] = []
    for block in blocks:
        if block.get("type") != "preformatted":
            structured.append(block)
            continue
        if replacement_index >= len(replacements):
            raise ValueError(f"{question_id}: missing preformatted replacement")
        structured.extend(replacements[replacement_index])
        replacement_index += 1
    if replacement_index != len(replacements):
        raise ValueError(f"{question_id}: unused preformatted replacement")
    return structured


def prompt_blocks(
    prompt: str, language: str | None, question_id: str
) -> list[dict[str, object]]:
    raw_blocks = [
        raw_block.strip()
        for raw_block in re.split(r"\n\s*\n", prompt)
        if raw_block.strip()
    ]
    if language in {"C", "Java", "Python"} and raw_blocks:
        instruction_match = re.match(
            r"(?s)^(.*?(?:\(\s*5\s*점\s*\)|\(5점\)))\s*(.*)$",
            prompt,
        )
        blocks: list[dict[str, object]] = []
        if instruction_match:
            blocks.append(
                {"type": "prose", "text": reflow_prose(instruction_match.group(1))}
            )
            code_text = textwrap.dedent(instruction_match.group(2)).strip()
        else:
            code_text = textwrap.dedent(prompt).strip()
        code_text = code_text.replace('printf("%d n",', 'printf("%d\\n",')
        code_text = normalize_code_indentation(code_text, language)
        if code_text:
            blocks.append(
                {"type": "code", "language": language, "text": code_text}
            )
        return apply_prompt_structure_overrides(question_id, blocks)

    blocks: list[dict[str, object]] = []
    for block in raw_blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        bullet_marker_re = re.compile(r"[ㆍ•]")
        bullet_start_count = sum(
            bool(re.match(r"^\s*(?:[ㆍ•]|[-*])\s*", line)) for line in lines
        )
        if bullet_start_count >= 2:
            items: list[str] = []
            current = ""
            for line in lines:
                stripped = line.strip()
                fragments = [
                    fragment.strip()
                    for fragment in bullet_marker_re.split(stripped)
                ]
                if re.match(r"^[ㆍ•]", stripped) and current:
                    items.append(reflow_prose(current))
                    current = ""
                if len(fragments) > 1:
                    if fragments[0]:
                        current = f"{current} {fragments[0]}".strip()
                    for fragment in fragments[1:]:
                        if not fragment:
                            continue
                        if current:
                            items.append(reflow_prose(current))
                        current = fragment
                else:
                    current = f"{current} {stripped}".strip()
            if current:
                items.append(reflow_prose(current))
            blocks.append({"type": "list", "items": items})
            continue
        table_like = (
            len(lines) >= 2
            and sum(bool(re.search(r"\S\s{2,}\S", line)) for line in lines)
            >= max(2, len(lines) // 2)
        )
        if looks_like_code(block, language):
            blocks.append(
                {
                    "type": "code",
                    "language": language,
                    "text": "\n".join(line.strip() for line in lines),
                }
            )
        elif table_like:
            blocks.append(
                {
                    "type": "preformatted",
                    "text": "\n".join(line.strip() for line in lines),
                }
            )
        else:
            blocks.append({"type": "prose", "text": reflow_prose(block)})
    return apply_prompt_structure_overrides(question_id, blocks)


def load_editorial_explanations() -> dict[str, dict[str, object]]:
    editorial: dict[str, dict[str, object]] = {}
    if not EDITORIAL_DIR.exists():
        return editorial
    for path in sorted(EDITORIAL_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.name} must contain an object")
        overlap = editorial.keys() & data.keys()
        if overlap:
            raise ValueError(f"Duplicate editorial IDs: {', '.join(sorted(overlap))}")
        editorial.update(data)
    return editorial


def load_answer_aliases() -> dict[str, dict[str, list[str]]]:
    if not ANSWER_ALIAS_PATH.exists():
        return {}
    data = json.loads(ANSWER_ALIAS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{ANSWER_ALIAS_PATH.name} must contain an object")
    return data


def load_answer_overrides() -> dict[str, str]:
    if not ANSWER_OVERRIDE_PATH.exists():
        return {}
    data = json.loads(ANSWER_OVERRIDE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(question_id, str) and isinstance(answer, str)
        for question_id, answer in data.items()
    ):
        raise ValueError(f"{ANSWER_OVERRIDE_PATH.name} must map question IDs to answers")
    return data


def detect_language(prompt: str) -> str | None:
    if re.search(r"Python(?:으로|\s)|파이썬|^\s*def\s+\w+\s*\(", prompt, re.IGNORECASE | re.MULTILINE):
        return "Python"
    if re.search(
        r"(?:JAVA|Java)(?:로|\s)|public\s+class|System\.out\.",
        prompt,
    ):
        return "Java"
    if re.search(r"\bC\s*언어\b|#include\s*<", prompt):
        return "C"
    if re.search(r"\bSQL\b|<SQL문>|SELECT\s+|CREATE\s+TABLE", prompt, re.IGNORECASE):
        return "SQL"
    return None


def concept_for(language: str, text: str) -> tuple[str, str]:
    lowered = text.casefold()
    if language == "C":
        if "*" in text and ("포인터" in text or "->" in text or "&" in text):
            return (
                "포인터와 메모리 참조",
                "별표(*)가 곱셈인지 포인터인지, 주소를 따라간 뒤 어느 값이 바뀌는지를 구분하세요.",
            )
        if "재귀" in text or re.search(r"\breturn\s+\w+\s*\(", text):
            return (
                "재귀 호출과 반환 순서",
                "재귀 함수는 내려가는 순서와 값을 돌려주며 올라오는 순서가 반대라는 점을 놓치기 쉽습니다.",
            )
        if "<<" in text or ">>" in text or any(op in text for op in ("&", "|", "^")):
            return (
                "비트 연산과 조건식",
                "시프트 연산을 하기 전에 조건식이 참인지 거짓인지부터 확정하세요.",
            )
        return (
            "배열·반복문 실행 추적",
            "반복문 조건을 검사하는 시점과 증감식이 실행되는 시점을 한 칸씩 기록하세요.",
        )
    if language == "Java":
        if any(word in lowered for word in ("extends", "override", "상속", "다형성")):
            return (
                "상속과 동적 메서드 호출",
                "변수의 선언 타입보다 실제로 만들어진 객체 타입이 재정의 메서드를 결정한다는 점이 핵심입니다.",
            )
        if "static" in lowered:
            return (
                "static 공유값과 객체 상태",
                "클래스가 공유하는 static 값과 객체마다 따로 가지는 인스턴스 값을 분리해서 적으세요.",
            )
        return (
            "객체 생성과 메서드 실행 순서",
            "생성자, 메서드 호출, 필드 변경을 실제 실행 순서대로 한 줄씩 따라가세요.",
        )
    if language == "Python":
        if any(word in lowered for word in ("slice", "슬라이", "리스트", "copy", "[:]")):
            return (
                "리스트 참조와 복사",
                "새 리스트의 틀만 복사된 것인지 내부 객체까지 복사된 것인지 확인해야 합니다.",
            )
        if "재귀" in text:
            return (
                "재귀 호출과 반환값",
                "종료 조건을 먼저 찾고, 가장 안쪽 호출부터 값을 되돌려 계산하세요.",
            )
        return (
            "파이썬 표현식과 반복 흐름",
            "각 줄이 새 값을 만드는지 기존 객체를 바꾸는지 구분해서 추적하세요.",
        )
    if "join" in lowered or "조인" in text:
        return (
            "JOIN 조건과 결과 행",
            "두 테이블에서 연결 조건이 맞는 행부터 만든 뒤 WHERE 조건으로 걸러내세요.",
        )
    if "group by" in lowered or "having" in lowered or "그룹" in text:
        return (
            "그룹화와 집계",
            "WHERE는 그룹화 전 행을, HAVING은 그룹화 후 결과를 거른다는 순서를 기억하세요.",
        )
    return (
        "SQL 실행 순서와 결과 테이블",
        "FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY 순서로 중간 결과를 확인하세요.",
    )


def execution_steps(explanation: str, answer: str, language: str) -> list[str]:
    if not explanation:
        return [
            f"{language} 문장을 위에서 아래로 읽으며 변수 또는 결과 행의 변화를 기록합니다.",
            f"마지막 출력 또는 조회 결과를 문제의 답안 형식에 맞춰 쓰면 {answer or '검토 필요'}입니다.",
        ]

    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n|(?=[❶❷❸❹❺❻❼❽❾❿])", explanation)
    ]
    useful = [
        paragraph
        for paragraph in paragraphs
        if len(paragraph) >= 12
        and not FOOTER_RE.match(paragraph)
        and re.search(r"[가-힣]", paragraph)
        and not re.match(
            r"^[❶❷❸❹❺❻❼❽❾❿⓫⓬⓭⓮⓯⓰⓱⓲⓳⓴●\s]*(?:#include|class\s|public\s|def\s|int\s+main)",
            paragraph,
        )
    ]
    return useful[:8] or [
        re.sub(r"\s+", " ", explanation).strip()[:900],
    ]


def value_flow(explanation: str, answer: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in explanation.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" ㆍ•")
        if not line:
            continue
        if (
            "=" in line
            or "결과" in line
            or "출력" in line
            or "저장" in line
            or "반환" in line
            or "행" in line
        ) and re.search(r"[가-힣]|\d+\s*[+\-*/]\s*\d+", line):
            candidates.append(line)
    if answer:
        candidates.append(f"최종 답: {answer}")
    return candidates[:12]


def make_friendly_explanation(
    language: str, prompt: str, answer: str, source_explanation: str
) -> dict[str, object]:
    concept, pitfall = concept_for(language, f"{prompt}\n{source_explanation}")
    return {
        "concept": concept,
        "summary": (
            f"정답은 `{answer}`입니다. "
            f"처음부터 한꺼번에 계산하지 말고 {concept}을 중심으로 순서대로 따라가면 됩니다."
            if answer
            else "복원 자료에서 정답을 확실하게 확인할 수 없어 풀이를 보류했습니다."
        ),
        "steps": execution_steps(source_explanation, answer, language),
        "valueFlow": value_flow(source_explanation, answer),
        "pitfall": pitfall,
    }


def render_page_image(pdf: fitz.Document, exam_id: str, page_number: int) -> str:
    relative = Path("page-images") / exam_id / f"page-{page_number}.webp"
    destination = ROOT / "public" / relative
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        page = pdf.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45), alpha=False)
        image = pixmap.pil_image()
        image.save(destination, "WEBP", quality=84, method=6)
    return "/" + relative.as_posix()


def locate_question_page(
    pdf: fitz.Document, question_number: int, fallback_page: int
) -> int:
    marker = re.compile(rf"(?m)^\s*문제\s*{question_number}\s+")
    for page_index, pdf_page in enumerate(pdf):
        if marker.search(pdf_page.get_text("text")):
            return page_index + 1
    return fallback_page


def extract_exam(
    exam: PdfExam,
    editorial: dict[str, dict[str, object]],
    answer_aliases: dict[str, dict[str, list[str]]],
    answer_overrides: dict[str, str],
) -> dict[str, object]:
    raw_text = extract_layout_text(exam.path)
    solution_start = SOLUTION_START_RE.search(raw_text)
    if solution_start:
        problem_text = raw_text[: solution_start.start()]
        solution_text = raw_text[solution_start.end() :]
    else:
        problem_text = raw_text
        solution_text = ""

    question_blocks = split_blocks(problem_text, QUESTION_RE)
    solution_blocks = {
        number: (clean_solution(block), page)
        for number, block, page in split_blocks(solution_text, SOLUTION_RE)
    }

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    source_destination = SOURCE_DIR / exam.path.name
    if not source_destination.exists() or source_destination.stat().st_size != exam.path.stat().st_size:
        shutil.copy2(exam.path, source_destination)

    pdf_document = fitz.open(exam.path)
    questions: list[dict[str, object]] = []
    for number, raw_block, page in question_blocks:
        prompt = clean_problem(raw_block)
        if not prompt or number > 20:
            continue

        solution, solution_page = solution_blocks.get(number, ("", 0))
        answer, source_explanation = answer_from_solution(solution)
        language = detect_language(prompt)
        question_id = f"{exam.exam_id}-{number:02d}"
        answer = answer_overrides.get(question_id, answer)
        authored_explanation = editorial.get(question_id)
        review_reasons: list[str] = []
        if not solution:
            review_reasons.append("PDF 정답·해설에서 해당 문항을 찾지 못했습니다.")
        if not answer:
            review_reasons.append("자동 채점용 정답을 확정하지 못했습니다.")
        if "재구성하기에 어려움" in prompt or "복원하지 못" in prompt:
            review_reasons.append("복원 자료에 문항 내용이 충분하지 않습니다.")
        if not authored_explanation:
            review_reasons.append("새로 작성한 초보자용 해설이 아직 없습니다.")
        elif authored_explanation.get("status") == "needs-review":
            review_reasons.append(
                "언어 표준 또는 원문 조건만으로 결과를 하나로 확정할 수 없어 검토가 필요합니다."
            )

        source_page = locate_question_page(pdf_document, number, page)
        page_image = render_page_image(pdf_document, exam.exam_id, source_page)
        answer_parts = apply_answer_aliases(
            question_id,
            answer_parts_for_question(question_id, answer),
            answer_aliases,
        )
        question_accepted_answers = accepted_answers(answer)
        if len(answer_parts) == 1:
            question_accepted_answers = list(answer_parts[0]["acceptedAnswers"])
        question: dict[str, object] = {
            "id": question_id,
            "number": number,
            "prompt": prompt,
            "promptBlocks": prompt_blocks(prompt, language, question_id),
            "answer": answer,
            "acceptedAnswers": question_accepted_answers,
            "answerParts": answer_parts,
            "sourceExplanation": source_explanation,
            "language": language,
            "sourcePage": source_page,
            "solutionPage": solution_page or None,
            "pageImage": page_image,
            "needsReview": bool(review_reasons),
            "reviewReasons": review_reasons,
            "explanationStatus": (
                authored_explanation.get("status")
                if authored_explanation
                else "needs-review"
            ),
        }
        if authored_explanation:
            question["friendlyExplanation"] = authored_explanation
        questions.append(question)

    pdf_document.close()
    questions.sort(key=lambda item: int(item["number"]))
    return {
        "id": exam.exam_id,
        "year": exam.year,
        "session": exam.session,
        "title": exam.title,
        "sourceFile": f"/sources/{exam.path.name}",
        "questionCount": len(questions),
        "questions": questions,
    }


def main() -> None:
    exams = discover_exams()
    if len(exams) != 7:
        raise SystemExit(f"2024~2026년 PDF 7개가 필요하지만 {len(exams)}개를 찾았습니다.")

    editorial = load_editorial_explanations()
    answer_aliases = load_answer_aliases()
    answer_overrides = load_answer_overrides()
    data = {
        "schemaVersion": 1,
        "notice": (
            "수험생 기억을 토대로 복원된 개인 학습용 자료입니다. "
            "실제 시험과 내용·배점이 다를 수 있습니다."
        ),
        "exams": [
            extract_exam(exam, editorial, answer_aliases, answer_overrides)
            for exam in exams
        ],
    }
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    for data_path in (DATA_PATH, PUBLIC_DATA_PATH):
        data_path.parent.mkdir(parents=True, exist_ok=True)
        data_path.write_text(serialized, encoding="utf-8")

    question_count = sum(int(exam["questionCount"]) for exam in data["exams"])
    authored_count = sum(
        1
        for exam in data["exams"]
        for question in exam["questions"]
        if question.get("friendlyExplanation")
    )
    review_count = sum(
        1
        for exam in data["exams"]
        for question in exam["questions"]
        if question["needsReview"]
    )
    print(
        f"Generated {len(exams)} exams, {question_count} questions, "
        f"{authored_count} authored explanations, {review_count} review items."
    )


if __name__ == "__main__":
    main()
