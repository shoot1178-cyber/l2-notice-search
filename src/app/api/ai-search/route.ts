import { NextRequest } from 'next/server';
import { fetchNoticesIndex } from '@/lib/github';
import { Notice } from '@/types';

export const runtime = 'nodejs';

// 서버명 별칭 매핑
const SERVER_ALIASES: Record<string, string> = {
  '본서버': '본서버',
  '각성서버': '각성서버',
  '각성': '각성서버',
  'l2노트': 'L2노트',
  '노트': 'L2노트',
  '말하는섬': '말하는섬',
  '말섬': '말하는섬',
};

// 의미 없는 검색어
const STOP_WORDS = new Set([
  '알려줘', '알려', '주세요', '줘', '알고싶어', '궁금해', '궁금', '찾아줘',
  '최근', '요즘', '언제', '뭐', '무엇', '어떤', '어떻게',
  '이', '가', '을', '를', '의', '에', '서', '는', '은', '도', '만', '와', '과', '으로',
  '있나요', '있어', '있었어', '했어', '했나', '됐나', '했는지',
  '본서버', '각성서버', '각성', 'l2노트', '노트', '말하는섬', '말섬',
]);

function preFilter(notices: Notice[], query: string): Notice[] {
  const q = query.toLowerCase();

  // 서버 감지
  let serverFilter: string | null = null;
  for (const [alias, name] of Object.entries(SERVER_ALIASES)) {
    if (q.includes(alias)) {
      serverFilter = name;
      break;
    }
  }

  // 콘텐츠 키워드 추출
  const keywords = q
    .split(/[\s,]+/)
    .map((k) => k.trim())
    .filter((k) => k.length >= 2 && !STOP_WORDS.has(k));

  // 서버 필터 적용
  const pool = serverFilter
    ? notices.filter((n) => n.server === serverFilter)
    : notices;

  // 키워드 점수 기반 필터
  if (keywords.length > 0) {
    const scored = pool
      .map((n) => {
        const text = (n.title + ' ' + n.preview).toLowerCase();
        const score = keywords.reduce((s, k) => s + (text.includes(k) ? 1 : 0), 0);
        return { notice: n, score };
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score);

    if (scored.length >= 5) {
      return scored.slice(0, 50).map((x) => x.notice);
    }
  }

  // 결과 부족 시 최근 공지로 폴백
  return pool.slice(0, 30);
}

export async function POST(req: NextRequest) {
  const body = await req.json() as { query?: string };
  const query = body.query?.trim() ?? '';

  if (!query) {
    return new Response(JSON.stringify({ error: '질문을 입력해주세요.' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return new Response(
      JSON.stringify({ error: 'GEMINI_API_KEY가 서버에 설정되지 않았습니다.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  let noticesData;
  try {
    noticesData = await fetchNoticesIndex();
  } catch {
    return new Response(
      JSON.stringify({ error: '공지 데이터를 불러오는 데 실패했습니다.' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  const relevant = preFilter(noticesData.notices, query);

  const noticesText = relevant
    .map((n, i) => `[${i + 1}] 제목: ${n.title} | 날짜: ${n.date} | 서버: ${n.server}\n${n.preview}`)
    .join('\n\n');

  const systemPrompt =
    '당신은 리니지2 게임 공지사항 검색 도우미입니다. ' +
    '제공된 공지 목록에서 사용자 질문과 관련된 내용을 찾아 한국어로 간결하게 요약합니다.\n\n' +
    '규칙:\n' +
    '- 관련 공지가 있으면 핵심 내용·날짜·서버를 포함해 답변\n' +
    '- 여러 공지가 관련 있으면 최신순으로 3~5개 요약\n' +
    '- 관련 공지가 없으면 솔직하게 안내\n' +
    '- 공지 원문을 그대로 나열하지 말고 질문에 맞게 요약';

  const userMessage = `${systemPrompt}\n\n공지사항 목록 (${relevant.length}건):\n\n${noticesText}\n\n---\n질문: ${query}`;

  const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-001:generateContent?key=${apiKey}`;

  try {
    const geminiRes = await fetch(geminiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: 'user', parts: [{ text: userMessage }] }],
      }),
    });

    if (!geminiRes.ok) {
      const errData = await geminiRes.json() as { error?: { message?: string } };
      return new Response(
        JSON.stringify({ error: `Gemini API 오류: ${errData?.error?.message ?? geminiRes.statusText}` }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const data = await geminiRes.json() as {
      candidates?: { content?: { parts?: { text?: string }[] } }[];
    };
    const answer = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? '응답을 받을 수 없습니다.';

    return new Response(JSON.stringify({ answer }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : '알 수 없는 오류';
    return new Response(
      JSON.stringify({ error: `오류가 발생했습니다: ${msg}` }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
