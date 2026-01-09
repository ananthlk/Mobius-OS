"use client";

import { useState, useEffect, useRef } from "react";
import { Send } from "lucide-react";
import { useEligibilityAgent } from "@/hooks/useEligibilityAgent";
import EligibilityProcessView from "./EligibilityProcessView";

interface Message {
    id: string;
    role: "user" | "assistant" | "process";
    content: string;
    next_questions?: any[];
    processEvents?: any[];
}

interface EligibilityChatProps {
    caseId: string;
    sessionId?: number;
    onMessageSent?: () => void;
}

export default function EligibilityChat({ caseId, sessionId, onMessageSent }: EligibilityChatProps) {
    const { submitMessage, loading } = useEligibilityAgent(caseId);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [processEvents, setProcessEvents] = useState<any[]>([]);
    const [isProcessExpanded, setIsProcessExpanded] = useState(true);
    const [hasCompletedProcess, setHasCompletedProcess] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    // Poll for process events
    useEffect(() => {
        if (!caseId || !sessionId) return;

        const pollProcessEvents = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const response = await fetch(
                    `${apiUrl}/api/eligibility-v2/cases/${caseId}/process-events`,
                    {
                        headers: {
                            "X-Session-ID": sessionId.toString(),
                        },
                    }
                );

                if (response.ok) {
                    const data = await response.json();
                    const newEvents = data.events || [];
                    setProcessEvents(newEvents);
                }
            } catch (error) {
                console.error("Failed to fetch process events:", error);
            }
        };

        // Poll every second when loading, or once when loading completes
        const interval = setInterval(pollProcessEvents, loading ? 1000 : 5000);
        pollProcessEvents(); // Initial fetch

        return () => clearInterval(interval);
    }, [caseId, sessionId, loading, hasCompletedProcess]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, processEvents]);

    // Auto-collapse process view when conversation completes
    useEffect(() => {
        if (!loading && processEvents.length > 0 && !hasCompletedProcess) {
            const conversationComplete = processEvents.some(
                (e: any) => e.phase === "conversation" && e.status === "complete"
            );
            if (conversationComplete) {
                setHasCompletedProcess(true);
                setIsProcessExpanded(false);
            }
        }
    }, [loading, processEvents, hasCompletedProcess]);

    const handleSend = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input,
        };

        setMessages((prev) => [...prev, userMessage]);
        const messageToSend = input;
        setInput("");
        setProcessEvents([]); // Clear previous process events
        setHasCompletedProcess(false); // Reset completion flag
        setIsProcessExpanded(true); // Re-expand for new process

        try {
            const result = await submitMessage(messageToSend, sessionId);

            // Add assistant response
            const assistantMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: result.presentation_summary || "Response received",
                next_questions: result.next_questions || [],
            };
            setMessages((prev) => [...prev, assistantMsg]);
            
            // Refresh parent's caseView
            if (onMessageSent) {
                onMessageSent();
            }
        } catch (error) {
            console.error("Error sending message:", error);
            setMessages((prev) => [
                ...prev,
                {
                    id: (Date.now() + 1).toString(),
                    role: "assistant",
                    content: "Sorry, I encountered an error. Please try again.",
                },
            ]);
        }
    };

    // Find the last user message index once
    let lastUserMessageIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === "user") {
            lastUserMessageIndex = i;
            break;
        }
    }

    return (
        <div className="flex flex-col h-full bg-[var(--bg-primary)]">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar space-y-4">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center -mt-10">
                        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
                            Eligibility Check
                        </h2>
                        <p className="text-sm text-[var(--text-secondary)] mb-8 max-w-md text-center">
                            Start by asking about a patient's eligibility. For example: "Check eligibility for MRN123"
                        </p>
                    </div>
                )}

                {messages.map((msg, index) => {
                    const isLastUserMessage = msg.role === "user" && index === lastUserMessageIndex;
                    const shouldShowProcessView = isLastUserMessage && (processEvents.length > 0 || loading);
                    
                    return (
                        <div key={msg.id}>
                            {msg.role === "process" && msg.processEvents ? (
                                <EligibilityProcessView
                                    events={msg.processEvents}
                                    isExpanded={isProcessExpanded}
                                    onToggle={() => setIsProcessExpanded(!isProcessExpanded)}
                                    isStreaming={loading}
                                />
                            ) : (
                                <>
                                    <div
                                        className={`flex w-full ${
                                            msg.role === "user" ? "justify-end" : "justify-start"
                                        }`}
                                    >
                                        <div
                                            className={`max-w-[80%] rounded-[20px] px-6 py-4 text-[15px] leading-relaxed shadow-sm break-words ${
                                                msg.role === "user"
                                                    ? "bg-[var(--accent-blue-soft)] text-[var(--text-primary)] rounded-tr-none"
                                                    : "bg-[var(--bg-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-tl-none"
                                            }`}
                                        >
                                            {msg.content}
                                        </div>
                                    </div>
                                    
                                    {/* Show process view inline after the last user message when processing */}
                                    {shouldShowProcessView && (
                                        <div className="mt-4">
                                            {processEvents.length > 0 ? (
                                                <EligibilityProcessView
                                                    events={processEvents}
                                                    isExpanded={isProcessExpanded}
                                                    onToggle={() => setIsProcessExpanded(!isProcessExpanded)}
                                                    isStreaming={loading}
                                                />
                                            ) : (
                                                <div className="flex justify-start w-full">
                                                    <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[20px] rounded-tl-none px-6 py-4 shadow-sm">
                                                        <div className="flex items-center gap-2 text-[var(--text-muted)] text-sm">
                                                            <span>Processing...</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    );
                })}

                {/* If no messages yet, show loading indicator */}
                {messages.length === 0 && loading && processEvents.length === 0 && (
                    <div className="flex justify-start w-full">
                        <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[20px] rounded-tl-none px-6 py-4 shadow-sm">
                            <div className="flex items-center gap-2 text-[var(--text-muted)] text-sm">
                                <span>Processing...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={bottomRef}></div>
            </div>

            {/* Input Area */}
            <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-primary)]/80 backdrop-blur-xl p-4">
                <form onSubmit={handleSend} className="flex gap-3 max-w-4xl mx-auto">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about patient eligibility..."
                        disabled={loading}
                        className="flex-1 px-4 py-3 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary-blue)]/20 focus:border-[var(--primary-blue)] transition-all"
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="bg-[var(--text-primary)] text-[var(--bg-primary)] px-6 py-3 rounded-[var(--radius-lg)] text-sm font-semibold hover:opacity-90 transition-colors shadow-[var(--shadow-md)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-4 h-4 border-2 border-[var(--bg-primary)] border-t-transparent rounded-full animate-spin"></div>
                                <span>Processing...</span>
                            </>
                        ) : (
                            <>
                                <Send size={16} />
                                <span>Send</span>
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
