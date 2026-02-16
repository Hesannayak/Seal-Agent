"use client";

import { useEffect, useState } from "react";
import type { Integration } from "@/lib/types";
import * as api from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  crm: "CRM",
  communication: "Communication",
  sales_tools: "Sales Tools",
  calendar: "Calendar",
  documents: "Documents",
};

const CATEGORY_ICONS: Record<string, string> = {
  crm: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  communication: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  sales_tools: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  calendar: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
  documents: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
};

export default function SettingsPage() {
  const [integrationsList, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiKey(localStorage.getItem("seal_api_key") || "");
    }
    async function load() {
      try {
        const data = await api.integrations.list();
        setIntegrations(data.integrations || []);
      } catch {
        setIntegrations([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function saveApiKey() {
    if (typeof window !== "undefined") {
      localStorage.setItem("seal_api_key", apiKey);
    }
  }

  const grouped = integrationsList.reduce((acc, int) => {
    (acc[int.category] = acc[int.category] || []).push(int);
    return acc;
  }, {} as Record<string, Integration[]>);

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure your agent and integrations</p>
      </div>

      {/* API Key */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">API Configuration</h2>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your Seal-Agent API key"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-seal-500 focus:border-seal-500 outline-none"
            />
          </div>
          <button onClick={saveApiKey} className="btn-primary">Save</button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          This key is stored in your browser and used for API authentication.
        </p>
      </div>

      {/* Integrations */}
      <div className="space-y-6">
        <h2 className="text-lg font-semibold">Integrations</h2>
        {loading ? (
          <p className="text-gray-400">Loading integrations...</p>
        ) : Object.keys(grouped).length === 0 ? (
          <div className="card text-center py-8">
            <p className="text-gray-400">No integrations found. Make sure the Seal-Agent API is running.</p>
          </div>
        ) : (
          Object.entries(grouped).map(([category, ints]) => (
            <div key={category}>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                {CATEGORY_LABELS[category] || category}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {ints.map((int) => (
                  <div
                    key={int.name}
                    className="card flex items-center gap-4 p-4"
                  >
                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={CATEGORY_ICONS[category] || CATEGORY_ICONS.crm} />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-gray-900 capitalize">
                        {int.name.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-gray-400 capitalize">{category}</p>
                    </div>
                    <span className={`flex-shrink-0 ${int.connected ? "badge-green" : "badge-gray"}`}>
                      {int.connected ? "Connected" : "Not connected"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Agent Skills */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Agent Skills</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            "Prospecting", "Outreach", "Deal Management", "Follow-Up", "Negotiation",
            "Research", "Proposal", "Scheduling", "Analytics", "Objection Handling",
          ].map((skill) => (
            <div key={skill} className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg">
              <span className="w-2 h-2 bg-green-400 rounded-full" />
              <span className="text-xs font-medium text-green-800">{skill}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
