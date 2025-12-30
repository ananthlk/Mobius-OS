"use client";

import { useState } from "react";

interface ToolSchema {
    name: string;
    description: string;
    parameters: Record<string, string>;
}

interface Step {
    id: string;
    tool_name: string;
    description: string;
    args_mapping: Record<string, string>;
}

interface StepEditorProps {
    step: Step;
    index: number;
    allSteps: Step[];
    toolSchema?: ToolSchema;
    onChange: (updatedStep: Step) => void;
    onDelete: () => void;
}

export default function StepEditor({ step, index, allSteps, toolSchema, onChange, onDelete }: StepEditorProps) {
    if (!toolSchema) return <div className="p-4 text-gray-400">Select a tool to configure step</div>;

    // Available variables calculation
    const availableVariables = [
        { label: "User Context (Global)", value: "context." },
        ...allSteps.slice(0, index).map(s => ({
            label: `Step ${allSteps.indexOf(s) + 1}: ${s.tool_name}`,
            value: `${s.id}`
        }))
    ];

    const [focusedParam, setFocusedParam] = useState<string | null>(null);

    return (
        <div className="p-0 bg-white border border-[#E5E7EB] rounded-xl mb-6 relative group transition-all duration-300 hover:border-blue-200 hover:shadow-lg overflow-visible">

            {/* Step Number Badge */}
            <div className="absolute -left-3 top-6 w-6 h-6 rounded-full bg-white border border-[#E5E7EB] flex items-center justify-center z-10 shadow-sm text-[#6B7280]">
                <span className="text-[10px] font-mono font-semibold">{index + 1}</span>
            </div>

            {/* Header */}
            <div className="p-5 flex items-start gap-4 border-b border-[#F3F4F6] bg-[#F9FAFB]/50">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center border border-blue-100 text-blue-600 font-bold font-mono text-sm group-hover:bg-blue-100 transition-colors">
                    {step.tool_name[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0 pt-0.5">
                    <h3 className="text-[#1A1A1A] font-semibold text-base tracking-tight flex items-center gap-2">
                        {step.tool_name}
                        <span className="px-1.5 py-0.5 rounded-full bg-[#F3F4F6] text-[9px] text-[#6B7280] uppercase tracking-widest border border-[#E5E7EB]">Tool</span>
                    </h3>
                    <p className="text-[#6B7280] text-xs mt-0.5 truncate font-normal">{toolSchema.description}</p>
                </div>

                <button
                    onClick={onDelete}
                    className="opacity-0 group-hover:opacity-100 transition-all text-gray-400 hover:text-red-500 p-2 hover:bg-red-50 rounded-lg"
                    title="Remove Step"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            </div>

            <div className="p-6 space-y-6">
                {/* Objective Input */}
                <div className="space-y-2">
                    <label className="text-[9px] uppercase tracking-[0.2em] text-[#9CA3AF] font-bold block ml-1">Objective</label>
                    <div className="relative group/input">
                        <input
                            type="text"
                            value={step.description}
                            onChange={(e) => onChange({ ...step, description: e.target.value })}
                            className="w-full bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg px-4 py-3 text-sm text-[#1A1A1A] placeholder-gray-400 focus:outline-none focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-50 transition-all"
                            placeholder="Describe what this step accomplishes..."
                        />
                    </div>
                </div>

                {/* Data Mapping */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <label className="text-[9px] uppercase tracking-[0.2em] text-[#9CA3AF] font-bold block ml-1">Data Flow</label>
                        <span className="text-[9px] text-gray-400 italic">Map inputs from previous steps</span>
                    </div>

                    <div className="bg-[#F9FAFB] rounded-xl p-0.5 border border-[#E5E7EB] space-y-px">
                        {Object.entries(toolSchema.parameters).map(([paramName, paramType]) => (
                            <div key={paramName} className="flex items-center gap-0 p-3 hover:bg-white transition-colors relative z-0 hover:z-10 group/row rounded-lg">
                                <div className="w-1/3 pr-4 border-r border-[#E5E7EB]">
                                    <span className="text-xs text-[#374151] font-medium tracking-wide block">{paramName}</span>
                                    <span className="text-[9px] text-gray-400 font-mono mt-0.5 block truncate" title={paramType}>{paramType}</span>
                                </div>

                                <div className="flex-1 pl-4 flex items-center gap-3 relative">
                                    <svg className="w-3 h-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>

                                    <div className="flex-1 relative">
                                        <input
                                            type="text"
                                            value={step.args_mapping[paramName] || ""}
                                            onChange={(e) => {
                                                const newMapping = { ...step.args_mapping, [paramName]: e.target.value };
                                                onChange({ ...step, args_mapping: newMapping });
                                            }}
                                            onFocus={() => setFocusedParam(paramName)}
                                            onBlur={() => setTimeout(() => setFocusedParam(null), 200)}
                                            className="w-full bg-transparent border-none text-xs text-[#1A1A1A] font-mono placeholder-gray-400 focus:outline-none focus:ring-0 p-0"
                                            placeholder="Select source..."
                                        />

                                        {/* Suggestions Dropdown (Light Theme) */}
                                        {focusedParam === paramName && availableVariables.length > 0 && (
                                            <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-[#E5E7EB] rounded-lg shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
                                                <div className="px-3 py-1.5 text-[9px] uppercase tracking-wider text-gray-400 font-semibold border-b border-[#F3F4F6] bg-[#F9FAFB]">Suggestions</div>
                                                {availableVariables.map((v) => (
                                                    <div
                                                        key={v.value}
                                                        className="px-3 py-2 text-xs text-[#4B5563] hover:bg-blue-50 hover:text-blue-700 cursor-pointer transition-colors border-b border-[#F3F4F6] last:border-0"
                                                        onClick={() => {
                                                            const newMapping = { ...step.args_mapping, [paramName]: v.value };
                                                            onChange({ ...step, args_mapping: newMapping });
                                                            setFocusedParam(null);
                                                        }}
                                                    >
                                                        <span className="font-mono text-blue-600 font-medium">{v.value}</span>
                                                        <span className="ml-2 text-[10px] text-gray-400">({v.label})</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
