import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '리니지2 공지 검색',
  description: '리니지2 공식 공지사항 통합 검색 서비스',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
