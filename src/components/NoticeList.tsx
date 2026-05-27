'use client';

import { Notice } from '@/types';
import NoticeCard from './NoticeCard';

interface Props {
  notices: Notice[];
  loading: boolean;
  error: string | null;
  query: string;
  onSelect: (notice: Notice) => void;
}

function SkeletonCard() {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-6 w-16 bg-slate-700 rounded-full" />
        <div className="h-4 w-24 bg-slate-700 rounded" />
      </div>
      <div className="h-5 bg-slate-700 rounded mb-2 w-3/4" />
      <div className="space-y-1.5">
        <div className="h-4 bg-slate-700 rounded w-full" />
        <div className="h-4 bg-slate-700 rounded w-5/6" />
        <div className="h-4 bg-slate-700 rounded w-4/6" />
      </div>
    </div>
  );
}

export default function NoticeList({ notices, loading, error, query, onSelect }: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <div className="text-5xl mb-4">⚠️</div>
        <p className="text-gray-400 mb-2">공지를 불러오는데 실패했습니다.</p>
        <p className="text-sm text-gray-600">{error}</p>
      </div>
    );
  }

  if (notices.length === 0) {
    return (
      <div className="text-center py-20">
        <div className="text-5xl mb-4">🔍</div>
        <p className="text-gray-400 mb-1">검색 결과가 없습니다.</p>
        {query && (
          <p className="text-sm text-gray-600">다른 키워드로 검색해보세요.</p>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {notices.map((notice) => (
        <NoticeCard
          key={notice.id}
          notice={notice}
          query={query}
          onClick={() => onSelect(notice)}
        />
      ))}
    </div>
  );
}
