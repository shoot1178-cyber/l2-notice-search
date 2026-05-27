'use client';

import { escapeRegex } from '@/lib/utils';

interface Props {
  text: string;
  query: string;
}

export default function Highlight({ text, query }: Props) {
  if (!query.trim()) return <>{text}</>;

  const escaped = escapeRegex(query);
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));
  const matchRegex = new RegExp(`^${escaped}$`, 'i');

  return (
    <>
      {parts.map((part, i) =>
        matchRegex.test(part) ? (
          <mark key={i} className="bg-amber-400/30 text-amber-200 rounded-sm px-0.5">
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </>
  );
}
