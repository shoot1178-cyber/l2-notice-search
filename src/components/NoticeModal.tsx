'use client';

import { useEffect } from 'react';
import { Notice } from '@/types';
import { getServerColor } from '@/lib/utils';
import Highlight from './Highlight';

interface Props {
  notice: Notice;
  query: string;
  onClose: () => void;
}

export default function NoticeModal({ notice, query, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl
                      max-h-[90vh] flex flex-col shadow-2xl shadow-black/50">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 p-6 border-b border-slate-700 flex-shrink-0">
          <div className="space-y-2 flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${getServerColor(notice.server)}`}>
                {notice.server}
              </span>
              <span className="text-sm text-gray-400">{notice.date}</span>
            </div>
            <h2 className="text-lg font-bold text-gray-100 leading-snug">
              <Highlight text={notice.title} query={query} />
            </h2>
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg
                       text-gray-400 hover:text-gray-200 hover:bg-slate-700 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-6">
          <div className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
            <Highlight text={notice.content || notice.preview} query={query} />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-slate-700 flex-shrink-0">
          {notice.url ? (
            <a
              href={notice.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-amber-400 hover:text-amber-300 transition-colors underline underline-offset-4"
            >
              원문 보기 →
            </a>
          ) : (
            <span />
          )}
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-700 hover:bg-slate-600 text-gray-200 text-sm
                       rounded-lg transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
