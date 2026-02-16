"use client";

import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import StageBar from "@/components/StageBar";
import type { PipelineSummary, ActivityMetrics, ForecastData } from "@/lib/types";
import * as api from "@/lib/api";

export default function DashboardPage() {
  const [pipeline, setPipeline] = useState<PipelineSummary | null>(null);
  const [activity, setActivity] = useState<ActivityMetrics | null>(null);
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [p, a, f] = await Promise.allSettled([
          api.analytics.pipeline(),
          api.analytics.activity(30),
          api.analytics.forecast(),
        ]);
        if (p.status === "fulfilled") setPipeline(p.value);
        if (a.status === "fulfilled") setActivity(a.value);
        if (f.status === "fulfilled") setForecast(f.value);
      } catch {
        // API may not be running
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your sales pipeline and activity</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Pipeline Value"
          value={pipeline ? `$${pipeline.total_pipeline_value.toLocaleString()}` : "--"}
          icon="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
        <StatCard
          label="Active Deals"
          value={pipeline?.total_deals ?? "--"}
          icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
        />
        <StatCard
          label="Forecast (Weighted)"
          value={forecast ? `$${forecast.forecast.expected.toLocaleString()}` : "--"}
          change={forecast ? `${forecast.confidence} confidence` : undefined}
          changeType={forecast?.confidence === "high" ? "positive" : "neutral"}
          icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
        />
        <StatCard
          label="Reply Rate"
          value={activity ? `${activity.reply_rate}%` : "--"}
          change={activity ? `${activity.outbound_count} outbound` : undefined}
          changeType={activity && activity.reply_rate > 20 ? "positive" : "neutral"}
          icon="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </div>

      {/* Pipeline Stages */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Pipeline Stages</h2>
        {pipeline?.stages ? (
          <StageBar stages={pipeline.stages} />
        ) : (
          <p className="text-gray-400 text-sm">
            {loading ? "Loading pipeline data..." : "Connect to the Seal-Agent API to see pipeline data"}
          </p>
        )}
      </div>

      {/* Activity + Forecast Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Summary */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Activity (Last 30 Days)</h2>
          {activity ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Total Interactions</p>
                  <p className="text-xl font-bold">{activity.total_interactions}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Daily Average</p>
                  <p className="text-xl font-bold">{activity.daily_average}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Open Rate</p>
                  <p className="text-xl font-bold">{activity.open_rate}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Reply Rate</p>
                  <p className="text-xl font-bold">{activity.reply_rate}%</p>
                </div>
              </div>
              {Object.keys(activity.by_channel).length > 0 && (
                <div>
                  <p className="text-sm text-gray-500 mb-2">By Channel</p>
                  <div className="flex gap-3">
                    {Object.entries(activity.by_channel).map(([ch, count]) => (
                      <span key={ch} className="badge-blue">{ch}: {count}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">
              {loading ? "Loading..." : "No activity data available"}
            </p>
          )}
        </div>

        {/* Forecast */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Sales Forecast</h2>
          {forecast ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Best Case</p>
                  <p className="text-lg font-bold text-green-600">
                    ${forecast.forecast.best_case.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Expected</p>
                  <p className="text-lg font-bold text-seal-600">
                    ${forecast.forecast.expected.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Worst Case</p>
                  <p className="text-lg font-bold text-red-600">
                    ${forecast.forecast.worst_case.toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`badge ${
                  forecast.confidence === "high" ? "badge-green" :
                  forecast.confidence === "medium" ? "badge-yellow" : "badge-red"
                }`}>
                  {forecast.confidence_percentage}% confidence
                </span>
                <span className="text-sm text-gray-500">
                  {forecast.forecast.deal_count} deals in pipeline
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">
              {loading ? "Loading..." : "No forecast data available"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
