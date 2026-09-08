import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import type { ExamCollection } from './types';
import './styles.css';

async function start(): Promise<void> {
  const root = createRoot(document.getElementById('root')!);
  try {
    const response = await fetch('/data/exams.json');
    if (!response.ok) throw new Error(`문제 데이터를 읽지 못했습니다 (${response.status})`);
    const examData = (await response.json()) as ExamCollection;
    root.render(
      <StrictMode>
        <App examData={examData} />
      </StrictMode>,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : '알 수 없는 오류';
    root.render(
      <main style={{ maxWidth: 720, margin: '80px auto', padding: 24 }}>
        <h1>문제 데이터를 열지 못했어요.</h1>
        <p>{message}</p>
        <p>터미널에서 <code>npm run extract-data</code>를 실행한 뒤 다시 열어 주세요.</p>
      </main>,
    );
  }
}

void start();
