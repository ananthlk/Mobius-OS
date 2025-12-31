"use client";

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Send, Bot, Check, Plus, Search, Menu, MessageSquare, GitBranch, Database, Settings } from "lucide-react";

export default function Dashboard() {
    const { data: session } = useSession();
    const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { role: "user", content: input };
        const newHistory = [...messages, userMsg];
        setMessages(newHistory);
        setInput("");
        setLoading(true);

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
        <div className="flex h-screen bg-[#F8F9FA] font-sans text-[#202124]">

            {/* Sidebar (Navigation Rail) */}
            <aside className="w-[280px] bg-[#F0F4F8] p-4 flex flex-col hidden md:flex rounded-r-2xl m-2 ml-0">
                <div className="flex items-center gap-3 px-4 mb-8 mt-2">
                    <div className="w-8 h-8 rounded-full border-[3px] border-l-[#4285F4] border-t-[#EA4335] border-r-[#FBBC05] border-b-[#34A853]"></div>
                    <span className="font-semibold text-xl text-[#5F6368]">Mobius</span>
                </div>

                {/* Modules Section */}
                <div className="px-4 py-2 text-xs font-semibold text-[#5F6368] uppercase tracking-wider mb-2">Modules</div>
                <nav className="space-y-1 mb-8">
                    <div onClick={() => window.location.reload()} className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer text-[#444746] hover:bg-white transition-colors">
                        <MessageSquare className="w-5 h-5 text-[#1a73e8]" />
                        <span className="text-sm font-medium">Chat</span>
                    </div>
                    <a href="/dashboard/workflows/new" className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer text-[#444746] hover:bg-white transition-colors">
                        <GitBranch className="w-5 h-5 text-purple-600" />
                        <span className="text-sm font-medium">Workflows</span>
                    </a>
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer text-[#444746]/60 hover:bg-white transition-colors" title="Coming Soon">
                        <Database className="w-5 h-5" />
                        <span className="text-sm font-medium">Knowledge</span>
                    </div>
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer text-[#444746]/60 hover:bg-white transition-colors" title="Coming Soon">
                        <Settings className="w-5 h-5" />
                        <span className="text-sm font-medium">Admin</span>
                    </div>
                </nav>

                <div className="px-4 py-2 text-xs font-semibold text-[#5F6368] uppercase tracking-wider mb-2">Recent Activity</div>
                <nav className="flex-1 space-y-1 overflow-y-auto">
                    <SidebarItem label="Patient Intake: John Doe" active />
                    <SidebarItem label="Billing Inquiry #402" />
                    <SidebarItem label="Crisis Protocol Review" />
                </nav>

                <div className="mt-auto flex items-center gap-3 px-2 py-3 hover:bg-white rounded-xl cursor-pointer transition-colors">
                    {session?.user?.image ? (
                        <img src={session.user.image} className="w-8 h-8 rounded-full" />
                    ) : (
                        <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold">
                            {session?.user?.name?.[0] || "U"}
                        </div>
                    )}
                    <div className="text-sm font-medium overflow-hidden text-ellipsis whitespace-nowrap max-w-[140px]">
                        {session?.user?.email}
                    </div>
                </div>
            </aside>

            {/* Main Area */}
            <main className="flex-1 flex flex-col relative bg-white m-2 rounded-2xl shadow-sm border border-gray-100 overflow-hidden">

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
                            <div className={`max-w-[80%] md:max-w-[70%] rounded-[20px] px-6 py-4 text-[15px] leading-relaxed shadow-sm ${msg.role === 'user'
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
                            <input
                                className="flex-1 bg-transparent border-none outline-none px-4 py-2 text-[#1f1f1f] placeholder-[#5F6368]"
                                placeholder="Ask Mobius a question..."
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
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

            </main>
        </div>
    );
}

function SidebarItem({ label, active = false }: { label: string, active?: boolean }) {
    return (
        <div className={`px-4 py-3 rounded-full cursor-pointer text-sm font-medium transition-colors ${active ? 'bg-[#E8F0FE] text-[#1967D2]' : 'text-[#444746] hover:bg-gray-100'}`}>
            {label}
        </div>
    )
}
