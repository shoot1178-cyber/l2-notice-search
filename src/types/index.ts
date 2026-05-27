export type ServerType = '전체' | '본서버' | '각성서버' | 'L2노트' | '말하는섬';

export interface Notice {
  id: string;
  title: string;
  date: string;
  server: string;
  url: string;
  content: string;
  preview: string;
}

export interface NoticesIndex {
  lastUpdated: string;
  total: number;
  notices: Notice[];
}

export type SortOrder = 'desc' | 'asc';
