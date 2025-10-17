interface Props {
  explain: Record<string, unknown>;
}

export function ShapDeltaBars({ explain }: Props) {
  const buckets = (explain?.buckets as Record<string, number>) || {};
  return (
    <div>
      <h2>Top Buckets</h2>
      <ul>
        {Object.entries(buckets).map(([bucket, value]) => (
          <li key={bucket}>
            {bucket}: {value.toFixed(3)}
          </li>
        ))}
      </ul>
    </div>
  );
}
