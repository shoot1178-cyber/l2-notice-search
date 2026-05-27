export function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function parseDate(dateStr: string): number {
  const formats = [
    /(\d{4})\.(\d{1,2})\.(\d{1,2})/,
    /(\d{4})-(\d{1,2})-(\d{1,2})/,
    /(\d{4})\/(\d{1,2})\/(\d{1,2})/,
  ];
  for (const fmt of formats) {
    const m = dateStr.match(fmt);
    if (m) {
      return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime();
    }
  }
  return 0;
}

export const SERVER_COLORS: Record<string, string> = {
  '본서버': 'bg-blue-600 text-blue-100',
  '각성서버': 'bg-purple-600 text-purple-100',
  'L2노트': 'bg-emerald-600 text-emerald-100',
  '말하는섬': 'bg-cyan-600 text-cyan-100',
};

export function getServerColor(server: string): string {
  return SERVER_COLORS[server] ?? 'bg-gray-600 text-gray-100';
}
