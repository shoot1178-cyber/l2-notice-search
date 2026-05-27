'use client';

interface Props {
  query: string;
  onChange: (value: string) => void;
  filteredCount: number;
  totalCount: number;
}

export default function SearchBar({ query, onChange, filteredCount, totalCount }: Props) {
  return (
    <div className="space-y-2">
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
        <input
          type="text"
          value={query}
          onChange={(e) => onChange(e.target.value)}
          placeholder="제목 또는 내용으로 검색..."
          className="w-full bg-slate-800 border border-slate-600 rounded-xl pl-12 pr-4 py-3.5
                     text-gray-100 placeholder-gray-500 text-base
                     focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/50
                     transition-colors"
        />
        {query && (
          <button
            onClick={() => onChange('')}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
      <p className="text-sm text-gray-500 pl-1">
        {query ? (
          <>
            <span className="text-amber-400 font-medium">{filteredCount.toLocaleString()}</span>건 검색됨
            {' '}(전체 {totalCount.toLocaleString()}건)
          </>
        ) : (
          <>전체 <span className="text-amber-400 font-medium">{totalCount.toLocaleString()}</span>건</>
        )}
      </p>
    </div>
  );
}
