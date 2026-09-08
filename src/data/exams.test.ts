import { describe, expect, it } from 'vitest';
import type { ExamCollection, PromptBlock } from '../types';
import { isPartCorrect } from '../utils/grading';
import examData from './exams.json';

const exams = (examData as unknown as ExamCollection).exams;
const questions = exams.flatMap((exam) => exam.questions);

function tableBlocks(questionId: string) {
  const question = questions.find((item) => item.id === questionId);
  if (!question) throw new Error(`${questionId} 문항을 찾지 못했습니다.`);
  return question.promptBlocks.filter(
    (block): block is Extract<PromptBlock, { type: 'table' }> => block.type === 'table',
  );
}

describe('구조화된 문제 표', () => {
  it('띄어쓰기 기반 임시 표가 남아 있지 않다', () => {
    expect(
      questions.flatMap((question) => question.promptBlocks)
        .filter((block) => block.type === 'preformatted'),
    ).toHaveLength(0);
  });

  it('모든 표의 행마다 머리글과 같은 수의 셀이 있다', () => {
    const tables = questions.flatMap((question) => question.promptBlocks)
      .filter(
        (block): block is Extract<PromptBlock, { type: 'table' }> => block.type === 'table',
      );

    expect(tables).toHaveLength(32);
    for (const table of tables) {
      for (const row of table.rows) expect(row).toHaveLength(table.headers.length);
    }
  });

  it('2025년 1회 2번의 4열 3행 표를 보존한다', () => {
    const [table] = tableBlocks('2025-1-02');
    expect(table.headers).toEqual([
      '구분',
      '( ① ) 무결성 제약 조건',
      '( ② ) 무결성 제약 조건',
      '( ③ ) 무결성 제약 조건',
    ]);
    expect(table.rows).toEqual([
      ['제약 대상', '속성', '튜플', '속성, 튜플'],
      ['NULL 값', '', '기본키', '외래키'],
      ['릴레이션 내 제약 조건 개수', '속성의 개수와 동일', '1개', '0~여러 개'],
    ]);
  });

  it('자동 추출에서 누락됐던 정규화 전후 표도 등록한다', () => {
    expect(tableBlocks('2024-1-03')).toHaveLength(3);
    expect(tableBlocks('2025-2-07')).toHaveLength(2);
  });

  it('2025년 2회 7번 결과 표의 ① 머리글과 ②~⑤ 데이터 행을 보존한다', () => {
    const tables = tableBlocks('2025-2-07');
    const resultTable = tables.find((table) => table.caption === '<결과>');

    expect(resultTable?.headers).toEqual(['①']);
    expect(resultTable?.rows).toEqual([['②'], ['③'], ['④'], ['⑤']]);
  });

  it('결과 표는 열 이름을 생략하고 결과값만 적어도 정답으로 인정한다', () => {
    const question = questions.find((item) => item.id === '2025-1-06');
    expect(question?.answerParts[0].acceptedAnswers).toEqual(
      expect.arrayContaining(['이순신 1000', '이순신, 1000']),
    );
    expect(isPartCorrect('이순신,1000', question!.answerParts[0])).toBe(true);

    const oneColumnResult = questions.find((item) => item.id === '2024-1-12');
    expect(oneColumnResult?.answerParts[0].acceptedAnswers).toContain('a, b');
  });
});

describe('용어형 답안 동의어', () => {
  function answerPart(questionId: string, partIndex = 0) {
    const question = questions.find((item) => item.id === questionId);
    if (!question) throw new Error(`${questionId} 문항을 찾지 못했습니다.`);
    return question.answerParts[partIndex];
  }

  it('2025년 3회 1번은 package와 패키지 다이어그램을 모두 인정한다', () => {
    const part = answerPart('2025-3-01');

    expect(part.acceptedAnswers).toEqual(
      expect.arrayContaining(['패키지', 'Package', 'Package Diagram', '패키지 다이어그램']),
    );
    expect(isPartCorrect('package', part)).toBe(true);
    expect(isPartCorrect('PACKAGE DIAGRAM', part)).toBe(true);
    expect(isPartCorrect('diagram', part)).toBe(false);
  });

  it('비슷한 디자인 패턴·보안·DB·테스트 용어도 검토된 동의어를 인정한다', () => {
    expect(isPartCorrect('어댑터 패턴', answerPart('2025-1-13'))).toBe(true);
    expect(isPartCorrect('scareware', answerPart('2025-1-08'))).toBe(true);
    expect(isPartCorrect('condition coverage', answerPart('2025-3-03'))).toBe(true);
    expect(isPartCorrect('tuple', answerPart('2025-3-15', 0))).toBe(true);
    expect(isPartCorrect('역할 기반 접근 통제', answerPart('2025-3-13', 1))).toBe(true);
  });

  it('색인과 같은 영문 용어의 통상적인 한글 표기를 인정한다', () => {
    expect(isPartCorrect('인덱스', answerPart('2025-2-01'))).toBe(true);
    expect(isPartCorrect('인덱스 파일', answerPart('2025-2-01'))).toBe(true);
    expect(isPartCorrect('엔터티', answerPart('2024-3-16'))).toBe(true);
    expect(isPartCorrect('행동 패턴', answerPart('2024-3-08'))).toBe(true);
    expect(isPartCorrect('에이잭스', answerPart('2025-2-11'))).toBe(true);
    expect(isPartCorrect('소프트 링크', answerPart('2026-1-14'))).toBe(true);
  });
});

describe('검토된 대표 정답 교정', () => {
  it('2025년 2회 10번은 2 그리고 3을 대표 답으로 표시하고 두 평가 결과를 인정한다', () => {
    const question = questions.find((item) => item.id === '2025-2-10');
    const part = question?.answerParts[0];

    expect(question?.answer).toBe('2 그리고 3');
    expect(part?.answer).toBe('2 그리고 3');
    expect(part?.acceptedAnswers).toEqual(
      expect.arrayContaining(['2 그리고 3', '3 그리고 2']),
    );
    expect(isPartCorrect('2 그리고 3', part!)).toBe(true);
    expect(isPartCorrect('3 그리고 2', part!)).toBe(true);
    expect(question?.explanationStatus).toBe('needs-review');
  });
});

describe('원본 그림과 코드 보존', () => {
  const figureQuestionIds = [
    '2024-2-20',
    '2024-3-11',
    '2024-3-13',
    '2025-1-14',
    '2025-2-14',
    '2025-3-01',
  ];

  it('그림·순서도를 읽어야 하는 모든 문항에 원본 그림을 표시한다', () => {
    const actualIds = questions
      .filter((question) => question.promptBlocks.some((block) => block.type === 'source-figure'))
      .map((question) => question.id)
      .sort();

    expect(actualIds).toEqual([...figureQuestionIds].sort());
  });

  it('2024년 3회 11번에 URL 구성 그림을 원본 크기로 표시한다', () => {
    const question = questions.find((item) => item.id === '2024-3-11');
    const figure = question?.promptBlocks.find(
      (block): block is Extract<PromptBlock, { type: 'source-figure' }> => (
        block.type === 'source-figure'
      ),
    );

    expect(figure?.src).toBe('/question-images/2024-3/2024-3-11-url-components.png');
    expect(figure?.sourceSize).toEqual([550, 101]);
    expect(figure?.crop).toEqual([0, 0, 550, 101]);
  });

  it('2025년 1회 14번 코드를 들여쓰기된 코드 블록으로 보존한다', () => {
    const question = questions.find((item) => item.id === '2025-1-14');
    const code = question?.promptBlocks.find(
      (block): block is Extract<PromptBlock, { type: 'code' }> => block.type === 'code',
    );

    expect(code?.language).toBe('C');
    expect(code?.text).toContain('    while (a < m || b[a] < x) {');
    expect(code?.text).toContain('        if (b[a] < 0)');
    expect(code?.text).toContain('            b[a] = -b[a];');
    expect(question?.answerParts).toHaveLength(7);
    expect(question?.answerParts[6].label).toContain('문장 커버리지 경로');
  });

  it('2024년 3회 2번 Python 코드의 함수·반복문 들여쓰기를 보존한다', () => {
    const question = questions.find((item) => item.id === '2024-3-02');
    const code = question?.promptBlocks.find(
      (block): block is Extract<PromptBlock, { type: 'code' }> => block.type === 'code',
    );

    expect(code?.text).toBe([
      'def func(lst):',
      '    for i in range(len(lst) // 2):',
      '        lst[i], lst[-i-1] = lst[-i-1], lst[i]',
      'lst = [1,2,3,4,5,6]',
      'func(lst)',
      'print(sum(lst[::2]) - sum(lst[1::2]))',
    ].join('\n'));
  });

  it('모든 코드 블록은 정규화된 들여쓰기와 문장 분리를 유지한다', () => {
    const codeBlocks = questions.flatMap((question) => question.promptBlocks)
      .filter((block): block is Extract<PromptBlock, { type: 'code' }> => block.type === 'code');

    expect(codeBlocks).toHaveLength(70);
    for (const code of codeBlocks) {
      expect(code.text).not.toMatch(/\n\s*\n\s*\n/);
      expect(code.text).not.toMatch(/\[요구사항\]|<출력값>|<SQL문>/);
      if (code.language === 'C' || code.language === 'Java' || code.language === 'Python') {
        for (const line of code.text.split('\n')) {
          const indent = line.match(/^ */)?.[0].length ?? 0;
          expect(indent % 4).toBe(0);
        }
      }
    }
  });
});
