"use client";

import { useEffect, useState } from "react";
import type { Prospect } from "@/lib/types";
import * as api from "@/lib/api";

const STATUS_BADGES: Record<string, string> = {
  new: "badge-blue",
  researching: "badge-yellow",
  qualified: "badge-green",
  contacted: "badge-blue",
  engaged: "badge-green",
  opportunity: "badge-green",
  customer: "badge-green",
  churned: "badge-red",
  disqualified: "badge-gray",
};

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    async function load() {
      try {
        const data = await api.prospects.list({ limit: 100 });
        setProspects(data.prospects || []);
      } catch {
        setProspects([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = prospects.filter((p) => {
    const matchSearch =
      !search ||
      `${p.first_name} ${p.last_name}`.toLowerCase().includes(search.toLowerCase()) ||
      (p.company || "").toLowerCase().includes(search.toLowerCase()) ||
      (p.email || "").toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Prospects</h1>
          <p className="text-gray-500 mt-1">
            {prospects.length} total prospect{prospects.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search by name, company, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-seal-500 focus:border-seal-500 outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-seal-500 outline-none"
        >
          <option value="all">All Statuses</option>
          <option value="new">New</option>
          <option value="qualified">Qualified</option>
          <option value="contacted">Contacted</option>
          <option value="engaged">Engaged</option>
          <option value="opportunity">Opportunity</option>
          <option value="customer">Customer</option>
          <option value="disqualified">Disqualified</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Name</th>
              <th className="table-header">Company</th>
              <th className="table-header">Title</th>
              <th className="table-header">Status</th>
              <th className="table-header text-right">Lead Score</th>
              <th className="table-header">Sentiment</th>
              <th className="table-header">Email</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="table-cell text-center text-gray-400 py-12">
                  Loading prospects...
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="table-cell text-center text-gray-400 py-12">
                  {search || statusFilter !== "all"
                    ? "No prospects match your filters"
                    : "No prospects yet. Import or add prospects to get started."}
                </td>
              </tr>
            ) : (
              filtered.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 cursor-pointer">
                  <td className="table-cell">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-seal-100 text-seal-700 rounded-full flex items-center justify-center text-xs font-bold">
                        {p.first_name[0]}{p.last_name[0]}
                      </div>
                      <span className="font-medium">
                        {p.first_name} {p.last_name}
                      </span>
                    </div>
                  </td>
                  <td className="table-cell text-gray-500">{p.company || "—"}</td>
                  <td className="table-cell text-gray-500">{p.title || "—"}</td>
                  <td className="table-cell">
                    <span className={STATUS_BADGES[p.status] || "badge-gray"}>
                      {p.status}
                    </span>
                  </td>
                  <td className="table-cell text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 bg-gray-100 rounded-full">
                        <div
                          className="h-full bg-seal-500 rounded-full"
                          style={{ width: `${Math.min(p.lead_score, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium w-8 text-right">{p.lead_score}</span>
                    </div>
                  </td>
                  <td className="table-cell">
                    <span className={`badge ${
                      p.sentiment === "positive" ? "badge-green" :
                      p.sentiment === "negative" ? "badge-red" : "badge-gray"
                    }`}>
                      {p.sentiment}
                    </span>
                  </td>
                  <td className="table-cell text-gray-500 text-xs">{p.email || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
