interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: string;
}

export default function StatCard({ label, value, change, changeType = "neutral", icon }: StatCardProps) {
  const changeColor =
    changeType === "positive" ? "text-green-600" :
    changeType === "negative" ? "text-red-600" :
    "text-gray-500";

  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <span className="stat-label">{label}</span>
        {icon && (
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
          </svg>
        )}
      </div>
      <p className="stat-value">{value}</p>
      {change && <p className={`stat-change ${changeColor}`}>{change}</p>}
    </div>
  );
}
