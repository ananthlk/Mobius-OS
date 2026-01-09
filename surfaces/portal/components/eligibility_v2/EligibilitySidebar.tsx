"use client";

import { useState, useEffect } from "react";
import { useEligibilityAgent } from "@/hooks/useEligibilityAgent";

interface EligibilitySidebarProps {
    caseId: string;
    sessionId?: number;
    caseView?: any; // Pass caseView from parent to ensure it's always up-to-date
}

export default function EligibilitySidebar({ caseId, sessionId, caseView: propCaseView }: EligibilitySidebarProps) {
    const { caseView: hookCaseView, getCaseView } = useEligibilityAgent(caseId);
    const [loading, setLoading] = useState(true);
    
    // Use prop caseView if provided, otherwise use hook caseView
    const caseView = propCaseView || hookCaseView;

    useEffect(() => {
        if (caseId && sessionId && !propCaseView) {
            getCaseView(sessionId).finally(() => setLoading(false));
        } else if (propCaseView) {
            setLoading(false);
        }
    }, [caseId, sessionId, getCaseView, propCaseView]);

    if (loading) {
        return (
            <div className="h-full p-6 flex items-center justify-center">
                <div className="text-sm text-[var(--text-secondary)]">Loading...</div>
            </div>
        );
    }

    if (!caseView) {
        return (
            <div className="h-full p-6 flex items-center justify-center">
                <div className="text-sm text-[var(--text-secondary)]">No case data available</div>
            </div>
        );
    }

    const scoreState = caseView.score_state;
    const caseState = caseView.case_state || {};

    // Determine status indicator color
    let statusColor = "bg-gray-200";
    let statusText = "Unknown";
    if (scoreState) {
        const prob = scoreState.base_probability || 0;
        const conf = scoreState.base_confidence || 0;
        if (prob >= 0.8 && conf >= 0.7) {
            statusColor = "bg-green-500";
            statusText = "High Confidence";
        } else if (prob >= 0.6 && conf >= 0.5) {
            statusColor = "bg-yellow-500";
            statusText = "Moderate";
        } else {
            statusColor = "bg-red-500";
            statusText = "Low Confidence";
        }
    }

    return (
        <div className="h-full p-6 overflow-y-auto custom-scrollbar">
            {/* Case Progress */}
            <div className="mb-6">
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Case Progress</h3>
                <div className="text-xs">
                    <div className="mb-1">
                        <span className="font-medium text-[var(--text-primary)]">Status:</span>{" "}
                        <span className="text-[var(--text-secondary)]">{caseView.status || "INIT"}</span>
                    </div>
                </div>
            </div>

            {/* Payment Probability */}
            {scoreState && (
                <div className="mb-6 p-4 bg-[var(--bg-secondary)] rounded-[var(--radius-lg)] border border-[var(--border-subtle)]">
                    <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">
                        Payment Probability
                    </h3>
                    <div className="text-2xl font-bold mb-1 text-[var(--text-primary)]">
                        {(scoreState.base_probability * 100).toFixed(1)}%
                    </div>
                    {scoreState.probability_interval && (
                        <div className="text-xs text-[var(--text-secondary)] mb-2">
                            95% Confidence Interval:{" "}
                            {Math.round(scoreState.probability_interval.lower_bound * 100)}% -{" "}
                            {Math.round(scoreState.probability_interval.upper_bound * 100)}%
                        </div>
                    )}
                    <div className="text-xs text-[var(--text-secondary)]">
                        Confidence: {Math.round((scoreState.base_confidence || 0) * 100)}%
                        {scoreState.sample_size && (
                            <>
                                {" "}
                                | n={scoreState.sample_size}
                            </>
                        )}
                    </div>
                    {scoreState.volatility && (
                        <div className="text-xs text-[var(--text-secondary)] mt-1">
                            Volatility:{" "}
                            {scoreState.volatility.volatility_score < 0.3
                                ? "Low"
                                : scoreState.volatility.volatility_score < 0.7
                                ? "Moderate"
                                : "High"}
                        </div>
                    )}
                </div>
            )}

            {/* Status Indicator */}
            {scoreState && (
                <div className="mb-6 p-3 bg-[var(--bg-secondary)] rounded-[var(--radius-lg)] border border-[var(--border-subtle)]">
                    <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${statusColor}`}></div>
                        <span className="text-xs font-medium text-[var(--text-primary)]">{statusText}</span>
                    </div>
                </div>
            )}

            {/* Probability Waterfall */}
            {scoreState && scoreState.backoff_path && scoreState.backoff_path.length > 0 && (
                <div className="mb-6">
                    <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">
                        Probability Waterfall
                    </h3>
                    <div className="space-y-1 text-xs">
                        {scoreState.backoff_path.map((step: any, idx: number) => (
                            <div
                                key={idx}
                                className={`p-2 rounded-[var(--radius-md)] border ${
                                    step.level === scoreState.backoff_level
                                        ? "bg-[var(--primary-blue-light)] border-[var(--primary-blue)]/30"
                                        : "bg-[var(--bg-secondary)] border-[var(--border-subtle)]"
                                }`}
                            >
                                <div className="font-medium text-[var(--text-primary)]">
                                    Level {step.level}: {step.dimensions_str || "Global"}
                                </div>
                                <div className="text-[var(--text-secondary)]">
                                    n={step.sample_size}
                                    {step.probability !== null && step.probability !== undefined && (
                                        <>
                                            {" "}
                                            | {(step.probability * 100).toFixed(1)}%
                                        </>
                                    )}
                                    {step.ci_width && (
                                        <>
                                            {" "}
                                            | CI: {(step.ci_width * 100).toFixed(1)}%
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Visits/Appointments */}
            {caseState.timing?.related_visits &&
                caseState.timing.related_visits.length > 0 && (
                    <div className="mb-4">
                        <p className="text-sm font-semibold text-[var(--text-primary)] mb-2">
                            Appointments & Visits
                        </p>
                        <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                            {caseState.timing.related_visits.map((visit: any, idx: number) => (
                                <div
                                    key={idx}
                                    className="text-xs p-2 rounded-[var(--radius-md)] border bg-[var(--bg-secondary)] border-[var(--border-subtle)]"
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium">
                                            {visit.visit_date
                                                ? new Date(visit.visit_date).toLocaleDateString()
                                                : "Date TBD"}
                                        </span>
                                        {visit.event_tense && (
                                            <span
                                                className={`text-xs px-1.5 py-0.5 rounded ${
                                                    visit.event_tense === "PAST"
                                                        ? "bg-gray-200 text-gray-700"
                                                        : "bg-blue-100 text-blue-700"
                                                }`}
                                            >
                                                {visit.event_tense}
                                            </span>
                                        )}
                                    </div>
                                    {visit.eligibility_status && (
                                        <div className="mt-1">
                                            <span
                                                className={`text-xs font-medium ${
                                                    visit.eligibility_status === "YES"
                                                        ? "text-green-600"
                                                        : visit.eligibility_status === "NO"
                                                        ? "text-red-600"
                                                        : "text-gray-600"
                                                }`}
                                            >
                                                {visit.eligibility_status === "YES"
                                                    ? "✅ Eligible"
                                                    : visit.eligibility_status === "NO"
                                                    ? "❌ Not Eligible"
                                                    : "⏳ Unknown"}
                                            </span>
                                            {visit.eligibility_probability !== undefined &&
                                                visit.eligibility_probability !== null && (
                                                    <span className="ml-2 text-gray-600">
                                                        (
                                                        {Math.round(
                                                            visit.eligibility_probability * 100
                                                        )}
                                                        % probability)
                                                    </span>
                                                )}
                                        </div>
                                    )}
                                    {visit.visit_type && (
                                        <div className="text-gray-500 mt-1">{visit.visit_type}</div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

            {/* Next Questions */}
            {caseView.next_questions && caseView.next_questions.length > 0 && (
                <div className="mb-4">
                    <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Next Questions</h3>
                    <div className="space-y-2 text-xs">
                        {caseView.next_questions.map((q: any, idx: number) => (
                            <div key={idx} className="p-2 bg-[var(--primary-blue-light)] rounded-[var(--radius-md)] border border-[var(--primary-blue)]/20">
                                <div className="text-[var(--text-primary)]">{q.text || q.formatted_text}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
