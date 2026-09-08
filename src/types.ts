export type PracticeMode = 'practice' | 'exam';

export interface AnswerPart {
  label: string;
  answer: string;
  acceptedAnswers: string[];
}

export type PromptBlock =
  | { type: 'prose'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'code'; text: string; language: PracticalQuestion['language'] }
  | {
      type: 'table';
      caption?: string;
      headers: string[];
      rows: string[][];
      rowHeaderColumn?: boolean;
    }
  | { type: 'choice-grid'; items: string[]; columns: 2 | 3 | 4 }
  | {
      type: 'source-figure';
      src: string;
      alt: string;
      caption?: string;
      sourceSize: [number, number];
      crop: [number, number, number, number];
    }
  | { type: 'preformatted'; text: string };

export interface ExplanationTrace {
  headers: string[];
  rows: string[][];
  caption?: string;
}

export interface ExplanationVerification {
  method: 'executed-and-cross-checked' | 'hand-traced-and-cross-checked' | 'source-cross-checked';
  note: string;
}

export interface FriendlyExplanation {
  status: 'authored' | 'needs-review';
  kind: 'general' | 'code' | 'sql';
  answerSummary: string;
  concept: string;
  rules: string[];
  steps: string[];
  distinctions: string[];
  trace?: ExplanationTrace;
  outputMoment?: string;
  calculation?: string;
  objectFlow?: string[];
  pitfalls: string[];
  takeaway: string;
  verification: ExplanationVerification;
}

export interface PracticalQuestion {
  id: string;
  number: number;
  prompt: string;
  promptBlocks: PromptBlock[];
  answer: string;
  acceptedAnswers: string[];
  answerParts: AnswerPart[];
  sourceExplanation: string;
  language: 'C' | 'Java' | 'Python' | 'SQL' | null;
  sourcePage: number;
  solutionPage: number | null;
  pageImage: string;
  needsReview: boolean;
  reviewReasons: string[];
  explanationStatus: 'authored' | 'needs-review';
  friendlyExplanation?: FriendlyExplanation;
}

export interface PracticalExam {
  id: string;
  year: number;
  session: number;
  title: string;
  sourceFile: string;
  questionCount: number;
  questions: PracticalQuestion[];
}

export interface ExamCollection {
  schemaVersion: number;
  notice: string;
  exams: PracticalExam[];
}

export type AnswerMap = Record<string, string[]>;

export interface PracticeSession {
  id: string;
  examId: string;
  mode: PracticeMode;
  currentIndex: number;
  answers: AnswerMap;
  revealedQuestionIds: string[];
  startedAt: string;
}

export interface QuestionResult {
  questionId: string;
  partCorrect: boolean[];
  correct: boolean;
}

export interface StudyAttempt {
  id: string;
  sessionId: string;
  examId: string;
  mode: PracticeMode;
  completedAt: string;
  answers: AnswerMap;
  results: QuestionResult[];
  correctQuestions: number;
  totalQuestions: number;
  correctFields: number;
  totalFields: number;
}
