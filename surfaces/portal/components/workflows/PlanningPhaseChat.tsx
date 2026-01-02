"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Bot, User } from "lucide-react";
import ThinkingContainer from "@/components/ThinkingContainer";
import Tooltip from "@/components/Tooltip";

interface Message {
    id: string;
    role: "system" | "user" | "thinking";
    content?: string;
    thinkingMessages?: string[];
    collapsed?: boolean;
    timestamp: number;
}

interface PlanningPhaseChatProps {
    sessionId?: number | null;
    onUpdate?: (data: any) => void;
}

export default function PlanningPhaseChat({ sessionId, onUpdate }: PlanningPhaseChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [currentThinkingId, setCurrentThinkingId] = useState<string | null>(null);
    const [expandedThinkingIds, setExpandedThinkingIds] = useState<Set<string>>(new Set());
    const [explicitlyCollapsedIds, setExplicitlyCollapsedIds] = useState<Set<string>>(new Set());
    const [userOverriddenIds, setUserOverriddenIds] = useState<Set<string>>(new Set());
    const scrollRef = useRef<HTMLDivElement>(null);

    // Polling effect similar to ShapingChat
    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (sessionId) {
            interval = setInterval(async () => {
                try {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                    const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}`);
                    const data = await res.json();

                    if (data.transcript && Array.isArray(data.transcript)) {
                        if (onUpdate) onUpdate(data);

                        // Update thinking container
                        if (data.latest_thought && currentThinkingId) {
                            setMessages(prev => prev.map(msg => {
                                if (msg.id === currentThinkingId && msg.role === "thinking" && !msg.collapsed) {
                                    const newMessages = data.latest_thought.messages || 
                                                      (data.latest_thought.message ? [data.latest_thought.message] : []);
                                    const existing = msg.thinkingMessages || [];
                                    const existingSet = new Set(existing);
                                    const uniqueNew = newMessages.filter((m: string) => !existingSet.has(m));
                                    
                                    if (uniqueNew.length > 0) {
                                        return {
                                            ...msg,
                                            thinkingMessages: [...existing, ...uniqueNew]
                                        };
                                    }
                                }
                                return msg;
                            }));
                        }

                        // Update transcript messages
                        setMessages(prev => {
                            const transcriptMsgs = data.transcript.map((t: any, idx: number) => ({
                                id: `poll_${idx}`,
                                role: t.role as "system" | "user",
                                content: t.content,
                                timestamp: t.timestamp === "now" ? Date.now() : t.timestamp
                            }));

                            const thinkingContainers = prev.filter(m => m.role === "thinking");
                            const regularMsgs = prev.filter(m => m.role !== "thinking");

                            // Match and merge
                            const result: Message[] = [];
                            const matchedLocalIndices = new Set<number>();

                            for (const transcriptMsg of transcriptMsgs) {
                                const matchingLocalIdx = regularMsgs.findIndex((localMsg, idx) => 
                                    !matchedLocalIndices.has(idx) &&
                                    localMsg.content === transcriptMsg.content &&
                                    localMsg.role === transcriptMsg.role
                                );
                                
                                if (matchingLocalIdx >= 0) {
                                    matchedLocalIndices.add(matchingLocalIdx);
                                    result.push(transcriptMsg);
                                } else {
                                    result.push(transcriptMsg);
                                }
                            }

                            // Add thinking containers
                            result.push(...thinkingContainers);
                            
                            return result;
                        });
                    }
                } catch (e) {
                    console.error("Polling failed", e);
                }
            }, 500);
        }
        return () => {
            if (interval) clearInterval(interval);
        };
    }, [currentThinkingId, sessionId, onUpdate]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: Message = { 
            id: Date.now().toString(), 
            role: "user", 
            content: input, 
            timestamp: Date.now() 
        };
        
        const thinkingId = `thinking_${Date.now()}`;
        const thinkingMsg: Message = {
            id: thinkingId,
            role: "thinking",
            thinkingMessages: ["Planning phase agent is thinking..."],
            collapsed: false,
            timestamp: Date.now()
        };

        setMessages(prev => [...prev, userMsg, thinkingMsg]);
        setCurrentThinkingId(thinkingId);
        setInput("");

        if (sessionId) {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: input, user_id: "user_123" }),
                });

                await res.json();
            } catch (e) {
                console.error("Chat failed", e);
                setMessages(prev => prev.filter(m => m.id !== thinkingId));
                setCurrentThinkingId(null);
            }
        }
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-2xl shadow-md border-2 border-gray-300 overflow-hidden relative">
            {/* Header */}
            <div className="p-4 border-b-2 border-gray-300 bg-gradient-to-b from-gray-50 to-white flex items-center gap-2 shadow-sm">
                <Tooltip content="Planning Phase Agent - Review and refine your workflow plan">
                    <Bot className="w-5 h-5 text-blue-600 cursor-help" />
                </Tooltip>
                <span className="text-sm font-bold text-gray-700 uppercase tracking-wider">Planning Phase</span>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
                {messages.map((msg) => {
                    if (msg.role === "thinking") {
                        const isStreaming = msg.collapsed !== true && msg.id === currentThinkingId && currentThinkingId !== null;
                        const isExpanded: boolean | undefined = expandedThinkingIds.has(msg.id) ? true : (
                            explicitlyCollapsedIds.has(msg.id) ? false : 
                            (msg.collapsed && !userOverriddenIds.has(msg.id) ? false : undefined)
                        );
                        
                        return (
                            <ThinkingContainer
                                key={msg.id}
                                message={{
                                    id: msg.id,
                                    thinkingMessages: msg.thinkingMessages || [],
                                    collapsed: msg.collapsed
                                }}
                                isExpanded={isExpanded}
                                onToggle={() => {
                                    if (expandedThinkingIds.has(msg.id)) {
                                        setExpandedThinkingIds(prev => {
                                            const newSet = new Set(prev);
                                            newSet.delete(msg.id);
                                            return newSet;
                                        });
                                        setExplicitlyCollapsedIds(prev => new Set(prev).add(msg.id));
                                        setUserOverriddenIds(prev => {
                                            const newSet = new Set(prev);
                                            newSet.delete(msg.id);
                                            return newSet;
                                        });
                                    } else {
                                        setExpandedThinkingIds(prev => new Set(prev).add(msg.id));
                                        setExplicitlyCollapsedIds(prev => {
                                            const newSet = new Set(prev);
                                            newSet.delete(msg.id);
                                            return newSet;
                                        });
                                        if (msg.collapsed) {
                                            setUserOverriddenIds(prev => new Set(prev).add(msg.id));
                                        }
                                    }
                                }}
                                isStreaming={isStreaming}
                            />
                        );
                    }

                    return (
                        <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === "system" ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"}`}>
                                {msg.role === "system" ? <Bot size={16} /> : <User size={16} />}
                            </div>
                            <div className={`max-w-[80%] rounded-2xl overflow-hidden ${msg.role === "system" ? "bg-blue-50 rounded-tl-none" : "bg-gray-100 rounded-tr-none"}`}>
                                <div className={`max-h-[400px] overflow-y-auto p-3 text-sm leading-relaxed text-[#1A1A1A] custom-scrollbar break-words`}>
                                    {msg.content && (
                                        <div className="break-words overflow-wrap-anywhere" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>') }} />
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Input Area */}
            <div className="p-4 border-t-2 border-gray-300 bg-white">
                <div className="relative">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="Ask questions or provide feedback..."
                        rows={1}
                        className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all pr-12 text-gray-800 placeholder-gray-400 resize-none overflow-hidden break-words"
                        style={{ minHeight: '44px', maxHeight: '120px' }}
                        onInput={(e) => {
                            const target = e.target as HTMLTextAreaElement;
                            target.style.height = 'auto';
                            target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                        }}
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

