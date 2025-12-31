"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Bot, User } from "lucide-react";

interface Message {
    id: string;
    role: "system" | "user";
    content: string;
    timestamp: number;
}

interface ShapingChatProps {
    initialQuery: string;
    onUpdate: (query: string) => void; // Callback to trigger re-diagnosis
    sessionId?: number | null;
}

export default function ShapingChat({ initialQuery, onUpdate, sessionId }: ShapingChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isThinking, setIsThinking] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Initial Load
    useEffect(() => {
        if (initialQuery && messages.length === 0) {
            // If we have a sessionId, we *should* fetch history. For now, we assume just started.
            const userMsg: Message = { id: "1", role: "user", content: initialQuery, timestamp: Date.now() };
            setMessages([userMsg]);

            // Mock System Reply for immediate feedback, but in reality backend handles this on /start
            // If the start endpoint returned a 'system_intro', we could show it.
            // For now, let's just simulate the first "thinking" if we haven't fetched history.
            setIsThinking(true);
            setTimeout(() => {
                setMessages(prev => [
                    ...prev,
                    {
                        id: "2",
                        role: "system",
                        content: `I've started session #${sessionId || '?'}. I'm analyzing '${initialQuery}'...`,
                        timestamp: Date.now()
                    }
                ]);
                setIsThinking(false);
            }, 1000);
        }
    }, [initialQuery, sessionId]);

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isThinking]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: Message = { id: Date.now().toString(), role: "user", content: input, timestamp: Date.now() };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setIsThinking(true);

        // Notify parent (for sidebar re-rank)
        onUpdate(input);

        // PERSISTENCE: Call Backend
        if (sessionId) {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: input, user_id: "user_123" }),
                });
                const data = await res.json();

                const sysMsg: Message = {
                    id: (Date.now() + 1).toString(),
                    role: "system",
                    content: data.reply,
                    timestamp: Date.now()
                };
                setMessages(prev => [...prev, sysMsg]);
            } catch (e) {
                console.error("Chat failed", e);
                // Fallback
            }
        } else {
            // Mock fallback if no session
            setTimeout(() => {
                const sysMsg: Message = {
                    id: (Date.now() + 1).toString(),
                    role: "system",
                    content: "Session ID missing, but I hear you. (Mock)",
                    timestamp: Date.now()
                };
                setMessages(prev => [...prev, sysMsg]);
            }, 1000);
        }

        setIsThinking(false);
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden relative">
            {/* Header */}
            <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center gap-2">
                <Bot className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Problem Shaping Agent</span>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === "system" ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"}`}>
                            {msg.role === "system" ? <Bot size={16} /> : <User size={16} />}
                        </div>
                        <div className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed ${msg.role === "system" ? "bg-blue-50 text-[#1A1A1A] rounded-tl-none" : "bg-gray-100 text-[#1A1A1A] rounded-tr-none"
                            }`}>
                            {msg.content}
                        </div>
                    </div>
                ))}

                {isThinking && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
                            <Bot size={16} />
                        </div>
                        <div className="bg-blue-50 p-3 rounded-2xl rounded-tl-none flex items-center gap-1">
                            <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"></div>
                            <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce delay-100"></div>
                            <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce delay-200"></div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-100 bg-white">
                <div className="relative">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        placeholder="Clarify the problem..."
                        className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all pr-12 text-gray-800 placeholder-gray-400"
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Send size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
}
