import type { PracticeSession, StudyAttempt } from '../types';

const SESSION_KEY = 'practical-practice:v1:session';
const ATTEMPTS_KEY = 'practical-practice:v1:attempts';

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function loadSession(): PracticeSession | null {
  return loadJson<PracticeSession | null>(SESSION_KEY, null);
}

export function saveSession(session: PracticeSession): void {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(SESSION_KEY);
}

export function loadAttempts(): StudyAttempt[] {
  return loadJson<StudyAttempt[]>(ATTEMPTS_KEY, []);
}

export function saveAttempt(attempt: StudyAttempt): void {
  const attempts = loadAttempts().filter((item) => item.id !== attempt.id);
  window.localStorage.setItem(
    ATTEMPTS_KEY,
    JSON.stringify([attempt, ...attempts].slice(0, 100)),
  );
}
