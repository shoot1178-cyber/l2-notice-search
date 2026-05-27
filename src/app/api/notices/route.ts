import { NextResponse } from 'next/server';
import { fetchNoticesIndex } from '@/lib/github';

export async function GET() {
  try {
    const data = await fetchNoticesIndex();
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : '알 수 없는 오류';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
