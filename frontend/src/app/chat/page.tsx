"use client";

import { useState } from "react";

export default function ChatPage() {
  const [messages, setMessages] = useState<
    Array<{ role: "user" | "assistant"; content: string }>
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: "user" as const, content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // TODO: Implement API call to chat endpoint
    setTimeout(() => {
      const assistantMessage = {
        role: "assistant" as const,
        content: "This is a placeholder response. Chat functionality coming soon!",
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 flex flex-col">
      <div className="container mx-auto px-4 py-8 flex-1 flex flex-col max-w-4xl">
        <h1 className="text-4xl font-bold text-amber-900 mb-8">
          Chat with Your Local Guide
        </h1>

        <div className="bg-white rounded-lg shadow-lg flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 mt-8">
                <p>Ask me anything about Bacolod!</p>
                <p className="text-sm mt-2">
                  I can help you discover places, plan itineraries, and share local insights.
                </p>
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-4 ${
                    msg.role === "user"
                      ? "bg-amber-600 text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-4">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="p-4 border-t">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about Bacolod..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading}
                className="bg-amber-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-amber-700 transition-colors disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

