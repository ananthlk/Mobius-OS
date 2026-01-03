"use client";

import { useState, useEffect } from "react";

// Matches backend DiagnosisResult
export interface DiagnosticResult {
    recipe_name: string;
    goal: string;
    match_score: number;
    missing_info: string[];
    reasoning: string;
    origin: "standard" | "ai" | "custom";
}

interface ProblemEntryProps {
    onDiagnose: (results: DiagnosticResult[], query: string, sessionId?: number) => void;
}

export default function ProblemEntry({ onDiagnose }: ProblemEntryProps) {
    const [query, setQuery] = useState("");
    // Default fallback list if API fails or no recent searches
    const [trendingIssues, setTrendingIssues] = useState<string[]>([
        "Compliance Audit",
        "User Onboarding",
        "Data Reconciliation",
        "Risk Assessment"
    ]);
    // Removed loading state - navigation is now immediate

    const handleDiagnose = async () => {
        if (!query.trim()) return;
        
        // IMMEDIATELY navigate to SELECTION view (optimistic navigation)
        // This allows the workflow builder screen to render while backend processes
        onDiagnose([], query); // Empty results initially, query passed for display
        
        // Make API call in background (non-blocking)
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/api/workflows/shaping/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, user_id: "user_123" }), // Mock user_id for now
            });
            const data = await res.json();

            // Debug logging
            console.log("Start shaping response:", data);
            console.log("Session ID from backend:", data.session_id);

            // Update with real results (triggers re-render with candidates)
            onDiagnose(data.candidates || [], query, data.session_id);

            // Trigger Sidebar Refresh
            window.dispatchEvent(new Event('refresh-sidebar'));
        } catch (e) {
            console.error("Diagnosis failed", e);
            // Keep query visible, results will be empty (can show error in workflow builder)
            // User is already on the workflow builder screen, so they can see the error state
            onDiagnose([], query);
        }
        // Note: No loading state needed since navigation is immediate
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && query.trim()) {
            handleDiagnose();
        }
    };

    // Fetch trending issues on component mount
    useEffect(() => {
        const fetchTrending = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/api/workflows/trending-issues?limit=4&days=7`);
                const data = await res.json();
                if (data.trending_issues?.length > 0) {
                    setTrendingIssues(data.trending_issues);
                }
            } catch (e) {
                console.error("Failed to fetch trending issues", e);
                // Keep default fallback
            }
        };
        fetchTrending();
    }, []);

    return (
        <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto animate-in fade-in zoom-in-95 duration-500 px-4">
            <h1 className="text-3xl font-light text-[#1A1A1A] mb-8 tracking-tight text-center">
                What problem <br />
                <span className="text-[#6B7280]">are we solving today?</span>
            </h1>

            {/* Container for Input and Trending - Aligned */}
            <div className="w-full space-y-6">
                {/* Main Input - Match chat page styling */}
                <div className="w-full relative group z-10">
                    <div className="bg-[#F0F4F8] rounded-full flex items-center px-2 py-2 focus-within:bg-white focus-within:shadow-md focus-within:ring-1 focus-within:ring-gray-200 transition-all">
                        <div className="pl-4 pr-2 text-[#5F6368]">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                        </div>
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            className="flex-1 bg-transparent border-none outline-none px-4 py-2 text-[#1f1f1f] placeholder-[#5F6368] focus:outline-none focus:ring-0 font-light"
                            placeholder="Ask Mobius a question..."
                            autoFocus
                        />
                        <button
                            onClick={() => query.trim() && handleDiagnose()}
                            disabled={!query.trim()}
                            className="w-10 h-10 flex items-center justify-center rounded-full text-[#1a73e8] hover:bg-blue-50 disabled:opacity-50 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                        </button>
                    </div>
                </div>

                {/* Trending Chips - Aligned with input width */}
                <div className="w-full flex flex-col items-center gap-3">
                    <span className="text-xs text-[#9CA3AF] uppercase tracking-widest font-semibold">Trending Issues</span>
                    <div className="flex flex-wrap justify-center gap-3 w-full">
                        {trendingIssues.map((s) => (
                            <button
                                key={s}
                                onClick={() => { setQuery(s); }}
                                className="px-4 py-1.5 rounded-full bg-white border border-[#E5E7EB] text-sm text-[#4B5563] hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all cursor-pointer shadow-sm"
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
