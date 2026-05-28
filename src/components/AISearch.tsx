'use client';

import { useState, useRef } from 'react';

const EXAMPLE_QUERIES = [
  '본서버 최근 이벤트 알려줘',
  '각성서버 사냥터 변경 공지',
  '점검 일정 알려줘',
];

export default function AISearch() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const submit = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || loading) return;

    abortRef.current?.abort();
    const abort = new AbortController();
    abortRef.current = abort;

    setAnswer('');
    setLoading(true);

    try {
      const res = await fetch('/api/ai-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed }),
        signal: abort.signal,
      });

      if (!res.ok) {
        const err = await res.json() as { error?: string };
        setAnswer(err.error ?? '오류가 발생했습니다.');
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let text = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        text += decoder.decode(value, { stream: true });
        setAnswer(text);
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setAnswer('요청 중 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit(query);
  };

  return (
    <div className="rounded-xl border border-amber-900/40 bg-slate-900/60 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-lg">✨</span>
        <h2 className="text-sm font-semibold text-amber-400">AI 공지 검색</h2>
        <span className="text-xs text-gray-500">자연어로 질문하세요</span>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="예: 본서버 최근 이벤트 알려줘"
          className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm
                     text-gray-200 placeholder-gray-500
                     focus:outline-none focus:border-amber-600 transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white whitespace-nowrap
                     bg-amber-700 hover:bg-amber-600
                     disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors"
        >
          {loading ? '검색 중…' : '검색'}
        </button>
      </form>

      {/* Example queries */}
      {!answer && !loading && (
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => { setQuery(q); submit(q); }}
              className="px-2.5 py-1 rounded-full text-xs border border-slate-700 text-gray-400
                         hover:border-amber-700 hover:text-amber-400 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Response */}
      {(answer || loading) && (
        <div className="rounded-lg bg-slate-800/60 border border-slate-700 p-3 text-sm text-gray-300
                        leading-relaxed whitespace-pre-wrap min-h-[60px]">
          {answer || (
            <span className="text-gray-500 animate-pulse">AI가 공지를 분석하고 있습니다…</span>
          )}
          {loading && answer && (
            <span className="inline-block w-1.5 h-4 bg-amber-500 ml-0.5 animate-pulse align-middle" />
          )}
        </div>
      )}
    </div>
  );
}
