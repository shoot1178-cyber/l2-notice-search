'use client';

import { ServerType } from '@/types';

const SERVERS: { label: string; value: ServerType }[] = [
  { label: '전체', value: '전체' },
  { label: '본서버', value: '본서버' },
  { label: '각성서버', value: '각성서버' },
  { label: 'L2노트', value: 'L2노트' },
  { label: '말하는섬', value: '말하는섬' },
];

interface Props {
  selected: ServerType;
  onChange: (server: ServerType) => void;
  counts: Record<string, number>;
}

export default function ServerFilter({ selected, onChange, counts }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {SERVERS.map(({ label, value }) => {
        const count = value === '전체'
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : (counts[value] ?? 0);

        if (value !== '전체' && count === 0) return null;

        const isActive = selected === value;
        return (
          <button
            key={value}
            onClick={() => onChange(value)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all
              ${isActive
                ? 'bg-amber-500 text-slate-900 shadow-lg shadow-amber-500/25'
                : 'bg-slate-800 text-gray-300 border border-slate-600 hover:border-amber-500/50 hover:text-gray-100'
              }`}
          >
            {label}
            {count > 0 && (
              <span className={`ml-1.5 text-xs ${isActive ? 'text-slate-700' : 'text-gray-500'}`}>
                {count.toLocaleString()}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
