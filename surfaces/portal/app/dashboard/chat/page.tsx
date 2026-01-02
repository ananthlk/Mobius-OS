"use client";

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Send, Bot, Search, Menu } from "lucide-react";

export default function ChatPage() {
    const { data: session } = useSession();
    const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async (e?: React.FormEvent | React.KeyboardEvent) => {
        if (e) e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { role: "user", content: input };
        const newHistory = [...messages, userMsg];
        setMessages(newHistory);
        const messageToSend = input;
        setInput("");
        setLoading(true);
        
        // Reset textarea height
        const textarea = document.querySelector('textarea');
        if (textarea) {
            textarea.style.height = 'auto';
        }

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/portal/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: session?.user?.email || "anonymous_wanderer",
                    messages: newHistory,
                    stream: false,
                }),
            });

            const data = await response.json();
            setMessages([...newHistory, { role: "assistant", content: data.content }]);
        } catch (error) {
            setMessages([...newHistory, { role: "system", content: "Nexus unreachable." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Header */}
            <header className="h-16 flex items-center justify-between px-6 border-b border-gray-100">
                <div className="flex items-center gap-2 text-[#5F6368]">
                    <Menu className="w-5 h-5 md:hidden" />
                    <span className="font-medium">Nexus v1</span>
                </div>
                <div className="flex gap-4">
                    <Search className="w-5 h-5 text-[#5F6368] cursor-pointer hover:text-black" />
                </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 md:p-10 space-y-8">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center -mt-10">
                        <div className="w-16 h-16 bg-white rounded-full shadow-lg flex items-center justify-center mb-6">
                            <Bot className="w-8 h-8 text-[#1a73e8]" />
                        </div>
                        <h2 className="text-2xl font-normal mb-2">How can I help you today?</h2>
                        <p className="text-[#5F6368] mb-8">I can draft care plans, search Medicaid codes, or summarize sessions.</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] md:max-w-[70%] rounded-[20px] px-6 py-4 text-[15px] leading-relaxed shadow-sm break-words overflow-wrap-anywhere ${msg.role === 'user'
                            ? 'bg-[#E8F0FE] text-[#1f1f1f] rounded-tr-none' // User: Light Blue (Google User style)
                            : 'bg-white border border-gray-100 text-[#1f1f1f] rounded-tl-none' // Assistant: White
                            }`}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start w-full">
                        <div className="bg-white border border-gray-100 rounded-[20px] rounded-tl-none px-6 py-4 shadow-sm flex gap-2">
                            <span className="w-2 h-2 bg-[#4285F4] rounded-full animate-bounce"></span>
                            <span className="w-2 h-2 bg-[#EA4335] rounded-full animate-bounce delay-100"></span>
                            <span className="w-2 h-2 bg-[#FBBC05] rounded-full animate-bounce delay-200"></span>
                        </div>
                    </div>
                )}
                <div ref={bottomRef}></div>
            </div>

            {/* Input Area */}
            <div className="p-4 md:p-6 w-full max-w-4xl mx-auto">
                <div className="bg-[#F0F4F8] rounded-full flex items-center px-2 py-2 focus-within:bg-white focus-within:shadow-md focus-within:ring-1 focus-within:ring-gray-200 transition-all">
                    <form onSubmit={sendMessage} className="flex-1 flex px-2">
                        <textarea
                            className="flex-1 bg-transparent border-none outline-none px-4 py-2 text-[#1f1f1f] placeholder-[#5F6368] resize-none overflow-hidden break-words"
                            placeholder="Ask Mobius a question..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            rows={1}
                            style={{ minHeight: '40px', maxHeight: '120px' }}
                            onInput={(e) => {
                                const target = e.target as HTMLTextAreaElement;
                                target.style.height = 'auto';
                                target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                            }}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    sendMessage(e);
                                }
                            }}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || loading}
                            className="w-10 h-10 flex items-center justify-center rounded-full text-[#1a73e8] hover:bg-blue-50 disabled:opacity-50 transition-colors"
                        >
                            <Send size={20} />
                        </button>
                    </form>
                </div>
                <div className="text-center mt-3 text-xs text-[#9aa0a6]">
                    Mobius can make mistakes. Verify critical clinical info.
                </div>
            </div>
        </>
    );
}
