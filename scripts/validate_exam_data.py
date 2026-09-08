from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "exams.json"
PUBLIC_DATA_PATH = ROOT / "public" / "data" / "exams.json"
EDITORIAL_DIR = ROOT / "src" / "data" / "editorial"
EXECUTION_PATH = ROOT / "src" / "data" / "execution-verification.json"
ANSWER_ALIAS_PATH = ROOT / "src" / "data" / "answer-alias-overrides.json"
ANSWER_OVERRIDE_PATH = ROOT / "src" / "data" / "answer-overrides.json"
STYLES_PATH = ROOT / "src" / "styles.css"
FIGURE_REQUIRED_QUESTION_IDS = {
    "2024-2-20",
    "2024-3-11",
    "2024-3-13",
    "2025-1-14",
    "2025-2-14",
    "2025-3-01",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in flatten_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in flatten_strings(item)]
    return []


def normalized_prose(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalized_answer(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def main() -> None:
    require_errors: list[str] = []
    require(
        PUBLIC_DATA_PATH.exists(),
        "브라우저가 읽을 public/data/exams.json이 없습니다.",
        require_errors,
    )
    if require_errors:
        print("\n".join(f"- {error}" for error in require_errors))
        raise SystemExit("공개 데이터 파일 검사 실패")
    require(
        DATA_PATH.read_bytes() == PUBLIC_DATA_PATH.read_bytes(),
        "원본 데이터와 브라우저용 데이터가 서로 다릅니다.",
        require_errors,
    )
    if require_errors:
        print("\n".join(f"- {error}" for error in require_errors))
        raise SystemExit("데이터 동기화 검사 실패")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    answer_aliases = json.loads(ANSWER_ALIAS_PATH.read_text(encoding="utf-8"))
    answer_overrides = json.loads(ANSWER_OVERRIDE_PATH.read_text(encoding="utf-8"))
    execution_results = json.loads(EXECUTION_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    styles = STYLES_PATH.read_text(encoding="utf-8")
    mobile_marker = "@media (max-width: 760px)"
    mobile_styles = styles[styles.find(mobile_marker) :] if mobile_marker in styles else ""
    require(bool(mobile_styles), "모바일 반응형 구간이 없습니다.", errors)
    require(
        ".mobile-pane-tabs" in mobile_styles and "display: grid" in mobile_styles,
        "모바일 문제·해설 탭 표시 규칙이 없습니다.",
        errors,
    )
    require(
        ".problem-pane.mobile-active" in mobile_styles
        and ".explanation-pane.mobile-active" in mobile_styles
        and "display: block" in mobile_styles,
        "모바일 활성 탭의 패널 표시 규칙이 없습니다.",
        errors,
    )
    exams = data.get("exams", [])
    require(len(exams) == 7, "2024~2026년 시험 데이터는 7회분이어야 합니다.", errors)
    require(
        sum(exam.get("questionCount", 0) for exam in exams) == 138,
        "전체 문항 수는 138개여야 합니다.",
        errors,
    )

    editorial_ids: set[str] = set()
    for editorial_path in sorted(EDITORIAL_DIR.glob("*.json")):
        editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
        require(
            isinstance(editorial, dict),
            f"{editorial_path.name}: 편집 해설 파일은 객체여야 합니다.",
            errors,
        )
        if not isinstance(editorial, dict):
            continue
        overlap = editorial_ids & editorial.keys()
        require(
            not overlap,
            f"{editorial_path.name}: 중복 편집 해설 ID {sorted(overlap)}",
            errors,
        )
        editorial_ids.update(editorial)

    seen_exam_ids: set[str] = set()
    seen_question_ids: set[str] = set()
    total_questions = 0
    code_questions = 0
    review_questions = 0
    table_question_ids: set[str] = set()
    choice_grid_question_ids: set[str] = set()
    source_figure_question_ids: set[str] = set()

    for exam in exams:
        exam_id = exam.get("id")
        require(exam_id not in seen_exam_ids, f"중복 시험 ID: {exam_id}", errors)
        seen_exam_ids.add(exam_id)
        questions = exam.get("questions", [])
        require(
            exam.get("questionCount") == len(questions),
            f"{exam_id}: questionCount가 실제 문항 수와 다릅니다.",
            errors,
        )
        require(
            (ROOT / "public" / str(exam.get("sourceFile", "")).lstrip("/")).exists(),
            f"{exam_id}: 원본 PDF 사본이 없습니다.",
            errors,
        )

        seen_numbers: set[int] = set()
        for question in questions:
            total_questions += 1
            question_id = question.get("id")
            number = question.get("number")
            require(
                question_id not in seen_question_ids,
                f"중복 문항 ID: {question_id}",
                errors,
            )
            seen_question_ids.add(question_id)
            require(number not in seen_numbers, f"{exam_id}: 중복 문항 번호 {number}", errors)
            seen_numbers.add(number)
            require(bool(question.get("prompt")), f"{question_id}: 문제 본문이 없습니다.", errors)
            prompt_blocks = question.get("promptBlocks") or []
            require(bool(prompt_blocks), f"{question_id}: 구조화된 문제 본문이 없습니다.", errors)
            for block_index, block in enumerate(prompt_blocks, start=1):
                block_type = block.get("type")
                require(
                    block_type
                    in {
                        "prose",
                        "list",
                        "code",
                        "table",
                        "choice-grid",
                        "source-figure",
                        "preformatted",
                    },
                    f"{question_id}: {block_index}번 문제 블록 유형이 잘못되었습니다.",
                    errors,
                )
                if block_type == "prose":
                    text = block.get("text", "")
                    require(
                        "\n" not in text,
                        f"{question_id}: 일반 문장이 강제 줄바꿈을 포함합니다.",
                        errors,
                    )
                    require(
                        not any(
                            broken in text
                            for broken in (
                                "준 수하시오",
                                "출 력",
                                "프 로토콜",
                                "네트 워크",
                                "의한미 다",
                            )
                        ),
                        f"{question_id}: 복원되지 않은 한글 분리 문자가 있습니다.",
                        errors,
                    )
                if block_type == "code":
                    code_text = str(block.get("text", ""))
                    code_language = block.get("language")
                    require(
                        not re.search(r"\n\s*\n\s*\n", code_text),
                        f"{question_id}: 코드 블록에 불필요한 연속 빈 줄이 있습니다.",
                        errors,
                    )
                    require(
                        not any(
                            label in code_text
                            for label in ("[요구사항]", "<출력값>", "<SQL문>")
                        ),
                        f"{question_id}: 일반 문장이나 레이블이 코드 블록에 섞여 있습니다.",
                        errors,
                    )
                    if code_language in {"C", "Java", "Python"}:
                        for line_number, line in enumerate(
                            code_text.splitlines(), start=1
                        ):
                            indent = len(line) - len(line.lstrip(" "))
                            require(
                                indent % 4 == 0,
                                f"{question_id}: 코드 {line_number}행 들여쓰기가 4칸 단위가 아닙니다.",
                                errors,
                            )
                    if code_language == "Python":
                        try:
                            ast.parse(code_text)
                        except SyntaxError as error:
                            errors.append(
                                f"{question_id}: Python 코드 구조가 잘못되었습니다 "
                                f"({error.msg}, {error.lineno}행)."
                            )
                if block_type == "table":
                    table_question_ids.add(question_id)
                    headers = block.get("headers") or []
                    rows = block.get("rows") or []
                    require(bool(headers), f"{question_id}: 표 머리글이 없습니다.", errors)
                    for row_index, row in enumerate(rows, start=1):
                        require(
                            len(row) == len(headers),
                            f"{question_id}: 표 {row_index}행의 셀 개수가 머리글과 다릅니다.",
                            errors,
                        )
                if block_type == "choice-grid":
                    choice_grid_question_ids.add(question_id)
                    require(
                        bool(block.get("items")),
                        f"{question_id}: 보기 항목이 없습니다.",
                        errors,
                    )
                    require(
                        block.get("columns") in {2, 3, 4},
                        f"{question_id}: 보기 열 개수가 잘못되었습니다.",
                        errors,
                    )
                if block_type == "source-figure":
                    source_figure_question_ids.add(question_id)
                    src = str(block.get("src", ""))
                    source_size = block.get("sourceSize") or []
                    crop = block.get("crop") or []
                    require(
                        bool(block.get("alt")),
                        f"{question_id}: 원본 그림의 대체 설명이 없습니다.",
                        errors,
                    )
                    require(
                        (ROOT / "public" / src.lstrip("/")).exists(),
                        f"{question_id}: 문제 본문 그림 파일이 없습니다.",
                        errors,
                    )
                    require(
                        len(source_size) == 2
                        and all(isinstance(value, (int, float)) and value > 0 for value in source_size),
                        f"{question_id}: 원본 그림 크기가 잘못되었습니다.",
                        errors,
                    )
                    require(
                        len(crop) == 4
                        and all(isinstance(value, (int, float)) and value >= 0 for value in crop)
                        and crop[2] > 0
                        and crop[3] > 0,
                        f"{question_id}: 문제 그림 자르기 영역이 잘못되었습니다.",
                        errors,
                    )
                    if len(source_size) == 2 and len(crop) == 4:
                        require(
                            crop[0] + crop[2] <= source_size[0]
                            and crop[1] + crop[3] <= source_size[1],
                            f"{question_id}: 문제 그림 영역이 원본 페이지를 벗어났습니다.",
                            errors,
                        )
                require(
                    block_type != "preformatted",
                    f"{question_id}: 띄어쓰기 기반 임시 표가 남아 있습니다.",
                    errors,
                )
            if question.get("language") in {"C", "Java", "Python"}:
                require(
                    prompt_blocks[0].get("type") == "prose",
                    f"{question_id}: 코드 문제 안내문이 코드 블록과 분리되지 않았습니다.",
                    errors,
                )
                require(
                    any(block.get("type") == "code" for block in prompt_blocks),
                    f"{question_id}: 코드 문제에 코드 블록이 없습니다.",
                    errors,
                )
            require(
                (ROOT / "public" / str(question.get("pageImage", "")).lstrip("/")).exists(),
                f"{question_id}: 원본 페이지 이미지가 없습니다.",
                errors,
            )

            if question.get("needsReview"):
                review_questions += 1
                require(
                    bool(question.get("reviewReasons")),
                    f"{question_id}: 검토 필요 사유가 없습니다.",
                    errors,
                )
            require(bool(question.get("answer")), f"{question_id}: 정답이 없습니다.", errors)
            if question.get("answer"):
                require(
                    bool(question.get("acceptedAnswers")),
                    f"{question_id}: 자동 채점용 정답이 없습니다.",
                    errors,
                )
                answer_parts = question.get("answerParts") or []
                require(bool(answer_parts), f"{question_id}: 답안 입력칸이 없습니다.", errors)
                for part_index, part in enumerate(answer_parts, start=1):
                    require(
                        bool(part.get("acceptedAnswers")),
                        f"{question_id}: {part_index}번 답칸의 자동 채점용 정답이 없습니다.",
                        errors,
                    )

            if question_id == "2025-1-01":
                session_aliases = set(
                    (question.get("answerParts") or [{}])[0].get("acceptedAnswers")
                    or []
                )
                require(
                    {
                        "세션 하이재킹(Session Hijacking)",
                        "세션 하이재킹",
                        "Session Hijacking",
                    }
                    <= session_aliases,
                    "2025-1-01: 한글명·영문명 독립 정답이 누락되었습니다.",
                    errors,
                )
            if question_id == "2025-1-06":
                result_aliases = set(
                    (question.get("answerParts") or [{}])[0].get("acceptedAnswers")
                    or []
                )
                require(
                    {"이순신 1000", "이순신, 1000"} <= result_aliases,
                    "2025-1-06: 열 이름을 생략한 결과값 정답이 누락되었습니다.",
                    errors,
                )

            friendly = question.get("friendlyExplanation") or {}
            require(
                question_id in editorial_ids,
                f"{question_id}: 분리 편집 해설 파일에 문항이 없습니다.",
                errors,
            )
            require(bool(friendly), f"{question_id}: 초보자용 해설이 없습니다.", errors)
            for key in (
                "status",
                "kind",
                "answerSummary",
                "concept",
                "rules",
                "steps",
                "pitfalls",
                "takeaway",
                "verification",
            ):
                require(
                    bool(friendly.get(key)),
                    f"{question_id}: 초보자용 해설의 {key} 항목이 없습니다.",
                    errors,
                )
            require(
                friendly.get("status") == question.get("explanationStatus"),
                f"{question_id}: 해설 상태가 편집 데이터와 다릅니다.",
                errors,
            )
            require(
                friendly.get("status") in {"authored", "needs-review"},
                f"{question_id}: 알 수 없는 해설 상태입니다.",
                errors,
            )
            if friendly.get("status") == "needs-review":
                require(
                    question.get("needsReview") is True,
                    f"{question_id}: 검토 필요 해설인데 문항 표시가 없습니다.",
                    errors,
                )
            require(
                not ({"summary", "valueFlow", "pitfall"} & friendly.keys()),
                f"{question_id}: 폐기된 PDF 파생 해설 필드가 남아 있습니다.",
                errors,
            )

            source_explanation = normalized_prose(question.get("sourceExplanation", ""))
            for authored_text in flatten_strings(friendly):
                authored_sentence = normalized_prose(authored_text)
                if len(authored_sentence) < 45:
                    continue
                require(
                    authored_sentence not in source_explanation,
                    f"{question_id}: 새 해설 문장이 PDF 원문 해설과 그대로 겹칩니다.",
                    errors,
                )

            if question.get("language"):
                code_questions += 1
                trace = friendly.get("trace") or {}
                headers = trace.get("headers") or []
                rows = trace.get("rows") or []
                require(bool(headers), f"{question_id}: 실행 추적표 머리글이 없습니다.", errors)
                require(bool(rows), f"{question_id}: 실행 추적표 행이 없습니다.", errors)
                for row_index, row in enumerate(rows, start=1):
                    require(
                        len(row) == len(headers),
                        f"{question_id}: 추적표 {row_index}행의 열 수가 다릅니다.",
                        errors,
                    )
                require(
                    bool(friendly.get("outputMoment")),
                    f"{question_id}: 결과가 정해지는 순간 설명이 없습니다.",
                    errors,
                )
                require(
                    bool(friendly.get("calculation")),
                    f"{question_id}: 마지막 계산 설명이 없습니다.",
                    errors,
                )
                verification_method = (friendly.get("verification") or {}).get("method")
                execution_passed = bool(
                    (execution_results.get(question_id) or {}).get("passed")
                )
                require(
                    (verification_method == "executed-and-cross-checked")
                    == execution_passed,
                    f"{question_id}: 실행 검증 표기가 실제 실행 기록과 다릅니다.",
                    errors,
                )

    require(
        len(table_question_ids) == 22,
        f"구조화 표 문항은 22개여야 하지만 {len(table_question_ids)}개입니다.",
        errors,
    )
    require(
        len(choice_grid_question_ids) == 12,
        f"구조화 보기 문항은 12개여야 하지만 {len(choice_grid_question_ids)}개입니다.",
        errors,
    )
    require(
        source_figure_question_ids == FIGURE_REQUIRED_QUESTION_IDS,
        "원본 그림이 필요한 문항의 그림 등록이 누락되었거나 예상과 다릅니다: "
        f"{sorted(source_figure_question_ids)}",
        errors,
    )

    questions_by_id = {
        question["id"]: question
        for exam in exams
        for question in exam.get("questions", [])
    }
    for question_id, expected_answer in answer_overrides.items():
        question = questions_by_id.get(question_id)
        require(question is not None, f"{question_id}: 정답 교정 문항 ID가 없습니다.", errors)
        if question is None:
            continue
        require(
            question.get("answer") == expected_answer,
            f"{question_id}: 교정된 대표 정답이 생성 데이터에 반영되지 않았습니다.",
            errors,
        )
    for question_id, aliases_by_label in answer_aliases.items():
        question = questions_by_id.get(question_id)
        require(question is not None, f"{question_id}: 동의어 문항 ID가 없습니다.", errors)
        if question is None:
            continue
        parts_by_label = {
            part.get("label"): part for part in question.get("answerParts", [])
        }
        for label, aliases in aliases_by_label.items():
            part = parts_by_label.get(label)
            require(
                part is not None,
                f"{question_id}: 동의어 답칸 {label}이 없습니다.",
                errors,
            )
            if part is None:
                continue
            accepted = {
                normalized_answer(value)
                for value in (part.get("acceptedAnswers") or [])
            }
            require(
                {normalized_answer(value) for value in aliases} <= accepted,
                f"{question_id} {label}: 검토된 동의어가 생성 데이터에서 누락되었습니다.",
                errors,
            )

    question_2025_1_02 = next(
        question
        for exam in exams
        for question in exam.get("questions", [])
        if question.get("id") == "2025-1-02"
    )
    integrity_table = next(
        block
        for block in question_2025_1_02.get("promptBlocks", [])
        if block.get("type") == "table"
    )
    require(
        integrity_table.get("headers")
        == [
            "구분",
            "( ① ) 무결성 제약 조건",
            "( ② ) 무결성 제약 조건",
            "( ③ ) 무결성 제약 조건",
        ],
        "2025-1-02: 무결성 표의 열 구조가 원본과 다릅니다.",
        errors,
    )
    require(
        len(integrity_table.get("rows") or []) == 3,
        "2025-1-02: 무결성 표의 데이터 행이 누락되었습니다.",
        errors,
    )
    question_2025_2_07 = next(
        question
        for exam in exams
        for question in exam.get("questions", [])
        if question.get("id") == "2025-2-07"
    )
    result_table = next(
        block
        for block in question_2025_2_07.get("promptBlocks", [])
        if block.get("type") == "table" and block.get("caption") == "<결과>"
    )
    require(
        result_table.get("headers") == ["①"],
        "2025-2-07: 결과 표 머리글은 빈칸 ①이어야 합니다.",
        errors,
    )
    require(
        result_table.get("rows") == [["②"], ["③"], ["④"], ["⑤"]],
        "2025-2-07: 결과 표 데이터 행은 ②~⑤의 4칸이어야 합니다.",
        errors,
    )
    normalized_question = next(
        question
        for exam in exams
        for question in exam.get("questions", [])
        if question.get("id") == "2024-1-03"
    )
    require(
        normalized_question.get("sourcePage") == 3,
        "2024-1-03: 실제 PDF 문제 페이지가 잘못 연결되었습니다.",
        errors,
    )

    if errors:
        print("\n".join(f"- {error}" for error in errors))
        raise SystemExit(f"데이터 검사 실패: {len(errors)}개 문제")

    print(
        f"데이터 검사 통과: {len(exams)}회, {total_questions}문항, "
        f"코드·SQL 풀이 {code_questions}개, 검토 필요 {review_questions}개, "
        f"분리 편집 해설 {len(editorial_ids)}개, 실행 검증 "
        f"{sum(bool(result.get('passed')) for result in execution_results.values())}개"
    )


if __name__ == "__main__":
    main()
