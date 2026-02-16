interface FunnelStep {
  stage: string;
  count: number;
}

interface FunnelChartProps {
  steps: FunnelStep[];
}

const STAGE_LABELS: Record<string, string> = {
  new_leads: "New Leads",
  qualified: "Qualified",
  contacted: "Contacted",
  engaged: "Engaged",
  opportunity: "Opportunity",
  closed_won: "Won",
  closed_lost: "Lost",
};

export default function FunnelChart({ steps }: FunnelChartProps) {
  const max = Math.max(...steps.map((s) => s.count), 1);

  return (
    <div className="space-y-2">
      {steps.map((step, i) => {
        const width = Math.max((step.count / max) * 100, 8);
        const isLost = step.stage === "closed_lost";
        return (
          <div key={step.stage} className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-24 text-right flex-shrink-0">
              {STAGE_LABELS[step.stage] || step.stage}
            </span>
            <div className="flex-1 h-7 bg-gray-100 rounded relative">
              <div
                className={`h-full rounded transition-all ${
                  isLost ? "bg-red-400" : "bg-seal-500"
                }`}
                style={{ width: `${width}%` }}
              />
              <span className="absolute inset-0 flex items-center px-3 text-xs font-medium">
                {step.count}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
