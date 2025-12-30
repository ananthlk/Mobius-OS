"use client";

interface Solution {
    id: string;
    name: string;
    description: string;
    matchScore: number;
    completionRate: number;
    origin: "standard" | "ai" | "custom";
}

interface SolutionRailProps {
    solutions: Solution[];
    selectedId: string | null;
    onSelect: (solution: Solution) => void;
}

export default function SolutionRail({ solutions, selectedId, onSelect }: SolutionRailProps) {
    return (
        <div className="w-80 bg-[#F9FAFB] border-r border-[#E5E7EB] flex flex-col h-full z-20">
            <div className="p-6 border-b border-[#E5E7EB]">
                <h2 className="text-[#6B7280] font-medium text-xs tracking-[0.2em] mb-4">DIAGNOSTIC RESULTS</h2>
                <div className="text-xs text-[#9CA3AF] font-light">
                    Found {solutions.length} potential workflows based on your problem statement.
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {solutions.map((sol) => {
                    const isSelected = selectedId === sol.id;
                    return (
                        <div
                            key={sol.id}
                            onClick={() => onSelect(sol)}
                            className={`p-4 rounded-xl border cursor-pointer transition-all duration-300 relative overflow-hidden group ${isSelected
                                    ? "bg-white border-blue-200 shadow-lg ring-1 ring-blue-100"
                                    : "bg-white border-[#E5E7EB] hover:border-blue-200 hover:shadow-md"
                                }`}
                        >
                            {isSelected && <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500"></div>}

                            <div className="flex justify-between items-start mb-2">
                                {/* Badges: Pastel Backgrounds */}
                                <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold ${sol.origin === "standard" ? "bg-emerald-100 text-emerald-700" :
                                        sol.origin === "ai" ? "bg-purple-100 text-purple-700" :
                                            "bg-blue-100 text-blue-700"
                                    }`}>
                                    {sol.origin === "ai" ? "AI Synthesized" : sol.origin}
                                </span>
                                {/* Match Score: High contrast pill */}
                                <span className="text-[10px] font-bold bg-green-100 text-green-800 px-1.5 py-0.5 rounded-md">
                                    {sol.matchScore}%
                                </span>
                            </div>

                            <h3 className={`font-semibold text-sm mb-1 ${isSelected ? "text-blue-900" : "text-[#1A1A1A]"}`}>
                                {sol.name}
                            </h3>

                            <p className="text-xs text-[#6B7280] line-clamp-2 leading-relaxed mb-3">
                                {sol.description}
                            </p>

                            <div className="flex items-center gap-2">
                                <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                                        style={{ width: `${sol.completionRate}%` }}
                                    ></div>
                                </div>
                                <span className="text-[10px] text-[#9CA3AF] font-mono">{sol.completionRate}% Data</span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
