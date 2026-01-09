"use client";

import { useState, useEffect } from "react";
import { useEligibilityAgent } from "@/hooks/useEligibilityAgent";
import VisitCard from "./VisitCard";
import VisitDrillDown from "./VisitDrillDown";

interface EligibilitySidebarProps {
    caseId: string;
    sessionId?: number;
    caseView?: any; // Pass caseView from parent to ensure it's always up-to-date
}

export default function EligibilitySidebar({ caseId, sessionId, caseView: propCaseView }: EligibilitySidebarProps) {
    const { caseView: hookCaseView, getCaseView } = useEligibilityAgent(caseId);
    const [loading, setLoading] = useState(true);
    const [selectedVisit, setSelectedVisit] = useState<any>(null);
    
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
                    <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                            Payment Probability
                        </h3>
                        {caseState.timing?.related_visits && caseState.timing.related_visits.length > 0 && (
                            <span className="text-[10px] text-[var(--text-secondary)] bg-[var(--bg-tertiary)] px-1.5 py-0.5 rounded">
                                Weighted Average
                            </span>
                        )}
                    </div>
                    <div className="text-2xl font-bold mb-1 text-[var(--text-primary)]">
                        {(scoreState.base_probability * 100).toFixed(1)}%
                    </div>
                    {caseState.timing?.related_visits && caseState.timing.related_visits.length > 0 && (
                        <div className="text-xs text-[var(--text-secondary)] mb-2">
                            Based on {caseState.timing.related_visits.filter((v: any) => v.eligibility_probability !== null && v.eligibility_probability !== undefined).length} visit(s)
                            <br />
                            <span className="italic">Higher weight on more recent visits</span>
                        </div>
                    )}
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
                        {selectedVisit ? (
                            <VisitDrillDown
                                visit={selectedVisit}
                                onBack={() => setSelectedVisit(null)}
                            />
                        ) : (
                            <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
                                {caseState.timing.related_visits.map((visit: any, idx: number) => (
                                    <VisitCard
                                        key={visit.visit_id || idx}
                                        visit={visit}
                                        onClick={() => setSelectedVisit(visit)}
                                    />
                                ))}
                            </div>
                        )}
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
