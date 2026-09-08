import { useEffect, useMemo, useState } from 'react';
import type {
  ExamCollection,
  PracticalExam,
  PracticalQuestion,
  PracticeMode,
  PracticeSession,
  QuestionResult,
  StudyAttempt,
} from './types';
import {
  getResultCounts,
  gradeQuestion,
  gradeQuestions,
  isQuestionAnswered,
} from './utils/grading';
import {
  clearSession,
  loadAttempts,
  loadSession,
  saveAttempt,
  saveSession,
} from './utils/storage';

let data: ExamCollection = {
  schemaVersion: 1,
  notice: '',
  exams: [],
};
let examById = new Map<string, PracticalExam>();

type Screen = 'home' | 'quiz' | 'result' | 'review';
type IconProps = {
  size?: number;
  className?: string;
  'aria-label'?: string;
  'aria-hidden'?: 'true';
};

function SymbolIcon({
  symbol,
  size = 18,
  className = '',
  ...accessibility
}: IconProps & { symbol: string }) {
  return (
    <span
      className={`ui-icon ${className}`}
      style={{ width: size, height: size, fontSize: Math.max(13, size - 2) }}
      {...accessibility}
    >
      {symbol}
    </span>
  );
}

const ArrowLeft = (props: IconProps) => <SymbolIcon symbol="←" {...props} />;
const ArrowRight = (props: IconProps) => <SymbolIcon symbol="→" {...props} />;
const BookOpenCheck = (props: IconProps) => <SymbolIcon symbol="✓" {...props} />;
const CheckCircle2 = (props: IconProps) => <SymbolIcon symbol="✓" {...props} />;
const ChevronRight = (props: IconProps) => <SymbolIcon symbol="›" {...props} />;
const Clock3 = (props: IconProps) => <SymbolIcon symbol="◷" {...props} />;
const Code2 = (props: IconProps) => <SymbolIcon symbol="</>" {...props} />;
const FileText = (props: IconProps) => <SymbolIcon symbol="▤" {...props} />;
const Home = (props: IconProps) => <SymbolIcon symbol="⌂" {...props} />;
const RotateCcw = (props: IconProps) => <SymbolIcon symbol="↻" {...props} />;
const Save = (props: IconProps) => <SymbolIcon symbol="●" {...props} />;
const TriangleAlert = (props: IconProps) => <SymbolIcon symbol="!" {...props} />;
const XCircle = (props: IconProps) => <SymbolIcon symbol="×" {...props} />;

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function makeSession(examId: string, mode: PracticeMode): PracticeSession {
  return {
    id: createId('session'),
    examId,
    mode,
    currentIndex: 0,
    answers: {},
    revealedQuestionIds: [],
    startedAt: new Date().toISOString(),
  };
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ko-KR', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function percent(correct: number, total: number): number {
  return total === 0 ? 0 : Math.round((correct / total) * 100);
}

function HomePage({
  attempts,
  resumableSession,
  onResume,
  onStart,
  onReview,
}: {
  attempts: StudyAttempt[];
  resumableSession: PracticeSession | null;
  onResume: () => void;
  onStart: (examId: string, mode: PracticeMode) => void;
  onReview: (attempt: StudyAttempt) => void;
}) {
  const sortedExams = [...data.exams].sort(
    (a, b) => b.year - a.year || b.session - a.session,
  );
  const latestByExam = new Map<string, StudyAttempt>();
  for (const attempt of attempts) {
    if (!latestByExam.has(attempt.examId)) latestByExam.set(attempt.examId, attempt);
  }

  return (
    <main className="home-page">
      <section className="hero">
        <div>
          <span className="eyebrow">개인용 실기 학습실</span>
          <h1>답을 외우기보다<br />코드가 흐르는 길을 따라가요.</h1>
          <p>
            2024~2026년 복원 문제 7회분을 연습하고, 코드 문제는 변수의 변화를
            한 단계씩 확인할 수 있습니다.
          </p>
        </div>
        <div className="hero-stat" aria-label="등록 자료 요약">
          <strong>{data.exams.reduce((sum, exam) => sum + exam.questionCount, 0)}</strong>
          <span>등록 문항</span>
          <strong>
            {data.exams.reduce(
              (sum, exam) => sum + exam.questions.filter((question) => question.language).length,
              0,
            )}
          </strong>
          <span>코드·SQL 풀이</span>
        </div>
      </section>

      <div className="notice-card">
        <TriangleAlert size={20} aria-hidden="true" />
        <span>{data.notice}</span>
      </div>

      {resumableSession && examById.has(resumableSession.examId) && (
        <section className="resume-card">
          <div>
            <span className="eyebrow">저장된 학습</span>
            <h2>{examById.get(resumableSession.examId)?.title} 이어 풀기</h2>
            <p>
              {resumableSession.mode === 'practice' ? '연습 모드' : '시험 모드'} ·{' '}
              {resumableSession.currentIndex + 1}번 문항부터 이어집니다.
            </p>
          </div>
          <button className="button primary" onClick={onResume}>
            이어서 풀기 <ChevronRight size={18} />
          </button>
        </section>
      )}

      <section className="section-heading">
        <div>
          <span className="eyebrow">회차 선택</span>
          <h2>어떤 문제부터 풀까요?</h2>
        </div>
        <p>연습은 즉시 해설, 시험은 마지막에 한꺼번에 채점합니다.</p>
      </section>

      <section className="exam-grid">
        {sortedExams.map((exam) => {
          const latest = latestByExam.get(exam.id);
          return (
            <article className="exam-card" key={exam.id}>
              <div className="exam-card-top">
                <span className="year-chip">{exam.year}</span>
                <span>{exam.questionCount}문항</span>
              </div>
              <h3>{exam.title}</h3>
              <p>
                코드·SQL 풀이{' '}
                {exam.questions.filter((question) => question.language).length}개
              </p>
              {latest ? (
                <button className="last-score" onClick={() => onReview(latest)}>
                  최근 결과 {latest.correctQuestions}/{latest.totalQuestions}
                  <span>오답 보기</span>
                </button>
              ) : (
                <div className="last-score empty">아직 학습 기록이 없습니다.</div>
              )}
              <div className="exam-actions">
                <button className="button secondary" onClick={() => onStart(exam.id, 'practice')}>
                  <BookOpenCheck size={18} /> 연습
                </button>
                <button className="button primary" onClick={() => onStart(exam.id, 'exam')}>
                  <Clock3 size={18} /> 시험
                </button>
              </div>
            </article>
          );
        })}
      </section>

      {attempts.length > 0 && (
        <section className="history-section">
          <div className="section-heading compact">
            <div>
              <span className="eyebrow">학습 기록</span>
              <h2>최근 결과</h2>
            </div>
          </div>
          <div className="history-list">
            {attempts.slice(0, 8).map((attempt) => {
              const exam = examById.get(attempt.examId);
              return (
                <button key={attempt.id} onClick={() => onReview(attempt)}>
                  <span>
                    <strong>{exam?.title}</strong>
                    <small>
                      {attempt.mode === 'practice' ? '연습' : '시험'} ·{' '}
                      {formatDate(attempt.completedAt)}
                    </small>
                  </span>
                  <strong>
                    {attempt.correctQuestions}/{attempt.totalQuestions}
                  </strong>
                </button>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}

function QuestionNavigation({
  exam,
  session,
  currentIndex,
  results,
  onMove,
}: {
  exam: PracticalExam;
  session: PracticeSession;
  currentIndex: number;
  results: Map<string, QuestionResult>;
  onMove: (index: number) => void;
}) {
  return (
    <aside className="question-nav" aria-label="문항 바로가기">
      <div>
        <span className="eyebrow">문항 목록</span>
        <strong>
          {exam.questions.filter((question) => isQuestionAnswered(question, session.answers)).length}
          /{exam.questionCount} 답변
        </strong>
      </div>
      <div className="question-dots">
        {exam.questions.map((question, index) => {
          const answered = isQuestionAnswered(question, session.answers);
          const result = results.get(question.id);
          const state = result ? (result.correct ? 'correct' : 'wrong') : answered ? 'answered' : '';
          return (
            <button
              key={question.id}
              className={`${index === currentIndex ? 'current' : ''} ${state}`}
              onClick={() => onMove(index)}
              aria-label={`${question.number}번 ${answered ? '답변함' : '미답변'}`}
            >
              {question.number}
            </button>
          );
        })}
      </div>
      <div className="nav-legend">
        <span><i className="answered" />답변</span>
        <span><i className="current" />현재</span>
      </div>
    </aside>
  );
}

function SourcePage({ question, exam }: { question: PracticalQuestion; exam: PracticalExam }) {
  return (
    <details className="source-details">
      <summary>
        <FileText size={18} /> 원본 PDF {question.sourcePage}쪽 확인
      </summary>
      <div className="source-page">
        <img
          src={question.pageImage}
          alt={`${exam.title} ${question.number}번 원본 페이지`}
          loading="lazy"
        />
        <a
          href={`${exam.sourceFile}#page=${question.sourcePage}`}
          target="_blank"
          rel="noreferrer"
        >
          PDF에서 크게 열기
        </a>
      </div>
    </details>
  );
}

function StructuredPrompt({ question }: { question: PracticalQuestion }) {
  return (
    <section className="question-prompt" aria-label="문제 본문">
      {question.promptBlocks.map((block, index) => {
        const key = `${question.id}-prompt-${index}`;
        if (block.type === 'prose') return <p key={key}>{block.text}</p>;
        if (block.type === 'list') {
          return (
            <ul key={key}>
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{item}</li>
              ))}
            </ul>
          );
        }
        if (block.type === 'code') {
          return (
            <pre className="prompt-code" key={key}>
              <code>{block.text}</code>
            </pre>
          );
        }
        if (block.type === 'table') {
          return (
            <div className="prompt-table-wrap" key={key}>
              <table className="prompt-data-table">
                {block.caption ? <caption>{block.caption}</caption> : null}
                <thead>
                  <tr>
                    {block.headers.map((header, headerIndex) => (
                      <th key={`${key}-header-${headerIndex}`} scope="col">{header}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rowIndex) => (
                    <tr key={`${key}-row-${rowIndex}`}>
                      {row.map((cell, cellIndex) => block.rowHeaderColumn && cellIndex === 0 ? (
                        <th key={`${key}-cell-${rowIndex}-${cellIndex}`} scope="row">{cell}</th>
                      ) : (
                        <td key={`${key}-cell-${rowIndex}-${cellIndex}`}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        if (block.type === 'choice-grid') {
          return (
            <ul className={`prompt-choice-grid columns-${block.columns}`} key={key}>
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-choice-${itemIndex}`}>{item}</li>
              ))}
            </ul>
          );
        }
        if (block.type === 'source-figure') {
          const [sourceWidth, sourceHeight] = block.sourceSize;
          const [cropX, cropY, cropWidth, cropHeight] = block.crop;
          return (
            <figure className="prompt-source-figure" key={key}>
              <svg
                viewBox={`${cropX} ${cropY} ${cropWidth} ${cropHeight}`}
                role="img"
                aria-label={block.alt}
              >
                <image
                  href={block.src}
                  width={sourceWidth}
                  height={sourceHeight}
                  preserveAspectRatio="xMidYMid meet"
                />
              </svg>
              {block.caption ? <figcaption>{block.caption}</figcaption> : null}
            </figure>
          );
        }
        return <pre className="prompt-preformatted" key={key}>{block.text}</pre>;
      })}
    </section>
  );
}

function InlineText({ children }: { children: string }) {
  return (
    <>
      {children.split(/(`[^`]+`)/g).filter(Boolean).map((part, index) =>
        part.startsWith('`') && part.endsWith('`') ? (
          <code className="inline-code" key={`${part}-${index}`}>{part.slice(1, -1)}</code>
        ) : (
          <span key={`${part}-${index}`}>{part}</span>
        ),
      )}
    </>
  );
}

function ExplanationList({
  title,
  items,
  ordered = false,
}: {
  title: string;
  items: string[];
  ordered?: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <section className="explanation-section">
      <h4>{title}</h4>
      {ordered ? (
        <ol>
          {items.map((item, index) => (
            <li key={`${title}-${index}`}><InlineText>{item}</InlineText></li>
          ))}
        </ol>
      ) : (
        <ul>
          {items.map((item, index) => (
            <li key={`${title}-${index}`}><InlineText>{item}</InlineText></li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Explanation({
  question,
  answerValues,
  result,
}: {
  question: PracticalQuestion;
  answerValues: string[];
  result: QuestionResult;
}) {
  return (
    <section className="explanation" aria-live="polite">
      <div className={`feedback-banner ${result.correct ? 'correct' : 'wrong'}`}>
        {result.correct ? <CheckCircle2 /> : <XCircle />}
        <div>
          <strong>{result.correct ? '정답이에요!' : '여기서 한 번 더 확인해 봐요.'}</strong>
          <span>
            정답 문항은 모든 답칸이 맞아야 합니다. 공백과 영문 대소문자는 채점에서
            제외됩니다.
          </span>
        </div>
      </div>

      <div className="answer-review">
        {question.answerParts.map((part, index) => (
          <div key={`${question.id}-${part.label}`}>
            <span>{part.label}</span>
            <p>
              내 답: <strong>{answerValues[index]?.trim() || '(미입력)'}</strong>
            </p>
            <p>
              정답: <strong>{part.answer}</strong>
            </p>
            {result.partCorrect[index] ? (
              <CheckCircle2 className="correct-icon" aria-label="정답" />
            ) : (
              <XCircle className="wrong-icon" aria-label="오답" />
            )}
          </div>
        ))}
      </div>

      {question.friendlyExplanation ? (
        <div className="friendly-solution">
          <div className="solution-title">
            {question.friendlyExplanation.kind === 'general'
              ? <BookOpenCheck size={22} />
              : <Code2 size={22} />}
            <div>
              <span>
                {question.friendlyExplanation.kind === 'general'
                  ? '초보자용 개념 풀이'
                  : `${question.language ?? 'SQL'} 실행 풀이`}
              </span>
              <h3>{question.friendlyExplanation.concept}</h3>
            </div>
          </div>
          <div className="solution-answer">
            <span>정답</span>
            <strong>{question.friendlyExplanation.answerSummary}</strong>
          </div>

          <ExplanationList
            title="먼저 알아둘 규칙"
            items={question.friendlyExplanation.rules}
          />
          <ExplanationList
            title={question.friendlyExplanation.kind === 'general' ? '풀이 과정' : '실행 순서'}
            items={question.friendlyExplanation.steps}
            ordered
          />

          {question.friendlyExplanation.trace && (
            <section className="explanation-section">
              <h4>값의 변화</h4>
              <div className="trace-table-wrap">
                <table className="trace-table">
                  <thead>
                    <tr>
                      {question.friendlyExplanation.trace.headers.map((header) => (
                        <th key={header}>{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {question.friendlyExplanation.trace.rows.map((row, rowIndex) => (
                      <tr key={`${question.id}-trace-${rowIndex}`}>
                        {row.map((cell, cellIndex) => (
                          <td key={`${question.id}-trace-${rowIndex}-${cellIndex}`}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {question.friendlyExplanation.trace.caption && (
                <p className="trace-caption">{question.friendlyExplanation.trace.caption}</p>
              )}
            </section>
          )}

          {question.friendlyExplanation.objectFlow &&
            question.friendlyExplanation.objectFlow.length > 0 && (
              <section className="explanation-section">
                <h4>객체·참조 흐름</h4>
                <div className="object-flow">
                  {question.friendlyExplanation.objectFlow.map((item, index) => (
                    <code key={`${question.id}-object-${index}`}>{item}</code>
                  ))}
                </div>
              </section>
            )}

          {(question.friendlyExplanation.outputMoment ||
            question.friendlyExplanation.calculation) && (
              <section className="explanation-section output-check">
                <h4>결과가 정해지는 순간</h4>
                {question.friendlyExplanation.outputMoment && (
                  <p><InlineText>{question.friendlyExplanation.outputMoment}</InlineText></p>
                )}
                {question.friendlyExplanation.calculation && (
                  <p>
                    <strong>마지막 계산:</strong>{' '}
                    <InlineText>{question.friendlyExplanation.calculation}</InlineText>
                  </p>
                )}
              </section>
            )}

          <ExplanationList
            title="보기·개념과 구분하기"
            items={question.friendlyExplanation.distinctions}
          />

          <div className="pitfall">
            <TriangleAlert size={18} />
            <div>
              <strong>자주 틀리는 지점</strong>
              <ul>
                {question.friendlyExplanation.pitfalls.map((item, index) => (
                  <li key={`${question.id}-pitfall-${index}`}><InlineText>{item}</InlineText></li>
                ))}
              </ul>
            </div>
          </div>

          <div className="takeaway">
            <strong>한 줄 정리</strong>
            <p><InlineText>{question.friendlyExplanation.takeaway}</InlineText></p>
          </div>

          <p className="verification-note">
            검증: {question.friendlyExplanation.verification.note}
          </p>
        </div>
      ) : (
        <div className="plain-solution">
          <h3>정답은 확인했지만 새 해설은 검토 중입니다.</h3>
          <p className="official-answer">{question.answer}</p>
        </div>
      )}

      {question.sourceExplanation && (
        <details className="source-explanation">
          <summary>검증 참고용 PDF 원문 해설 보기</summary>
          <pre>{question.sourceExplanation}</pre>
        </details>
      )}
    </section>
  );
}

function QuestionView({
  exam,
  question,
  answerValues,
  onAnswer,
  showExplanation,
  readOnly = false,
  mode,
}: {
  exam: PracticalExam;
  question: PracticalQuestion;
  answerValues: string[];
  onAnswer: (partIndex: number, value: string) => void;
  showExplanation: boolean;
  readOnly?: boolean;
  mode?: PracticeMode;
}) {
  const [mobilePane, setMobilePane] = useState<'problem' | 'explanation'>('problem');
  const result = gradeQuestion(question, answerValues);
  useEffect(() => {
    setMobilePane(showExplanation ? 'explanation' : 'problem');
  }, [question.id, showExplanation]);
  return (
    <article className="question-card">
      <header className="question-header">
        <div>
          <span className="question-number">문제 {question.number}</span>
          {question.language && <span className="language-chip">{question.language}</span>}
          {question.needsReview && <span className="review-chip">검토 필요</span>}
        </div>
        <span>원본 {question.sourcePage}쪽</span>
      </header>

      <div className="mobile-pane-tabs" role="tablist" aria-label="문제와 해설 전환">
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === 'problem'}
          className={mobilePane === 'problem' ? 'active' : ''}
          onClick={() => setMobilePane('problem')}
        >
          문제·답안
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === 'explanation'}
          className={mobilePane === 'explanation' ? 'active' : ''}
          disabled={!showExplanation}
          onClick={() => setMobilePane('explanation')}
        >
          해설
        </button>
      </div>

      <div className="learning-workspace">
        <section
          className={`problem-pane ${mobilePane === 'problem' ? 'mobile-active' : ''}`}
          aria-label="문제와 답안"
        >
          <StructuredPrompt question={question} />
          <SourcePage question={question} exam={exam} />

          {question.needsReview && !question.answerParts.length ? (
            <div className="review-warning">
              <TriangleAlert size={20} />
              <div>
                <strong>자동 채점을 보류한 문제입니다.</strong>
                {question.reviewReasons.map((reason) => <p key={reason}>{reason}</p>)}
              </div>
            </div>
          ) : (
            <section className="answer-form">
              <h3>{readOnly ? '이전에 작성한 답안' : '답안 작성'}</h3>
              {question.answerParts.map((part, index) => (
                <label key={`${question.id}-${part.label}`}>
                  <span>{part.label}</span>
                  <textarea
                    value={answerValues[index] ?? ''}
                    onChange={(event) => onAnswer(index, event.target.value)}
                    placeholder={
                      question.answerParts.length > 1
                        ? `${part.label}에 들어갈 답을 입력하세요`
                        : '정답을 입력하세요'
                    }
                    rows={question.answerParts.length > 1 ? 2 : 3}
                    spellCheck={false}
                    readOnly={readOnly}
                  />
                </label>
              ))}
              {!readOnly && (
                <p className="grading-note">
                  <Save size={15} /> 빈칸이어도 채점할 수 있으며, 입력 내용은 자동 저장됩니다.
                </p>
              )}
            </section>
          )}
        </section>

        <section
          className={`explanation-pane ${mobilePane === 'explanation' ? 'mobile-active' : ''}`}
          aria-label="정답과 해설"
        >
          {showExplanation ? (
            <Explanation question={question} answerValues={answerValues} result={result} />
          ) : (
            <div className="explanation-placeholder">
              <BookOpenCheck size={34} />
              <h3>
                {question.explanationStatus !== 'authored'
                  ? '해설 검토 중'
                  : mode === 'exam'
                    ? '시험 제출 전에는 해설이 잠겨 있습니다.'
                    : '해설이 준비되어 있습니다.'}
              </h3>
              <p>
                {question.explanationStatus === 'authored'
                  ? mode === 'exam'
                    ? '회차를 제출한 뒤 문제·해설 비교 화면에서 정답과 풀이를 확인할 수 있습니다.'
                    : '답을 몰라도 괜찮습니다. 빈칸인 채로 “채점하고 해설 보기”를 누를 수 있습니다.'
                  : '확실하게 검증된 내용만 보여드리기 위해 이 문항은 검토 중입니다.'}
              </p>
            </div>
          )}
        </section>
      </div>
    </article>
  );
}

function QuizPage({
  session,
  onSessionChange,
  onFinish,
  onHome,
}: {
  session: PracticeSession;
  onSessionChange: (session: PracticeSession) => void;
  onFinish: () => void;
  onHome: () => void;
}) {
  const [confirmation, setConfirmation] = useState<{
    message: string;
    confirmLabel: string;
    action: () => void;
  } | null>(null);
  const exam = examById.get(session.examId)!;
  const question = exam.questions[session.currentIndex];
  const answerValues = session.answers[question.id] ?? [];
  const revealed = session.revealedQuestionIds.includes(question.id);
  const practiceResults = useMemo(() => {
    const entries = exam.questions
      .filter((item) => session.revealedQuestionIds.includes(item.id))
      .map((item) => [item.id, gradeQuestion(item, session.answers[item.id])] as const);
    return new Map(entries);
  }, [exam.questions, session.answers, session.revealedQuestionIds]);

  const move = (index: number) => {
    onSessionChange({ ...session, currentIndex: Math.max(0, Math.min(index, exam.questionCount - 1)) });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    const handleArrowNavigation = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.matches('input, textarea, select') || target.isContentEditable)
      ) {
        return;
      }
      if (event.key === 'ArrowLeft' && session.currentIndex > 0) {
        event.preventDefault();
        move(session.currentIndex - 1);
      }
      if (event.key === 'ArrowRight' && session.currentIndex < exam.questionCount - 1) {
        event.preventDefault();
        move(session.currentIndex + 1);
      }
    };
    window.addEventListener('keydown', handleArrowNavigation);
    return () => window.removeEventListener('keydown', handleArrowNavigation);
  });

  const updateAnswer = (partIndex: number, value: string) => {
    const current = session.answers[question.id] ?? [];
    const next = [...current];
    next[partIndex] = value;
    onSessionChange({
      ...session,
      answers: { ...session.answers, [question.id]: next },
    });
  };

  const reveal = () => {
    onSessionChange({
      ...session,
      revealedQuestionIds: [...new Set([...session.revealedQuestionIds, question.id])],
    });
  };

  const submitExam = () => {
    const unanswered = exam.questions.filter(
      (item) => !isQuestionAnswered(item, session.answers),
    );
    const message = unanswered.length
      ? `아직 답하지 않은 문제가 ${unanswered.length}개 있습니다 (${unanswered
          .map((item) => item.number)
          .join(', ')}번). 그래도 제출할까요?`
      : '시험 답안을 제출하고 결과를 확인할까요?';
    setConfirmation({
      message,
      confirmLabel: '제출하고 결과 보기',
      action: onFinish,
    });
  };

  const next = () => {
    if (session.currentIndex === exam.questionCount - 1) {
      setConfirmation({
        message: '연습을 마치고 전체 결과를 확인할까요?',
        confirmLabel: '마치고 결과 보기',
        action: onFinish,
      });
      return;
    }
    move(session.currentIndex + 1);
  };

  return (
    <main className="quiz-page">
      <header className="quiz-toolbar">
        <button className="icon-button" onClick={onHome} aria-label="홈으로">
          <Home size={20} />
        </button>
        <div>
          <strong>{exam.title}</strong>
          <span>{session.mode === 'practice' ? '연습 모드' : '시험 모드'}</span>
        </div>
        <div className="progress-copy">
          {session.currentIndex + 1} / {exam.questionCount}
        </div>
      </header>
      <div
        className="progress-track"
        aria-label={`진행률 ${session.currentIndex + 1}/${exam.questionCount}`}
      >
        <span style={{ width: `${((session.currentIndex + 1) / exam.questionCount) * 100}%` }} />
      </div>

      <div className="quiz-layout">
        <QuestionNavigation
          exam={exam}
          session={session}
          currentIndex={session.currentIndex}
          results={practiceResults}
          onMove={move}
        />

        <div className="question-column">
          <QuestionView
            exam={exam}
            question={question}
            answerValues={answerValues}
            onAnswer={updateAnswer}
            showExplanation={session.mode === 'practice' && revealed}
            mode={session.mode}
          />

          <nav className="question-actions">
            <button
              className="button secondary"
              onClick={() => move(session.currentIndex - 1)}
              disabled={session.currentIndex === 0}
            >
              <ArrowLeft size={18} /> 이전
            </button>
            {session.mode === 'practice' ? (
              revealed ? (
                <button className="button primary" onClick={next}>
                  {session.currentIndex === exam.questionCount - 1 ? '결과 보기' : '다음 문제'}
                  <ArrowRight size={18} />
                </button>
              ) : (
                <button className="button primary" onClick={reveal}>
                  <BookOpenCheck size={18} /> 채점하고 해설 보기
                </button>
              )
            ) : session.currentIndex === exam.questionCount - 1 ? (
              <button className="button primary" onClick={submitExam}>
                시험 제출
              </button>
            ) : (
              <button className="button primary" onClick={() => move(session.currentIndex + 1)}>
                다음 <ArrowRight size={18} />
              </button>
            )}
          </nav>
        </div>
      </div>
      {confirmation && (
        <div className="modal-backdrop" role="presentation">
          <section
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
          >
            <span className="eyebrow">제출 확인</span>
            <h2 id="confirm-title">이대로 마칠까요?</h2>
            <p>{confirmation.message}</p>
            <div>
              <button className="button secondary" onClick={() => setConfirmation(null)}>
                계속 풀기
              </button>
              <button
                className="button primary"
                onClick={() => {
                  const action = confirmation.action;
                  setConfirmation(null);
                  action();
                }}
              >
                {confirmation.confirmLabel}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

function ResultPage({
  attempt,
  onHome,
  onRetry,
  onReview,
}: {
  attempt: StudyAttempt;
  onHome: () => void;
  onRetry: () => void;
  onReview: () => void;
}) {
  const exam = examById.get(attempt.examId)!;
  const wrongCount = attempt.totalQuestions - attempt.correctQuestions;
  return (
    <main className="result-page">
      <section className="result-hero">
        <span className="eyebrow">{exam.title} 학습 결과</span>
        <h1>
          {wrongCount === 0 ? '전부 맞혔어요!' : '오늘 헷갈린 부분이 다음 공부 방향이에요.'}
        </h1>
        <div className="result-metrics">
          <div>
            <strong>{attempt.correctQuestions}/{attempt.totalQuestions}</strong>
            <span>정답 문항</span>
          </div>
          <div>
            <strong>{percent(attempt.correctFields, attempt.totalFields)}%</strong>
            <span>답칸 정답률</span>
          </div>
          <div>
            <strong>{wrongCount}</strong>
            <span>복습 문항</span>
          </div>
        </div>
        <p className="score-note">
          공식 부분 배점이 공개되지 않은 문항이 있어 환산 점수는 표시하지 않습니다.
        </p>
      </section>

      <div className="result-actions">
        <button className="button secondary" onClick={onHome}><Home size={18} /> 홈으로</button>
        <button className="button secondary" onClick={onRetry}><RotateCcw size={18} /> 다시 풀기</button>
        <button className="button primary" onClick={onReview}>
          <BookOpenCheck size={18} /> 문제·해설 비교
        </button>
      </div>
    </main>
  );
}

function ReviewPage({
  attempt,
  onHome,
  showAll = false,
}: {
  attempt: StudyAttempt;
  onHome: () => void;
  showAll?: boolean;
}) {
  const exam = examById.get(attempt.examId)!;
  const resultById = new Map(attempt.results.map((result) => [result.questionId, result]));
  const reviewQuestions = showAll
    ? exam.questions
    : exam.questions.filter((question) => !resultById.get(question.id)?.correct);
  const [index, setIndex] = useState(0);
  const question = reviewQuestions[index];

  useEffect(() => {
    const handleArrowNavigation = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        (target.matches('input, textarea, select') || target.isContentEditable)
      ) {
        return;
      }
      if (event.key === 'ArrowLeft' && index > 0) {
        event.preventDefault();
        setIndex((value) => value - 1);
      }
      if (event.key === 'ArrowRight' && index < reviewQuestions.length - 1) {
        event.preventDefault();
        setIndex((value) => value + 1);
      }
    };
    window.addEventListener('keydown', handleArrowNavigation);
    return () => window.removeEventListener('keydown', handleArrowNavigation);
  }, [index, reviewQuestions.length]);

  if (!question) {
    return (
      <main className="result-page">
        <section className="result-hero">
          <CheckCircle2 size={48} className="correct-icon" />
          <h1>복습할 오답이 없습니다.</h1>
          <button className="button primary" onClick={onHome}>홈으로</button>
        </section>
      </main>
    );
  }

  return (
    <main className="review-page">
      <header className="quiz-toolbar">
        <button className="icon-button" onClick={onHome} aria-label="홈으로">
          <Home size={20} />
        </button>
        <div>
          <strong>{exam.title} {showAll ? '문제·해설 비교' : '오답 복습'}</strong>
          <span>{index + 1} / {reviewQuestions.length}</span>
        </div>
      </header>
      <div className="review-container">
        <QuestionView
          exam={exam}
          question={question}
          answerValues={attempt.answers[question.id] ?? []}
          onAnswer={() => undefined}
          showExplanation
          readOnly
        />
        <nav className="question-actions">
          <button
            className="button secondary"
            disabled={index === 0}
            onClick={() => setIndex((value) => value - 1)}
          >
              <ArrowLeft size={18} /> 이전 문제
          </button>
          {index === reviewQuestions.length - 1 ? (
            <button className="button primary" onClick={onHome}>복습 마치기</button>
          ) : (
            <button className="button primary" onClick={() => setIndex((value) => value + 1)}>
              다음 문제 <ArrowRight size={18} />
            </button>
          )}
        </nav>
      </div>
    </main>
  );
}

export default function App({ examData }: { examData: ExamCollection }) {
  data = examData;
  examById = new Map(data.exams.map((exam) => [exam.id, exam]));
  const storedSession = useMemo(() => {
    const saved = loadSession();
    return saved && examById.has(saved.examId) ? saved : null;
  }, []);
  const [session, setSession] = useState<PracticeSession | null>(storedSession);
  const [attempts, setAttempts] = useState<StudyAttempt[]>(() => loadAttempts());
  const [activeAttempt, setActiveAttempt] = useState<StudyAttempt | null>(null);
  const [reviewAll, setReviewAll] = useState(false);
  const [screen, setScreen] = useState<Screen>('home');

  useEffect(() => {
    if (session) saveSession(session);
  }, [session]);

  const start = (examId: string, mode: PracticeMode) => {
    const next = makeSession(examId, mode);
    setSession(next);
    setActiveAttempt(null);
    setScreen('quiz');
    window.scrollTo(0, 0);
  };

  const finish = () => {
    if (!session) return;
    const exam = examById.get(session.examId);
    if (!exam) return;
    const results = gradeQuestions(exam.questions, session.answers);
    const counts = getResultCounts(exam.questions, results);
    const attempt: StudyAttempt = {
      id: createId('attempt'),
      sessionId: session.id,
      examId: session.examId,
      mode: session.mode,
      completedAt: new Date().toISOString(),
      answers: session.answers,
      results,
      ...counts,
    };
    saveAttempt(attempt);
    setAttempts(loadAttempts());
    setActiveAttempt(attempt);
    clearSession();
    setSession(null);
    setScreen('result');
    window.scrollTo(0, 0);
  };

  const goHome = () => {
    setScreen('home');
    setActiveAttempt(null);
    window.scrollTo(0, 0);
  };

  if (screen === 'quiz' && session) {
    return (
      <QuizPage
        session={session}
        onSessionChange={setSession}
        onFinish={finish}
        onHome={goHome}
      />
    );
  }

  if (screen === 'result' && activeAttempt) {
    return (
      <ResultPage
        attempt={activeAttempt}
        onHome={goHome}
        onRetry={() => start(activeAttempt.examId, activeAttempt.mode)}
        onReview={() => {
          setReviewAll(true);
          setScreen('review');
        }}
      />
    );
  }

  if (screen === 'review' && activeAttempt) {
    return <ReviewPage attempt={activeAttempt} onHome={goHome} showAll={reviewAll} />;
  }

  return (
    <HomePage
      attempts={attempts}
      resumableSession={storedSession ?? session}
      onResume={() => {
        if (storedSession) setSession(storedSession);
        setScreen('quiz');
      }}
      onStart={start}
      onReview={(attempt) => {
        setActiveAttempt(attempt);
        setReviewAll(false);
        setScreen('review');
      }}
    />
  );
}
