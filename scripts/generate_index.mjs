import { readFileSync, writeFileSync, readdirSync } from 'fs';
import { join, basename, extname } from 'path';

const noticesDir = 'notices';

function parseNoticeFile(filepath) {
  const text = readFileSync(filepath, 'utf-8');
  const sections = text.split(/={4,}/);
  const notices = [];

  for (let i = 0; i < sections.length; i++) {
    const section = sections[i].trim();
    if (!section) continue;

    let title = '', date = '', server = '', url = '';
    const contentLines = [];
    let inContent = false;

    for (const line of section.split('\n')) {
      if (line.startsWith('제목:')) {
        title = line.slice(3).trim();
      } else if (line.startsWith('날짜:')) {
        date = line.slice(3).trim();
      } else if (line.startsWith('서버:')) {
        server = line.slice(3).trim();
      } else if (line.startsWith('URL:')) {
        url = line.slice(4).trim();
      } else if (line.startsWith('내용:')) {
        inContent = true;
        const rest = line.slice(3).trim();
        if (rest) contentLines.push(rest);
      } else if (inContent) {
        contentLines.push(line);
      }
    }

    if (!title) continue;

    const content = contentLines.join('\n').trim();
    const preview = content.length > 200 ? content.slice(0, 200) + '...' : content;
    const stem = basename(filepath, extname(filepath));

    notices.push({ id: `${stem}_${i}`, title, date, server: server || '본서버', url, content, preview });
  }

  return notices;
}

function parseDate(d) {
  const formats = [/^(\d{4})\.(\d{2})\.(\d{2})$/, /^(\d{4})-(\d{2})-(\d{2})$/, /^(\d{4})\/(\d{2})\/(\d{2})$/];
  for (const fmt of formats) {
    const m = d.match(fmt);
    if (m) return new Date(`${m[1]}-${m[2]}-${m[3]}`).getTime();
  }
  return 0;
}

const txtFiles = readdirSync(noticesDir).filter(f => f.endsWith('.txt')).sort();

if (!txtFiles.length) {
  console.log('⚠️  notices/ 폴더에 txt 파일이 없습니다.');
  process.exit(0);
}

const allNotices = [];
for (const file of txtFiles) {
  const filepath = join(noticesDir, file);
  console.log(`파싱: ${file}`);
  const notices = parseNoticeFile(filepath);
  allNotices.push(...notices);
  console.log(`  → ${notices.length}건`);
}

allNotices.sort((a, b) => parseDate(b.date) - parseDate(a.date));

const index = {
  lastUpdated: new Date().toISOString(),
  total: allNotices.length,
  notices: allNotices,
};

writeFileSync(join(noticesDir, 'index.json'), JSON.stringify(index, null, 2), 'utf-8');
console.log(`\n✅ notices/index.json 생성 완료: ${allNotices.length}건`);
