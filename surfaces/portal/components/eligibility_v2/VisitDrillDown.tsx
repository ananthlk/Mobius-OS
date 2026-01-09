"use client";

import { useState } from "react";
import { ChevronLeft, ChevronDown, ChevronRight, Calendar, Info } from "lucide-react";

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
    score_state?: {
        base_probability?: number;
        base_confidence?: number;
        base_probability_source?: string;
        state_probabilities?: {
            eligible?: number;
            not_eligible?: number;
            no_info?: number;
            unestablished?: number;
        };
        risk_probabilities?: Record<string, number>;
        calculation_explanation?: any;
        calculation_human_readable?: string;
    };
}

interface VisitDrillDownProps {
    visit: VisitInfo;
    onBack: () => void;
}

export default function VisitDrillDown({ visit, onBack }: VisitDrillDownProps) {
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

    const toggleSection = (section: string) => {
        setExpandedSections(prev => {
            const newSet = new Set(prev);
            if (newSet.has(section)) {
                newSet.delete(section);
            } else {
                newSet.add(section);
            }
            return newSet;
        });
    };

    const formatDate = (dateStr: string | null | undefined): string => {
        if (!dateStr) return "Date TBD";
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
                year: 'numeric'
            });
        } catch {
            return dateStr;
        }
    };

    const getStatusColor = (status: string | null | undefined) => {
        if (status === "YES") return "text-green-600 bg-green-50";
        if (status === "NO") return "text-red-600 bg-red-50";
        return "text-gray-600 bg-gray-50";
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

    const scoreState = visit.score_state;

    return (
        <div className="w-full">
            {/* Back Button */}
            <button
                onClick={onBack}
                className="mb-4 flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
                <ChevronLeft size={16} />
                <span>Back to Visits</span>
            </button>

            {/* Summary Section */}
            <div className="mb-4 p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)]">
                <div className="flex items-center gap-2 mb-3">
                    <Calendar size={16} className="text-[var(--text-secondary)]" />
                    <h3 className="font-semibold text-sm text-[var(--text-primary)]">Visit Summary</h3>
                </div>
                
                <div className="space-y-2 text-xs">
                    <div>
                        <span className="font-medium text-[var(--text-secondary)]">Date: </span>
                        <span className="text-[var(--text-primary)]">{formatDate(visit.visit_date)}</span>
                    </div>
                    
                    {visit.visit_type && (
                        <div>
                            <span className="font-medium text-[var(--text-secondary)]">Type: </span>
                            <span className="text-[var(--text-primary)]">{visit.visit_type}</span>
                        </div>
                    )}
                    
                    {visit.status && (
                        <div>
                            <span className="font-medium text-[var(--text-secondary)]">Status: </span>
                            <span className="text-[var(--text-primary)]">{visit.status}</span>
                        </div>
                    )}
                    
                    <div>
                        <span className="font-medium text-[var(--text-secondary)]">Eligibility: </span>
                        <span className={`px-2 py-1 rounded ${getStatusColor(visit.eligibility_status)}`}>
                            {getStatusIcon(visit.eligibility_status)} {getStatusText(visit.eligibility_status)}
                        </span>
                    </div>
                    
                    {visit.eligibility_probability !== undefined && visit.eligibility_probability !== null && (
                        <div>
                            <span className="font-medium text-[var(--text-secondary)]">Payment Probability: </span>
                            <span className="text-lg font-bold text-[var(--text-primary)]">
                                {Math.round(visit.eligibility_probability * 100)}%
                            </span>
                        </div>
                    )}
                    
                    {scoreState?.base_confidence !== undefined && (
                        <div>
                            <span className="font-medium text-[var(--text-secondary)]">Confidence: </span>
                            <span className="text-[var(--text-primary)]">
                                {Math.round((scoreState.base_confidence || 0) * 100)}%
                            </span>
                        </div>
                    )}
                    
                    {visit.event_tense && (
                        <div>
                            <span className="font-medium text-[var(--text-secondary)]">Time: </span>
                            <span className="text-[var(--text-primary)]">{visit.event_tense}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Calculation Details Section */}
            {scoreState && (
                <>
                    {/* Base Probability Source */}
                    {scoreState.base_probability_source && (
                        <div className="mb-3 p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)]">
                            <div className="flex items-center gap-2 mb-2">
                                <Info size={14} className="text-[var(--text-secondary)]" />
                                <span className="text-xs font-semibold text-[var(--text-primary)]">
                                    Probability Source
                                </span>
                            </div>
                            <div className="text-xs text-[var(--text-secondary)]">
                                {scoreState.base_probability_source === "direct_evidence"
                                    ? "Direct eligibility check performed"
                                    : "Historical propensity data used"}
                            </div>
                        </div>
                    )}

                    {/* State Probabilities */}
                    {scoreState.state_probabilities && (
                        <div className="mb-3">
                            <button
                                onClick={() => toggleSection("state_probabilities")}
                                className="w-full flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] hover:bg-[var(--bg-tertiary)] transition-colors"
                            >
                                <span className="text-xs font-semibold text-[var(--text-primary)]">
                                    State Probabilities
                                </span>
                                {expandedSections.has("state_probabilities") ? (
                                    <ChevronDown size={14} className="text-[var(--text-secondary)]" />
                                ) : (
                                    <ChevronRight size={14} className="text-[var(--text-secondary)]" />
                                )}
                            </button>
                            {expandedSections.has("state_probabilities") && (
                                <div className="mt-2 p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] space-y-1.5 text-xs">
                                    {scoreState.state_probabilities.eligible !== undefined && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--text-secondary)]">Eligible:</span>
                                            <span className="font-medium text-[var(--text-primary)]">
                                                {Math.round((scoreState.state_probabilities.eligible || 0) * 100)}%
                                            </span>
                                        </div>
                                    )}
                                    {scoreState.state_probabilities.not_eligible !== undefined && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--text-secondary)]">Not Eligible:</span>
                                            <span className="font-medium text-[var(--text-primary)]">
                                                {Math.round((scoreState.state_probabilities.not_eligible || 0) * 100)}%
                                            </span>
                                        </div>
                                    )}
                                    {scoreState.state_probabilities.no_info !== undefined && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--text-secondary)]">No Info:</span>
                                            <span className="font-medium text-[var(--text-primary)]">
                                                {Math.round((scoreState.state_probabilities.no_info || 0) * 100)}%
                                            </span>
                                        </div>
                                    )}
                                    {scoreState.state_probabilities.unestablished !== undefined && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--text-secondary)]">Unestablished:</span>
                                            <span className="font-medium text-[var(--text-primary)]">
                                                {Math.round((scoreState.state_probabilities.unestablished || 0) * 100)}%
                                            </span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Risk Probabilities */}
                    {scoreState.risk_probabilities && Object.keys(scoreState.risk_probabilities).length > 0 && (
                        <div className="mb-3">
                            <button
                                onClick={() => toggleSection("risk_probabilities")}
                                className="w-full flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] hover:bg-[var(--bg-tertiary)] transition-colors"
                            >
                                <span className="text-xs font-semibold text-[var(--text-primary)]">
                                    Risk Factors
                                </span>
                                {expandedSections.has("risk_probabilities") ? (
                                    <ChevronDown size={14} className="text-[var(--text-secondary)]" />
                                ) : (
                                    <ChevronRight size={14} className="text-[var(--text-secondary)]" />
                                )}
                            </button>
                            {expandedSections.has("risk_probabilities") && (
                                <div className="mt-2 p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] space-y-1.5 text-xs">
                                    {Object.entries(scoreState.risk_probabilities).map(([risk, prob]) => (
                                        <div key={risk} className="flex justify-between">
                                            <span className="text-[var(--text-secondary)] capitalize">
                                                {risk.replace(/_/g, " ")}:
                                            </span>
                                            <span className="font-medium text-[var(--text-primary)]">
                                                {Math.round((prob as number) * 100)}%
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Human-Readable Explanation */}
                    {scoreState.calculation_human_readable && (
                        <div className="mb-3">
                            <button
                                onClick={() => toggleSection("explanation")}
                                className="w-full flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] hover:bg-[var(--bg-tertiary)] transition-colors"
                            >
                                <span className="text-xs font-semibold text-[var(--text-primary)]">
                                    Calculation Explanation
                                </span>
                                {expandedSections.has("explanation") ? (
                                    <ChevronDown size={14} className="text-[var(--text-secondary)]" />
                                ) : (
                                    <ChevronRight size={14} className="text-[var(--text-secondary)]" />
                                )}
                            </button>
                            {expandedSections.has("explanation") && (
                                <div className="mt-2 p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
                                    {scoreState.calculation_human_readable}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Raw Data (for debugging) */}
                    <div className="mb-3">
                        <button
                            onClick={() => toggleSection("raw_data")}
                            className="w-full flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)] hover:bg-[var(--bg-tertiary)] transition-colors"
                        >
                            <span className="text-xs font-semibold text-[var(--text-primary)]">
                                Raw Score Data
                            </span>
                            {expandedSections.has("raw_data") ? (
                                <ChevronDown size={14} className="text-[var(--text-secondary)]" />
                            ) : (
                                <ChevronRight size={14} className="text-[var(--text-secondary)]" />
                            )}
                        </button>
                        {expandedSections.has("raw_data") && (
                            <div className="mt-2 p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)]">
                                <pre className="text-[10px] text-[var(--text-secondary)] overflow-x-auto">
                                    {JSON.stringify(scoreState, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                </>
            )}

            {/* No calculation details available */}
            {!scoreState && (
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-xs text-gray-600">
                    Calculation details not available for this visit.
                </div>
            )}
        </div>
    );
}
