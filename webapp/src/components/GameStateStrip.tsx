interface Props {
  gid: string;
  ts: number;
  pWin: number;
}

export function GameStateStrip({ gid, ts, pWin }: Props) {
  const date = new Date(ts).toLocaleTimeString();
  return (
    <div style={{ display: "flex", gap: "1rem", alignItems: "baseline" }}>
      <strong>{gid}</strong>
      <span>{date}</span>
      <span>{(pWin * 100).toFixed(2)}% win</span>
    </div>
  );
}
