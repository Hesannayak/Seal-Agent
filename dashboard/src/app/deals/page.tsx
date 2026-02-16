"use client";

import { useEffect, useState } from "react";
import type { Deal, DealStage } from "@/lib/types";
import * as api from "@/lib/api";

const STAGE_ORDER: DealStage[] = [
  "prospecting", "qualification", "discovery", "proposal", "negotiation", "closed_won", "closed_lost",
];

const STAGE_LABELS: Record<string, string> = {
  prospecting: "Prospecting",
  qualification: "Qualification",
  discovery: "Discovery",
  proposal: "Proposal",
  negotiation: "Negotiation",
  closed_won: "Closed Won",
  closed_lost: "Closed Lost",
};

const STAGE_COLORS: Record<string, string> = {
  prospecting: "border-t-gray-400",
  qualification: "border-t-blue-400",
  discovery: "border-t-indigo-400",
  proposal: "border-t-purple-400",
  negotiation: "border-t-yellow-400",
  closed_won: "border-t-green-500",
  closed_lost: "border-t-red-400",
};

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"board" | "list">("board");

  useEffect(() => {
    async function load() {
      try {
        const data = await api.deals.list();
        setDeals(data.deals || []);
      } catch {
        // Demo data
        setDeals([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const dealsByStage = STAGE_ORDER.reduce((acc, stage) => {
    acc[stage] = deals.filter((d) => d.stage === stage);
    return acc;
  }, {} as Record<DealStage, Deal[]>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Deals</h1>
          <p className="text-gray-500 mt-1">
            {deals.length} deal{deals.length !== 1 ? "s" : ""} in pipeline
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setView("board")}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                view === "board" ? "bg-white shadow text-gray-900" : "text-gray-500"
              }`}
            >
              Board
            </button>
            <button
              onClick={() => setView("list")}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                view === "list" ? "bg-white shadow text-gray-900" : "text-gray-500"
              }`}
            >
              List
            </button>
          </div>
        </div>
      </div>

      {view === "board" ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STAGE_ORDER.filter((s) => s !== "closed_lost").map((stage) => (
            <div key={stage} className="flex-shrink-0 w-72">
              <div className={`card border-t-4 ${STAGE_COLORS[stage]} p-4`}>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700">
                    {STAGE_LABELS[stage]}
                  </h3>
                  <span className="badge-gray">{dealsByStage[stage]?.length || 0}</span>
                </div>
                <div className="space-y-3">
                  {(dealsByStage[stage] || []).length === 0 ? (
                    <p className="text-xs text-gray-400 py-4 text-center">No deals</p>
                  ) : (
                    (dealsByStage[stage] || []).map((deal) => (
                      <div
                        key={deal.id}
                        className="bg-gray-50 rounded-lg p-3 border border-gray-100 hover:border-seal-300 transition-colors cursor-pointer"
                      >
                        <p className="font-medium text-sm text-gray-900 truncate">{deal.title}</p>
                        {deal.company && (
                          <p className="text-xs text-gray-500 mt-0.5">{deal.company}</p>
                        )}
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-sm font-semibold text-gray-900">
                            ${deal.value.toLocaleString()}
                          </span>
                          <span className="text-xs text-gray-400">
                            {Math.round(deal.probability * 100)}%
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-header">Deal</th>
                <th className="table-header">Company</th>
                <th className="table-header">Stage</th>
                <th className="table-header text-right">Value</th>
                <th className="table-header text-right">Probability</th>
                <th className="table-header">Close Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {deals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="table-cell text-center text-gray-400 py-12">
                    {loading ? "Loading deals..." : "No deals yet. Start prospecting to fill the pipeline."}
                  </td>
                </tr>
              ) : (
                deals.map((deal) => (
                  <tr key={deal.id} className="hover:bg-gray-50">
                    <td className="table-cell font-medium">{deal.title}</td>
                    <td className="table-cell text-gray-500">{deal.company || "—"}</td>
                    <td className="table-cell">
                      <span className={`badge ${
                        deal.stage === "closed_won" ? "badge-green" :
                        deal.stage === "closed_lost" ? "badge-red" :
                        "badge-blue"
                      }`}>
                        {STAGE_LABELS[deal.stage]}
                      </span>
                    </td>
                    <td className="table-cell text-right font-medium">
                      ${deal.value.toLocaleString()}
                    </td>
                    <td className="table-cell text-right">
                      {Math.round(deal.probability * 100)}%
                    </td>
                    <td className="table-cell text-gray-500">
                      {deal.expected_close_date ? new Date(deal.expected_close_date).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
