"use client";

import { useState } from "react";

interface ProblemEntryProps {
    onSearch: (query: string) => void;
}

export default function ProblemEntry({ onSearch }: ProblemEntryProps) {
    const [query, setQuery] = useState("");

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && query.trim()) {
            onSearch(query);
        }
    };

    const suggestions = [
        "Compliance Audit",
        "User Onboarding",
        "Data Reconciliation",
        "Risk Assessment"
    ];

    return (
        <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <h1 className="text-3xl font-light text-[#1A1A1A] mb-8 tracking-tight text-center">
                What problem <br />
                <span className="text-[#6B7280]">are we solving today?</span>
            </h1>

            {/* Main Input - Light Theme */}
            <div className="w-full relative group z-10">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
                <div className="relative bg-white border border-[#E5E7EB] rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] flex items-center p-2 transition-all group-hover:border-blue-400/30 group-hover:shadow-[0_8px_30px_rgba(0,0,0,0.08)]">
                    <div className="pl-4 pr-3 text-[#9CA3AF]">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                    </div>
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="flex-1 bg-transparent border-none text-lg text-[#1A1A1A] placeholder-[#9CA3AF] focus:outline-none focus:ring-0 py-3 font-light"
                        placeholder="e.g. Patient intake errors..."
                        autoFocus
                    />
                    <button
                        onClick={() => query.trim() && onSearch(query)}
                        className="bg-[#F3F4F6] hover:bg-[#E5E7EB] text-[#4B5563] rounded-xl px-4 py-2 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                    </button>
                </div>
            </div>

            {/* Trending Chips - Light Theme */}
            <div className="mt-8 flex flex-wrap justify-center gap-3">
                <span className="text-xs text-[#9CA3AF] uppercase tracking-widest font-semibold w-full text-center mb-1">Trending Issues</span>
                {suggestions.map((s) => (
                    <button
                        key={s}
                        onClick={() => onSearch(s)}
                        className="px-4 py-1.5 rounded-full bg-white border border-[#E5E7EB] text-sm text-[#4B5563] hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all cursor-pointer shadow-sm"
                    >
                        {s}
                    </button>
                ))}
            </div>
        </div>
    );
}
