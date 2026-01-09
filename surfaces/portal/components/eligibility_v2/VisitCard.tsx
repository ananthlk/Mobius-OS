"use client";

import { Calendar, Clock } from "lucide-react";

interface VisitInfo {
    visit_id?: string | null;
    visit_date?: string | null;
    visit_type?: string | null;
    status?: string | null;
    provider?: string | null;
    location?: string | null;
    eligibility_status?: string | null;
    eligibility_probability?: number | null;
    event_tense?: string | null;
    score_state?: any;
}

interface VisitCardProps {
    visit: VisitInfo;
    onClick: () => void;
}

export default function VisitCard({ visit, onClick }: VisitCardProps) {
    const formatDate = (dateStr: string | null | undefined): string => {
        if (!dateStr) return "Date TBD";
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } catch {
            return dateStr;
        }
    };

    const getStatusColor = (status: string | null | undefined) => {
        if (status === "YES") return "text-green-600";
        if (status === "NO") return "text-red-600";
        return "text-gray-600";
    };

    const getStatusIcon = (status: string | null | undefined) => {
        if (status === "YES") return "✅";
        if (status === "NO") return "❌";
        return "⏳";
    };

    const getStatusText = (status: string | null | undefined) => {
        if (status === "YES") return "Eligible";
        if (status === "NO") return "Not Eligible";
        return "Unknown";
    };

    return (
        <button
            onClick={onClick}
            className="w-full text-left p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] hover:border-[var(--primary-blue)]/30 transition-all cursor-pointer group"
        >
            {/* Header: Date and Event Tense */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <Calendar size={12} className="text-[var(--text-secondary)]" />
                    <span className="font-semibold text-sm text-[var(--text-primary)]">
                        {formatDate(visit.visit_date)}
                    </span>
                </div>
                {visit.event_tense && (
                    <span
                        className={`text-xs px-2 py-0.5 rounded font-medium ${
                            visit.event_tense === "PAST"
                                ? "bg-gray-200 text-gray-700"
                                : "bg-blue-100 text-blue-700"
                        }`}
                    >
                        {visit.event_tense}
                    </span>
                )}
            </div>

            {/* Body: Visit Type and Status */}
            {visit.visit_type && (
                <div className="text-xs text-[var(--text-secondary)] mb-2">
                    {visit.visit_type}
                    {visit.status && (
                        <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-gray-100 text-gray-600">
                            {visit.status}
                        </span>
                    )}
                </div>
            )}

            {/* Eligibility Status and Probability */}
            <div className="flex items-center justify-between">
                {visit.eligibility_status && (
                    <span className={`text-xs font-medium ${getStatusColor(visit.eligibility_status)}`}>
                        {getStatusIcon(visit.eligibility_status)} {getStatusText(visit.eligibility_status)}
                    </span>
                )}
                {visit.eligibility_probability !== undefined &&
                    visit.eligibility_probability !== null && (
                        <span className="text-xs font-semibold text-[var(--text-primary)]">
                            {Math.round(visit.eligibility_probability * 100)}% probability
                        </span>
                    )}
            </div>

            {/* Footer: Click hint */}
            <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-secondary)] opacity-0 group-hover:opacity-100 transition-opacity">
                Click to view calculation details →
            </div>
        </button>
    );
}
