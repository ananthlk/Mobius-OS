"use client";

interface PhaseSummary {
    phase_id: string;
    name: string;
    step_count: number;
    description: string;
}

interface PlanOverviewProps {
    overviewText: string;
    phasesSummary: PhaseSummary[];
    totalSteps: number;
    expectedTimeline: string;
    expectedOutcomes: string[];
    allCardsOk: boolean;
    onApprove?: () => void;
    onReview?: () => void;
    onStartNew?: () => void;
    onSelectReview?: () => void;
    onCancel?: () => void;
}

export default function PlanOverview({
    overviewText,
    phasesSummary,
    totalSteps,
    expectedTimeline,
    expectedOutcomes,
    allCardsOk,
    onApprove,
    onReview,
    onStartNew,
    onSelectReview,
    onCancel
}: PlanOverviewProps) {
    return (
        <div className="bg-white border-2 border-gray-200 rounded-xl p-6 space-y-6">
            <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">📋 Workflow Plan Overview</h3>
                <p className="text-sm text-gray-600 whitespace-pre-line">{overviewText}</p>
            </div>

            {phasesSummary.length > 0 && (
                <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-gray-700">Phases:</h4>
                    {phasesSummary.map((phase) => (
                        <div key={phase.phase_id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="font-medium text-gray-800">{phase.name}</p>
                                    <p className="text-xs text-gray-500 mt-1">{phase.description}</p>
                                </div>
                                <span className="text-xs text-gray-400">
                                    {phase.step_count} step{phase.step_count !== 1 ? 's' : ''}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                <div>
                    <p className="text-xs text-gray-500">Total Steps</p>
                    <p className="text-lg font-semibold text-gray-800">{totalSteps}</p>
                </div>
                <div>
                    <p className="text-xs text-gray-500">Expected Timeline</p>
                    <p className="text-lg font-semibold text-gray-800">{expectedTimeline}</p>
                </div>
            </div>

            {expectedOutcomes.length > 0 && (
                <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Expected Outcomes:</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                        {expectedOutcomes.slice(0, 5).map((outcome, idx) => (
                            <li key={idx}>{outcome}</li>
                        ))}
                        {expectedOutcomes.length > 5 && (
                            <li className="text-gray-400 italic">...and {expectedOutcomes.length - 5} more</li>
                        )}
                    </ul>
                </div>
            )}

            {/* Conditional Action Buttons */}
            <div className="pt-4 border-t border-gray-200 space-y-3">
                {allCardsOk ? (
                    <>
                        <button
                            onClick={onApprove}
                            className="w-full bg-green-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-green-700 transition-colors shadow-md"
                        >
                            Approve Plan
                        </button>
                        <div className="flex gap-3">
                            <button
                                onClick={onReview}
                                className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                            >
                                Review & Edit Plan
                            </button>
                            <button
                                onClick={onStartNew}
                                className="flex-1 bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                            >
                                Start New Plan
                            </button>
                        </div>
                    </>
                ) : (
                    <>
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-3">
                            <p className="text-sm text-yellow-800">
                                ⚠️ Some steps need attention before approval.
                            </p>
                        </div>
                        <button
                            onClick={onSelectReview}
                            className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-md"
                        >
                            Select Plan to Review
                        </button>
                        <button
                            onClick={onCancel}
                            className="w-full bg-gray-200 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                        >
                            Cancel
                        </button>
                    </>
                )}
            </div>
        </div>
    );
}

