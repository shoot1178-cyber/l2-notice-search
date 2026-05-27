import { NoticesIndex } from '@/types';

export async function fetchNoticesIndex(): Promise<NoticesIndex> {
  const owner = process.env.GITHUB_REPO_OWNER;
  const repo = process.env.GITHUB_REPO_NAME;
  const token = process.env.GITHUB_TOKEN;

  if (!owner || !repo) {
    throw new Error('GITHUB_REPO_OWNER 와 GITHUB_REPO_NAME 환경변수를 설정해주세요.');
  }

  const url = `https://raw.githubusercontent.com/${owner}/${repo}/main/notices/index.json`;

  const headers: Record<string, string> = {
    'Cache-Control': 'no-cache',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    headers,
    next: { revalidate: 3600 },
  });

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error('notices/index.json 파일을 찾을 수 없습니다. GitHub Actions로 크롤링을 먼저 실행해주세요.');
    }
    throw new Error(`GitHub에서 데이터를 가져오는데 실패했습니다. (${res.status})`);
  }

  return res.json();
}
