"use client";

interface BuildReuseDecisionProps {
    onDecision: (choice: "build_new" | "reuse") => void;
}

export default function BuildReuseDecision({ onDecision }: BuildReuseDecisionProps) {
    return (
        <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-gray-800">Choose Your Path</span>
            </div>
            
            <p className="text-sm text-gray-600">
                We've gathered all the information we need. Now let's build your workflow plan.
            </p>

            <div className="flex gap-3">
                <button
                    onClick={() => onDecision("build_new")}
                    className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-md"
                >
                    Build New
                </button>
                <button
                    onClick={() => onDecision("reuse")}
                    disabled
                    className="flex-1 bg-gray-300 text-gray-500 px-6 py-3 rounded-lg font-semibold cursor-not-allowed opacity-50"
                    title="Coming soon"
                >
                    Reuse from Repository
                </button>
            </div>

            <p className="text-xs text-gray-500 italic">
                Reuse from repository feature coming soon
            </p>
        </div>
    );
}




