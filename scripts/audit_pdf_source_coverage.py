from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import fitz
from PIL import Image

from extract_practical_exams import (
    QUESTION_RE,
    SOLUTION_RE,
    SOLUTION_START_RE,
    answer_from_solution,
    clean_problem,
    clean_solution,
    discover_exams,
    extract_layout_text,
    locate_question_page,
    normalize_answer,
    split_blocks,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "src" / "data" / "exams.json"
ANSWER_OVERRIDE_PATH = ROOT / "src" / "data" / "answer-overrides.json"
REPORT_PATH = ROOT / "reports" / "pdf-source-audit.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_block_is_clean(block: dict[str, object]) -> bool:
    text = str(block.get("text", ""))
    language = block.get("language")
    if re.search(r"\n\s*\n\s*\n", text):
        return False
    if any(label in text for label in ("[요구사항]", "<출력값>", "<SQL문>")):
        return False
    if language in {"C", "Java", "Python"}:
        if any(
            (len(line) - len(line.lstrip(" "))) % 4
            for line in text.splitlines()
        ):
            return False
    if language == "Python":
        try:
            ast.parse(text)
        except SyntaxError:
            return False
    return True


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    answer_overrides = json.loads(ANSWER_OVERRIDE_PATH.read_text(encoding="utf-8"))
    data_by_exam = {exam["id"]: exam for exam in data["exams"]}
    audit_entries: list[dict[str, object]] = []
    errors: list[str] = []
    code_block_count = 0

    for pdf_exam in discover_exams():
        exam = data_by_exam[pdf_exam.exam_id]
        raw_text = extract_layout_text(pdf_exam.path)
        solution_start = SOLUTION_START_RE.search(raw_text)
        if not solution_start:
            errors.append(f"{pdf_exam.exam_id}: 정답 및 해설 구역을 찾지 못했습니다.")
            continue
        problem_text = raw_text[: solution_start.start()]
        solution_text = raw_text[solution_start.end() :]
        problem_blocks = {
            number: (clean_problem(block), page)
            for number, block, page in split_blocks(problem_text, QUESTION_RE)
            if number <= 20
        }
        solution_blocks = {
            number: (clean_solution(block), page)
            for number, block, page in split_blocks(solution_text, SOLUTION_RE)
            if number <= 20
        }
        pdf_document = fitz.open(pdf_exam.path)
        expected_numbers = {question["number"] for question in exam["questions"]}
        if set(problem_blocks) != expected_numbers:
            errors.append(
                f"{pdf_exam.exam_id}: 문제 번호 집합 불일치 "
                f"{sorted(problem_blocks)} != {sorted(expected_numbers)}"
            )

        copied_pdf = ROOT / "public" / exam["sourceFile"].lstrip("/")
        if sha256(pdf_exam.path) != sha256(copied_pdf):
            errors.append(f"{pdf_exam.exam_id}: 공개용 PDF 사본의 해시가 다릅니다.")

        for question in exam["questions"]:
            question_id = question["id"]
            number = question["number"]
            source_prompt, extracted_source_page = problem_blocks[number]
            source_page = locate_question_page(
                pdf_document, number, extracted_source_page
            )
            source_solution, solution_page = solution_blocks[number]
            source_answer, source_explanation = answer_from_solution(source_solution)
            expected_answer = answer_overrides.get(question_id, source_answer)
            accepted_answers = {
                normalize_answer(str(answer))
                for part in question["answerParts"]
                for answer in part.get("acceptedAnswers", [])
            }
            code_blocks = [
                block
                for block in question["promptBlocks"]
                if block.get("type") == "code"
            ]
            code_block_count += len(code_blocks)
            checks = {
                "promptExact": source_prompt == question["prompt"],
                "answerMatchesSourceOrReviewedOverride": (
                    expected_answer == question["answer"]
                ),
                "overriddenSourceAnswerRemainsAccepted": (
                    question_id not in answer_overrides
                    or normalize_answer(source_answer) in accepted_answers
                ),
                "sourceExplanationExact": (
                    source_explanation == question["sourceExplanation"]
                ),
                "sourcePageExact": source_page == question["sourcePage"],
                "solutionPageExact": solution_page == question["solutionPage"],
                "promptBlocksPresent": bool(question["promptBlocks"]),
                "answerPartsPresent": bool(question["answerParts"]),
                "codeFormattingValid": all(
                    code_block_is_clean(block) for block in code_blocks
                ),
            }
            image_path = ROOT / "public" / question["pageImage"].lstrip("/")
            try:
                with Image.open(image_path) as image:
                    image.verify()
                    checks["pageImageReadable"] = image.width > 0 and image.height > 0
            except Exception:
                checks["pageImageReadable"] = False
            if not all(checks.values()):
                errors.append(
                    f"{question_id}: 실패한 검사 "
                    f"{[name for name, passed in checks.items() if not passed]}"
                )
            audit_entries.append(
                {
                    "questionId": question_id,
                    "sourcePage": source_page,
                    "solutionPage": solution_page,
                    "sourceAnswer": source_answer,
                    "reviewedAnswerOverride": answer_overrides.get(question_id),
                    "checks": checks,
                }
            )
        pdf_document.close()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "passed": not errors,
                "examCount": len(data["exams"]),
                "questionCount": len(audit_entries),
                "codeBlockCount": code_block_count,
                "errors": errors,
                "questions": audit_entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if errors:
        print("\n".join(errors))
        raise SystemExit(f"PDF source audit failed: {len(errors)}")
    print(
        f"PDF source audit passed: {len(data['exams'])} exams, "
        f"{len(audit_entries)} questions, {code_block_count} code blocks."
    )


if __name__ == "__main__":
    main()
