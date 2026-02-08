"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { chatApi, WelcomeMessageResponse, isAuthenticated } from "@/lib/api";
import { WelcomeMessage } from "./WelcomeMessage";

interface ChatMessage {
  role: "user" | "assistant";
  type?: "text" | "welcome";
  content?: string;
  recommendations?: any;
  personality_summary?: string;
}

export default function MOGIChatbot() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [welcomeLoaded, setWelcomeLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load welcome message on mount - only if authenticated
    const loadWelcome = async () => {
      if (welcomeLoaded) return;
      
      // Check if user is authenticated before making API call
      if (!isAuthenticated()) {
        console.warn("User not authenticated, skipping welcome message load");
        setMessages([{
          role: "assistant",
          type: "text",
          content: "Please log in to get personalized recommendations!"
        }]);
        setWelcomeLoaded(true);
        return;
      }
      
      try {
        setLoading(true);
        const welcomeData = await chatApi.getWelcomeMessage();
        
        // Debug: Log what we received
        console.log("Welcome data received:", {
          hasContent: !!welcomeData.content,
          hasRecommendations: !!welcomeData.recommendations,
          recommendationCounts: welcomeData.recommendations ? {
            hotels: welcomeData.recommendations.hotels?.length || 0,
            restaurants: welcomeData.recommendations.restaurants?.length || 0,
            tourist_spots: welcomeData.recommendations.tourist_spots?.length || 0,
            secret_spots: welcomeData.recommendations.secret_spots?.length || 0,
            total: Object.values(welcomeData.recommendations || {}).reduce((sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0), 0)
          } : null,
          personality_summary: welcomeData.personality_summary
        });
        
        setMessages([{
          role: "assistant",
          type: "welcome",
          content: welcomeData.content,
          recommendations: welcomeData.recommendations || {
            hotels: [],
            restaurants: [],
            accommodations: [],
            tourist_spots: [],
            beaches: [],
            mountains: [],
            resorts: [],
            places_to_avoid: [],
            businesses: [],
            events: [],
            secret_spots: []
          },
          personality_summary: welcomeData.personality_summary || ""
        }]);
        
        setWelcomeLoaded(true);
      } catch (err: any) {
        console.error("Error loading welcome message:", err);
        
        // If it's an authentication error, redirect to login
        if (err?.status === 401 || err?.detail?.includes("credentials")) {
          setMessages([{
            role: "assistant",
            type: "text",
            content: "Your session has expired. Redirecting to login..."
          }]);
          // Redirect to login after showing message
          setTimeout(() => {
            router.push("/login");
          }, 2000);
        } else {
          // Set default welcome message for other errors
          setMessages([{
            role: "assistant",
            type: "text",
            content: "Kumusta! I'm MOGI, your friendly guide to Bacolod! 🎭 What would you like to explore today?"
          }]);
        }
        setWelcomeLoaded(true);
      } finally {
        setLoading(false);
      }
    };

    loadWelcome();
  }, [welcomeLoaded]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = { role: "user", type: "text", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await chatApi.sendMessage(input);
      const assistantMessage: ChatMessage = {
        role: "assistant",
        type: "text",
        content: response.response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error("Error sending message:", err);
      const errorMessage: ChatMessage = {
        role: "assistant",
        type: "text",
        content: "Sorry, I'm having trouble right now. Please try again later.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = (msg: ChatMessage, idx: number) => {
    if (msg.type === "welcome") {
      return (
        <div key={idx}>
          <WelcomeMessage
            content={msg.content || ""}
            recommendations={msg.recommendations || {
              hotels: [],
              restaurants: [],
              accommodations: [],
              tourist_spots: [],
              beaches: [],
              mountains: [],
              resorts: [],
              places_to_avoid: [],
              businesses: [],
              events: [],
              secret_spots: []
            }}
            personality_summary={msg.personality_summary || ""}
          />
        </div>
      );
    }

    return (
      <div
        key={idx}
        className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} mb-4`}
      >
        <div
          className={`max-w-[80%] rounded-lg p-4 ${
            msg.role === "user"
              ? "bg-amber-600 text-white"
              : "bg-gray-100 text-gray-800"
          }`}
        >
          {msg.role === "assistant" && (
            <div className="flex items-center gap-2 mb-2">
              <Image
                src="/Image2.png"
                alt="MOGI"
                width={24}
                height={24}
                className="rounded-full object-cover"
              />
              <span className="font-semibold text-sm">MOGI</span>
            </div>
          )}
          <div className="whitespace-pre-wrap">{msg.content}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 flex flex-col">
      <div className="container mx-auto px-4 py-8 flex-1 flex flex-col max-w-6xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-full overflow-hidden flex items-center justify-center bg-amber-400">
            <Image
              src="/Image2.png"
              alt="MOGI"
              width={48}
              height={48}
              className="w-full h-full object-cover"
            />
          </div>
          <h1 className="text-3xl font-bold text-amber-900">
            Chat with MOGI
          </h1>
        </div>

        <div className="bg-white rounded-lg shadow-lg flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 mt-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto mb-4"></div>
                <p>Loading your personalized recommendations...</p>
              </div>
            )}
            {messages.map((msg, idx) => renderMessage(msg, idx))}
            {loading && messages.length > 0 && (
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
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSend} className="p-4 border-t">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask MOGI about Bacolod..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-gray-900 placeholder:text-gray-500"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="bg-amber-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-amber-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
