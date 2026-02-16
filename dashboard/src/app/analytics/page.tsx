"use client";

import { useEffect, useState } from "react";
import StatCard from "@/components/StatCard";
import FunnelChart from "@/components/FunnelChart";
import type { PerformanceReport } from "@/lib/types";
import * as api from "@/lib/api";

export default function AnalyticsPage() {
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await api.analytics.report(period);
        setReport(data);
      } catch {
        setReport(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [period]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Sales performance and insights</p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-seal-500 outline-none"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Overall Score */}
      {report && (
        <div className="card flex items-center gap-8">
          <div className="flex-shrink-0">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold text-white ${
              report.grade === "A" ? "bg-green-500" :
              report.grade === "B" ? "bg-blue-500" :
              report.grade === "C" ? "bg-yellow-500" : "bg-red-500"
            }`}>
              {report.grade}
            </div>
          </div>
          <div>
            <h2 className="text-lg font-semibold">Overall Performance Score</h2>
            <p className="text-3xl font-bold text-gray-900">{report.overall_score}/100</p>
            <div className="flex gap-4 mt-2">
              {Object.entries(report.scores || {}).map(([key, val]) => (
                <span key={key} className="text-xs text-gray-500">
                  {key.replace("_", " ")}: <span className="font-medium text-gray-700">{val}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Interactions"
          value={report?.activity?.total_interactions ?? "--"}
        />
        <StatCard
          label="Reply Rate"
          value={report?.activity ? `${report.activity.reply_rate}%` : "--"}
          changeType={report?.activity && report.activity.reply_rate > 20 ? "positive" : "neutral"}
        />
        <StatCard
          label="Win Rate"
          value={report?.funnel ? `${report.funnel.win_rate}%` : "--"}
          changeType={report?.funnel && report.funnel.win_rate > 30 ? "positive" : "neutral"}
        />
        <StatCard
          label="Avg Deal Size"
          value={report?.pipeline ? `$${report.pipeline.average_deal_size.toLocaleString()}` : "--"}
        />
      </div>

      {/* Funnel + Channel Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Conversion Funnel</h2>
          {report?.funnel?.funnel ? (
            <FunnelChart steps={report.funnel.funnel} />
          ) : (
            <p className="text-gray-400 text-sm">
              {loading ? "Loading..." : "No funnel data available"}
            </p>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Channel Breakdown</h2>
          {report?.activity?.by_channel && Object.keys(report.activity.by_channel).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(report.activity.by_channel).map(([channel, count]) => {
                const total = report.activity?.total_interactions || 1;
                const pct = Math.round(((count as number) / total) * 100);
                return (
                  <div key={channel}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="capitalize text-gray-700">{channel}</span>
                      <span className="text-gray-500">{count as number} ({pct}%)</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full">
                      <div
                        className="h-full bg-seal-500 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">
              {loading ? "Loading..." : "No channel data available"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
