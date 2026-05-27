'use client';

import { Notice } from '@/types';
import { getServerColor } from '@/lib/utils';
import Highlight from './Highlight';

interface Props {
  notice: Notice;
  query: string;
  onClick: () => void;
}

export default function NoticeCard({ notice, query, onClick }: Props) {
  return (
    <article
      onClick={onClick}
      className="bg-slate-800 border border-slate-700 rounded-xl p-5 cursor-pointer
                 hover:border-amber-500/40 hover:bg-slate-750 hover:shadow-lg hover:shadow-amber-500/5
                 transition-all group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${getServerColor(notice.server)}`}>
            {notice.server}
          </span>
          <span className="text-xs text-gray-500">{notice.date}</span>
        </div>
        <span className="text-gray-600 group-hover:text-amber-500/70 transition-colors text-sm flex-shrink-0">→</span>
      </div>

      <h3 className="font-semibold text-gray-100 mb-2 line-clamp-2 group-hover:text-amber-100 transition-colors">
        <Highlight text={notice.title} query={query} />
      </h3>

      {notice.preview && (
        <p className="text-sm text-gray-400 line-clamp-3 leading-relaxed">
          <Highlight text={notice.preview} query={query} />
        </p>
      )}
    </article>
  );
}
