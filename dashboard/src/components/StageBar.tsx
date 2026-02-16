interface StageBarProps {
  stages: Record<string, { count: number; value: number; pct_of_pipeline: number }>;
}

const STAGE_COLORS: Record<string, string> = {
  prospecting: "bg-gray-400",
  qualification: "bg-blue-400",
  discovery: "bg-indigo-400",
  proposal: "bg-purple-400",
  negotiation: "bg-yellow-400",
  closed_won: "bg-green-500",
  closed_lost: "bg-red-400",
};

const STAGE_LABELS: Record<string, string> = {
  prospecting: "Prospecting",
  qualification: "Qualification",
  discovery: "Discovery",
  proposal: "Proposal",
  negotiation: "Negotiation",
  closed_won: "Won",
  closed_lost: "Lost",
};

export default function StageBar({ stages }: StageBarProps) {
  const entries = Object.entries(stages).filter(([_, s]) => s.count > 0);
  const total = entries.reduce((sum, [_, s]) => sum + s.value, 0);

  return (
    <div>
      <div className="flex h-4 rounded-full overflow-hidden bg-gray-100">
        {entries.map(([name, data]) => (
          <div
            key={name}
            className={`${STAGE_COLORS[name] || "bg-gray-300"} transition-all`}
            style={{ width: `${total ? (data.value / total) * 100 : 0}%` }}
            title={`${STAGE_LABELS[name] || name}: $${data.value.toLocaleString()} (${data.count} deals)`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-4 mt-3">
        {entries.map(([name, data]) => (
          <div key={name} className="flex items-center gap-1.5 text-xs text-gray-600">
            <span className={`w-2.5 h-2.5 rounded-full ${STAGE_COLORS[name] || "bg-gray-300"}`} />
            <span>{STAGE_LABELS[name] || name}</span>
            <span className="font-medium text-gray-900">{data.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
