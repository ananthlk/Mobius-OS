"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import EligibilityChat from "@/components/eligibility_v2/EligibilityChat";
import EligibilitySidebar from "@/components/eligibility_v2/EligibilitySidebar";
import { useEligibilityAgent } from "@/hooks/useEligibilityAgent";

export default function EligibilityV2Page() {
    const { data: session } = useSession();
    const [caseId, setCaseId] = useState<string>("");
    const [sessionId, setSessionId] = useState<number | undefined>(undefined);
    const [isClient, setIsClient] = useState(false);
    
    // Initialize hook with a stable caseId (will be updated once client-side caseId is set)
    const { getCaseView, caseView } = useEligibilityAgent(caseId || "temp");

    // Generate caseId only on client side
    useEffect(() => {
        if (typeof window === "undefined") return; // SSR guard
        setIsClient(true);
        const storedCaseId = sessionStorage.getItem("eligibility_case_id");
        if (storedCaseId) {
            setCaseId(storedCaseId);
        } else {
            const newCaseId = `case_${Date.now()}`;
            setCaseId(newCaseId);
            sessionStorage.setItem("eligibility_case_id", newCaseId);
        }
    }, []);

    // Create or retrieve session
    useEffect(() => {
        if (typeof window === "undefined") return; // SSR guard
        if (!isClient || !session?.user?.email) return;

        const createSession = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const storedSessionId = sessionStorage.getItem("eligibility_session_id");
                
                if (storedSessionId) {
                    setSessionId(parseInt(storedSessionId));
                } else {
                    const response = await fetch(`${apiUrl}/api/eligibility-v2/session/start`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ user_id: session.user.email }),
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        setSessionId(data.session_id);
                        sessionStorage.setItem("eligibility_session_id", data.session_id.toString());
                    }
                }
            } catch (error) {
                console.error("Failed to create session:", error);
            }
        };

        createSession();
    }, [isClient, session?.user?.email]);

    // Load initial case view
    useEffect(() => {
        if (caseId && sessionId) {
            getCaseView(sessionId);
        }
    }, [caseId, sessionId, getCaseView]);

    // Refresh case view callback
    const refreshCaseView = useCallback(async () => {
        if (caseId && sessionId) {
            await getCaseView(sessionId);
        }
    }, [caseId, sessionId, getCaseView]);

    if (!isClient || !caseId) {
        return (
            <div className="flex items-center justify-center h-screen bg-[var(--bg-secondary)]">
                <div className="text-[var(--text-secondary)]">Loading...</div>
            </div>
        );
    }

    return (
        <div className="flex h-full bg-[var(--bg-secondary)] text-[var(--text-primary)] overflow-hidden font-sans">
            <div className="flex-1 flex p-6 gap-6 min-h-0">
                {/* Sidebar */}
                <div className="w-1/3 bg-[var(--bg-primary)] rounded-2xl shadow-[var(--shadow-md)] overflow-hidden">
                    <EligibilitySidebar caseId={caseId} sessionId={sessionId} caseView={caseView} />
                </div>
                
                {/* Main Chat Area */}
                <div className="flex-1 flex flex-col h-full min-w-0 bg-[var(--bg-primary)] rounded-2xl shadow-[var(--shadow-md)]">
                    {/* Header */}
                    <div className="h-20 border-b border-[var(--border-subtle)] flex items-center justify-between px-8 bg-[var(--bg-primary)]/80 backdrop-blur-xl z-20 sticky top-0">
                        <div className="flex flex-col gap-1">
                            <h1 className="text-xl font-semibold text-[var(--text-primary)] tracking-tight">
                                Eligibility Agent
                            </h1>
                        </div>
                    </div>
                    
                    {/* Chat Content */}
                    <div className="flex-1 overflow-hidden">
                        <EligibilityChat 
                            caseId={caseId} 
                            sessionId={sessionId}
                            onMessageSent={refreshCaseView}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
