export interface WinProbSnapshot {
  gid: string;
  ts: number;
  p_win: number;
  explain: Record<string, unknown>;
}

export interface LiveMessage extends WinProbSnapshot {}
