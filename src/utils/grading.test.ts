import { describe, expect, it } from 'vitest';
import type { AnswerPart, PracticalQuestion } from '../types';
import {
  gradeQuestion,
  isPartCorrect,
  normalizeAnswer,
} from './grading';

const answerPart: AnswerPart = {
  label: '답',
  answer: 'Open Shortest Path First',
  acceptedAnswers: ['OSPF', 'Open Shortest Path First'],
};

describe('답안 자동 채점', () => {
  it('공백과 영문 대소문자는 무시한다', () => {
    expect(normalizeAnswer(' Open Shortest PATH First ')).toBe(
      normalizeAnswer('openshortestpathfirst'),
    );
    expect(isPartCorrect('o s p f', answerPart)).toBe(true);
  });

  it('한국어의 다른 표현과 오탈자는 자동으로 정답 처리하지 않는다', () => {
    const koreanPart: AnswerPart = {
      label: '답',
      answer: '제3정규형',
      acceptedAnswers: ['제3정규형'],
    };
    expect(isPartCorrect('제 3 정규형', koreanPart)).toBe(true);
    expect(isPartCorrect('삼차 정규형', koreanPart)).toBe(false);
  });

  it('괄호로 함께 적힌 한글명과 영문명은 각각 정답으로 인정한다', () => {
    const sessionHijackingPart: AnswerPart = {
      label: '답',
      answer: '세션 하이재킹(Session Hijacking)',
      acceptedAnswers: [
        '세션 하이재킹(Session Hijacking)',
        '세션 하이재킹',
        'Session Hijacking',
      ],
    };

    expect(isPartCorrect('세션 하이재킹', sessionHijackingPart)).toBe(true);
    expect(isPartCorrect('session hijacking', sessionHijackingPart)).toBe(true);
    expect(isPartCorrect('하이재킹', sessionHijackingPart)).toBe(false);
  });

  it('검토된 핵심 용어의 한글명·영문명·정식 명칭을 인정한다', () => {
    const packagePart: AnswerPart = {
      label: '답',
      answer: '패키지',
      acceptedAnswers: ['패키지', 'Package', 'Package Diagram', '패키지 다이어그램'],
    };

    expect(isPartCorrect('package', packagePart)).toBe(true);
    expect(isPartCorrect('PACKAGE DIAGRAM', packagePart)).toBe(true);
    expect(isPartCorrect('패키지 다이어그램', packagePart)).toBe(true);
    expect(isPartCorrect('diagram', packagePart)).toBe(false);
  });

  it('복수 답칸은 모든 칸이 맞아야 문항 정답이다', () => {
    const question = {
      id: 'test',
      answerParts: [
        { label: '①', answer: 'Bridge', acceptedAnswers: ['Bridge'] },
        { label: '②', answer: 'Observer', acceptedAnswers: ['Observer'] },
      ],
    } as PracticalQuestion;
    expect(gradeQuestion(question, ['bridge', ' Observer ']).correct).toBe(true);
    expect(gradeQuestion(question, ['bridge', 'Adapter']).correct).toBe(false);
  });

  it('빈 답안은 제출할 수 있지만 오답으로 채점한다', () => {
    const question = {
      id: 'blank-answer',
      answerParts: [answerPart],
    } as PracticalQuestion;
    const result = gradeQuestion(question, ['']);
    expect(result.correct).toBe(false);
    expect(result.partCorrect).toEqual([false]);
  });
});
