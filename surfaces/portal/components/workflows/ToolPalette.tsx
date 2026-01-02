"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface ToolSchema {
    name: string;
    description: string;
    parameters: Record<string, string>;
}

interface ToolPaletteProps {
    onSelectTool: (tool: ToolSchema) => void;
    collapsed?: boolean;
    onToggleCollapse?: () => void;
}

export default function ToolPalette({ 
    onSelectTool, 
    collapsed = false, 
    onToggleCollapse 
}: ToolPaletteProps) {
    const [tools, setTools] = useState<ToolSchema[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        fetch(`${apiUrl}/api/workflows/tools`)
            .then((res) => res.json())
            .then((data) => {
                setTools(data);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch tools", err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="relative flex h-full">
            {/* Collapse/Expand Button - Outside the panel, on the border */}
            {onToggleCollapse && (
                <button
                    onClick={onToggleCollapse}
                    className={`
                        absolute left-0 top-6 z-30 p-1.5 rounded-r-lg
                        bg-neutral-800 hover:bg-neutral-700 text-white/70 hover:text-white
                        border border-neutral-700 border-l-0 shadow-lg
                        transition-all duration-200
                        ${collapsed ? '-translate-x-full' : ''}
                    `}
                    title={collapsed ? "Show Toolkit" : "Hide Toolkit"}
                >
                    {collapsed ? (
                        <ChevronRight className="w-4 h-4" />
                    ) : (
                        <ChevronLeft className="w-4 h-4" />
                    )}
                </button>
            )}

            {/* Panel */}
            <div className={`
                bg-neutral-900/50 backdrop-blur-xl border-r border-white/5 
                p-6 flex flex-col h-full shadow-2xl z-20 transition-all duration-300
                ${collapsed ? 'w-0 p-0 opacity-0 overflow-hidden border-none' : 'w-72'}
            `}>
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-white/60 font-medium text-xs tracking-[0.2em]">TOOLKIT</h2>
                <div className="w-2 h-2 rounded-full bg-emerald-500/50 animate-pulse"></div>
            </div>

            {loading ? (
                <div className="flex flex-col gap-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-20 bg-white/5 rounded-xl animate-pulse"></div>
                    ))}
                </div>
            ) : (
                <div className="space-y-3 overflow-y-auto pr-2 custom-scrollbar">
                    {tools.map((tool) => (
                        <div
                            key={tool.name}
                            onClick={() => onSelectTool(tool)}
                            className="group relative p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/20 hover:bg-white/10 cursor-pointer transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/10 active:scale-[0.98]"
                        >
                            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 rounded-xl transition-opacity pointer-events-none"></div>

                            <div className="flex items-center justify-between mb-2">
                                <span className="text-white font-medium text-sm tracking-tight group-hover:text-purple-200 transition-colors">
                                    {tool.name}
                                </span>
                                <span className="w-5 h-5 flex items-center justify-center rounded-full bg-white/10 text-white/50 text-[10px] group-hover:bg-purple-500/20 group-hover:text-purple-300 transition-all">
                                    +
                                </span>
                            </div>
                            <p className="text-xs text-white/40 leading-relaxed line-clamp-2 font-light group-hover:text-white/60">
                                {tool.description}
                            </p>
                        </div>
                    ))}
                </div>
            )}
            </div>
        </div>
    );
}
