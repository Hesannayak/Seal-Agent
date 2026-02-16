"use client";

import { useState } from "react";
import * as api from "@/lib/api";

export default function ConversationsPage() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string; time: string }[]>([]);
  const [sending, setSending] = useState(false);

  async function handleSend() {
    if (!message.trim() || sending) return;

    const userMsg = {
      role: "user",
      content: message,
      time: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setMessage("");
    setSending(true);

    try {
      const res = await api.agent.chat(message);
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content: res.response || res.message || JSON.stringify(res),
          time: new Date().toLocaleTimeString(),
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: `Error: ${err.message || "Could not reach agent"}`,
          time: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Agent Chat</h1>
        <p className="text-gray-500 mt-1">Talk to your AI sales agent</p>
      </div>

      {/* Messages */}
      <div className="flex-1 card overflow-y-auto mb-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-seal-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-seal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-700">Start a conversation</h3>
            <p className="text-sm text-gray-400 mt-1">
              Ask the agent to research a prospect, compose an email, analyze your pipeline, or anything sales-related.
            </p>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {[
                "Show my pipeline summary",
                "Who needs a follow-up?",
                "Compose a cold email for a VP of Sales",
                "What deals are at risk?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => { setMessage(suggestion); }}
                  className="btn-secondary text-xs"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-seal-600 text-white"
                  : msg.role === "system"
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              <p className={`text-xs mt-1 ${
                msg.role === "user" ? "text-seal-200" : "text-gray-400"
              }`}>
                {msg.time}
              </p>
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: "0ms"}} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: "150ms"}} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: "300ms"}} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask the agent anything..."
          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-seal-500 focus:border-seal-500 outline-none"
          disabled={sending}
        />
        <button onClick={handleSend} disabled={sending || !message.trim()} className="btn-primary px-6">
          Send
        </button>
      </div>
    </div>
  );
}
