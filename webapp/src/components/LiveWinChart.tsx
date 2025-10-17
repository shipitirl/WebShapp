import { useMemo } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface Props {
  gid: string;
  pWin: number;
}

export function LiveWinChart({ gid, pWin }: Props) {
  const data = useMemo(() => [{ name: "Now", value: pWin * 100 }], [pWin]);

  return (
    <div style={{ height: 200 }}>
      <ResponsiveContainer>
        <AreaChart data={data}>
          <XAxis dataKey="name" hide />
          <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} width={40} />
          <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
          <Area type="monotone" dataKey="value" stroke="#2563eb" fill="#93c5fd" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
