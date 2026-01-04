"use client";

interface PlanningStagesProps {
    stage: "approve" | "review" | "cancel";
    approveData?: {
        message: string;
        overview?: any;
    };
    reviewData?: {
        step: any;
        phase: any;
        issue: any;
        message: string;
    };
    cancelData?: {
        message: string;
        redirectTo?: string;
    };
    onExecute?: () => void;
    onSaveDraft?: () => void;
    onEditStep?: (stepId: string) => void;
    onReturn?: () => void;
}

export default function PlanningStages({
    stage,
    approveData,
    reviewData,
    cancelData,
    onExecute,
    onSaveDraft,
    onEditStep,
    onReturn
}: PlanningStagesProps) {
    if (stage === "approve") {
        return (
            <div className="bg-green-50 border-2 border-green-200 rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">✅</span>
                    <h3 className="text-lg font-semibold text-gray-800">Plan Approved</h3>
                </div>
                
                <p className="text-sm text-gray-600">{approveData?.message || "Plan approved successfully!"}</p>

                {approveData?.overview && (
                    <div className="bg-white rounded-lg p-4 border border-green-200">
                        <p className="text-xs text-gray-500 mb-2">Summary:</p>
                        <p className="text-sm text-gray-700">
                            {approveData.overview.total_steps} steps across {approveData.overview.phases_summary?.length || 0} phases
                        </p>
                    </div>
                )}

                <div className="flex gap-3 pt-4">
                    <button
                        onClick={onExecute}
                        className="flex-1 bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition-colors shadow-md"
                    >
                        Execute Workflow
                    </button>
                    <button
                        onClick={onSaveDraft}
                        className="flex-1 bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                    >
                        Save as Draft
                    </button>
                </div>
            </div>
        );
    }

    if (stage === "review") {
        return (
            <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">🔍</span>
                    <h3 className="text-lg font-semibold text-gray-800">Reviewing Plan</h3>
                </div>

                <p className="text-sm text-gray-600">{reviewData?.message || "Reviewing step..."}</p>

                {reviewData?.step && (
                    <div className="bg-white rounded-lg p-4 border border-blue-200 space-y-3">
                        <div>
                            <p className="text-sm font-semibold text-gray-800">Step:</p>
                            <p className="text-sm text-gray-600">{reviewData.step.description || reviewData.step.id}</p>
                        </div>

                        {reviewData.issue && (
                            <div className={`p-3 rounded-lg ${reviewData.issue.issue_type === "missing_info" ? "bg-red-50 border border-red-200" : "bg-yellow-50 border border-yellow-200"}`}>
                                <p className="text-xs font-semibold text-gray-700 mb-1">Issue:</p>
                                <p className="text-xs text-gray-600">{reviewData.issue.description}</p>
                                {reviewData.issue.missing_fields && reviewData.issue.missing_fields.length > 0 && (
                                    <p className="text-xs text-red-600 mt-2">
                                        Missing: {reviewData.issue.missing_fields.join(", ")}
                                    </p>
                                )}
                            </div>
                        )}

                        <button
                            onClick={() => onEditStep?.(reviewData.step.id)}
                            className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
                        >
                            Edit Step
                        </button>
                    </div>
                )}

                <button
                    onClick={onReturn}
                    className="w-full bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                >
                    Return to Overview
                </button>
            </div>
        );
    }

    if (stage === "cancel") {
        return (
            <div className="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">⚠️</span>
                    <h3 className="text-lg font-semibold text-gray-800">Planning Phase Cancelled</h3>
                </div>

                <p className="text-sm text-gray-600">{cancelData?.message || "Planning phase cancelled."}</p>

                <div className="bg-white rounded-lg p-4 border border-yellow-200">
                    <p className="text-xs text-gray-500 mb-2">Returning to Gate Phase...</p>
                </div>

                <button
                    onClick={onReturn}
                    className="w-full bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                >
                    Return to Gate Phase
                </button>
            </div>
        );
    }

    return null;
}


