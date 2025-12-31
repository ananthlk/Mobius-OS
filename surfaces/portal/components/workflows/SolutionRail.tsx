"use client";

import { DiagnosticResult } from "./ProblemEntry";

interface SolutionRailProps {
    solutions: DiagnosticResult[];
    selectedId: string | null;
    onSelect: (solution: DiagnosticResult) => void;
}

export default function SolutionRail({ solutions, selectedId, onSelect }: SolutionRailProps) {
    return (
        <div className="w-80 bg-[#F9FAFB] border-r border-[#E5E7EB] flex flex-col h-full z-20">
            <div className="p-6 border-b border-[#E5E7EB]">
                <h2 className="text-[#6B7280] font-medium text-xs tracking-[0.2em] mb-4">WORKFLOWS MATCHING YOUR NEEDS</h2>
                <div className="text-xs text-[#9CA3AF] font-light">
                    Found {solutions.length} potential workflows based on your problem statement.
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {solutions.map((sol) => {
                    const isSelected = selectedId === sol.recipe_name;
                    // Format score as percentage
                    const scorePct = Math.round(sol.match_score * 100);

                    return (
                        <div
                            key={sol.recipe_name}
                            onClick={() => onSelect(sol)}
                            className={`p-4 rounded-xl border cursor-pointer transition-all duration-300 relative overflow-hidden group ${isSelected
                                ? "bg-white border-blue-200 shadow-lg ring-1 ring-blue-100"
                                : "bg-white border-[#E5E7EB] hover:border-blue-200 hover:shadow-md"
                                }`}
                        >
                            {isSelected && <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500"></div>}

                            <div className="flex justify-between items-start mb-2">
                                {/* Badges: Origin */}
                                <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold ${sol.origin === "standard" ? "bg-emerald-100 text-emerald-700" :
                                    sol.origin === "ai" ? "bg-purple-100 text-purple-700" :
                                        "bg-blue-100 text-blue-700"
                                    }`}>
                                    {sol.origin === "ai" ? "Synthesized" : "Standard"}
                                </span>
                                {/* Match Score */}
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${scorePct > 75 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                    {scorePct}% Fit
                                </span>
                            </div>

                            <h3 className={`font-semibold text-sm mb-1 ${isSelected ? "text-blue-900" : "text-[#1A1A1A]"}`}>
                                {sol.recipe_name}
                            </h3>

                            <p className="text-xs text-[#6B7280] line-clamp-2 leading-relaxed mb-3">
                                {sol.reasoning}
                            </p>

                            {/* Missing Info Badge */}
                            {sol.missing_info.length > 0 ? (
                                <div className="flex items-center gap-2 mt-2 bg-red-50 p-2 rounded-lg border border-red-100">
                                    <div className="w-4 h-4 rounded-full bg-red-200 flex items-center justify-center text-[10px] font-bold text-red-700">
                                        !
                                    </div>
                                    <span className="text-[10px] text-red-600 font-medium">
                                        Missing: {sol.missing_info.slice(0, 2).join(", ")}
                                        {sol.missing_info.length > 2 && "..."}
                                    </span>
                                </div>
                            ) : (
                                <div className="flex items-center gap-2 mt-2 bg-green-50 p-2 rounded-lg border border-green-100">
                                    <div className="w-4 h-4 rounded-full bg-green-200 flex items-center justify-center text-[10px] font-bold text-green-700">
                                        ✓
                                    </div>
                                    <span className="text-[10px] text-green-600 font-medium">Ready to run</span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
