'use client';

import { useState, useEffect, useMemo } from 'react';
import { Notice, NoticesIndex, ServerType, SortOrder } from '@/types';
import { parseDate } from '@/lib/utils';
import SearchBar from '@/components/SearchBar';
import ServerFilter from '@/components/ServerFilter';
import NoticeList from '@/components/NoticeList';
import NoticeModal from '@/components/NoticeModal';

export default function Home() {
  const [data, setData] = useState<NoticesIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [server, setServer] = useState<ServerType>('전체');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);

  useEffect(() => {
    fetch('/api/notices')
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(new Error(d.error)));
        return r.json();
      })
      .then((d: NoticesIndex) => {
        setData(d);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const serverCounts = useMemo(() => {
    if (!data) return {};
    return data.notices.reduce<Record<string, number>>((acc, n) => {
      acc[n.server] = (acc[n.server] ?? 0) + 1;
      return acc;
    }, {});
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    let result = data.notices;

    if (server !== '전체') {
      result = result.filter((n) => n.server === server);
    }

    if (query.trim()) {
      const q = query.toLowerCase();
      result = result.filter(
        (n) => n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q)
      );
    }

    return [...result].sort((a, b) => {
      const da = parseDate(a.date);
      const db = parseDate(b.date);
      return sortOrder === 'desc' ? db - da : da - db;
    });
  }, [data, server, query, sortOrder]);

  const lastUpdated = data?.lastUpdated
    ? new Date(data.lastUpdated).toLocaleString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚔️</span>
            <div>
              <h1 className="font-bold text-amber-400 text-lg leading-tight">리니지2 공지 검색</h1>
              <p className="text-xs text-gray-500">Lineage II Notice Search</p>
            </div>
          </div>
          {lastUpdated && (
            <p className="text-xs text-gray-600 hidden sm:block">
              마지막 업데이트: {lastUpdated}
            </p>
          )}
        </div>
      </header>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {/* Search */}
        <SearchBar
          query={query}
          onChange={setQuery}
          filteredCount={filtered.length}
          totalCount={data?.total ?? 0}
        />

        {/* Filters row */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <ServerFilter
            selected={server}
            onChange={setServer}
            counts={serverCounts}
          />

          <button
            onClick={() => setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-gray-400
                       bg-slate-800 border border-slate-700 hover:border-slate-500
                       hover:text-gray-200 transition-colors flex-shrink-0"
          >
            <span>{sortOrder === 'desc' ? '↓' : '↑'}</span>
            <span>{sortOrder === 'desc' ? '최신순' : '오래된순'}</span>
          </button>
        </div>

        {/* Notice list */}
        <NoticeList
          notices={filtered}
          loading={loading}
          error={error}
          query={query}
          onSelect={setSelectedNotice}
        />
      </main>

      {/* Modal */}
      {selectedNotice && (
        <NoticeModal
          notice={selectedNotice}
          query={query}
          onClose={() => setSelectedNotice(null)}
        />
      )}
    </div>
  );
}
