import type {
  AnswerMap,
  AnswerPart,
  PracticalQuestion,
  QuestionResult,
} from '../types';

export function normalizeAnswer(value: string): string {
  return value.normalize('NFKC').replace(/\s+/g, '').toLocaleLowerCase('en-US');
}

export function isPartCorrect(value: string, part: AnswerPart): boolean {
  const normalized = normalizeAnswer(value);
  return (
    normalized.length > 0 &&
    part.acceptedAnswers.some((answer) => normalizeAnswer(answer) === normalized)
  );
}

export function gradeQuestion(
  question: PracticalQuestion,
  answerValues: string[] | undefined,
): QuestionResult {
  const values = answerValues ?? [];
  const partCorrect = question.answerParts.map((part, index) =>
    isPartCorrect(values[index] ?? '', part),
  );
  return {
    questionId: question.id,
    partCorrect,
    correct: partCorrect.length > 0 && partCorrect.every(Boolean),
  };
}

export function gradeQuestions(
  questions: PracticalQuestion[],
  answers: AnswerMap,
): QuestionResult[] {
  return questions.map((question) => gradeQuestion(question, answers[question.id]));
}

export function getResultCounts(
  questions: PracticalQuestion[],
  results: QuestionResult[],
): {
  correctQuestions: number;
  totalQuestions: number;
  correctFields: number;
  totalFields: number;
} {
  return {
    correctQuestions: results.filter((result) => result.correct).length,
    totalQuestions: questions.length,
    correctFields: results.reduce(
      (sum, result) => sum + result.partCorrect.filter(Boolean).length,
      0,
    ),
    totalFields: questions.reduce((sum, question) => sum + question.answerParts.length, 0),
  };
}

export function isQuestionAnswered(
  question: PracticalQuestion,
  answers: AnswerMap,
): boolean {
  const values = answers[question.id] ?? [];
  return question.answerParts.every((_, index) => Boolean(values[index]?.trim()));
}
