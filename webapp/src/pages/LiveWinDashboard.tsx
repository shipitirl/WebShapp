import { useEffect, useState } from "react";
import { LiveWinChart } from "../components/LiveWinChart";
import { ShapDeltaBars } from "../components/ShapDeltaBars";
import { GameStateStrip } from "../components/GameStateStrip";
import { fetchSnapshot, subscribeLive } from "../sockets";
import type { WinProbSnapshot } from "../types";

export function LiveWinDashboard() {
  const [snapshot, setSnapshot] = useState<WinProbSnapshot | null>(null);

  useEffect(() => {
    fetchSnapshot("demo").then(setSnapshot).catch(console.error);
    const unsub = subscribeLive((msg) => {
      setSnapshot({ gid: msg.gid, ts: msg.ts, p_win: msg.p_win, explain: msg.explain });
    });
    return () => unsub();
  }, []);

  return (
    <div style={{ padding: "1rem", fontFamily: "sans-serif" }}>
      <h1>Live Win Probability</h1>
      {snapshot ? (
        <>
          <GameStateStrip gid={snapshot.gid} ts={snapshot.ts} pWin={snapshot.p_win} />
          <LiveWinChart gid={snapshot.gid} pWin={snapshot.p_win} />
          <ShapDeltaBars explain={snapshot.explain} />
        </>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}
