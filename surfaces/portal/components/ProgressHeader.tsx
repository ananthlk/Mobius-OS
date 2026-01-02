"use client";

import { useState } from "react";
import { MapPin, TrendingUp, PlayCircle, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import Tooltip from "@/components/Tooltip";

export interface ProgressState {
    domain?: string;
    strategy?: string;
    currentStep?: string;
    percentComplete?: number;
    status?: string;
}

export interface ProgressHeaderProps {
    progress: ProgressState;
    className?: string;
    defaultCollapsed?: boolean; // Start collapsed by default
    variant?: "default" | "compact" | "detailed";
}

// Strategy label mappings
const STRATEGY_LABELS: Record<string, string> = {
    'EVIDENCE_BASED': 'Evidence Based',
    'TABULA_RASA': 'Tabula Rasa',
    'CREATIVE': 'Creative',
    'evidence_based': 'Evidence Based',
    'tabula_rasa': 'Tabula Rasa',
    'creative': 'Creative'
};

// Status label mappings
const STATUS_LABELS: Record<string, string> = {
    'GATHERING': 'Gathering Requirements',
    'PLANNING': 'Planning Workflow',
    'APPROVED': 'Approved',
    'EXECUTING': 'Executing',
    'COMPLETED': 'Completed',
    'gathering': 'Gathering Requirements',
    'planning': 'Planning Workflow',
    'approved': 'Approved',
    'executing': 'Executing',
    'completed': 'Completed'
};

// Status color mappings
const STATUS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    'GATHERING': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    'PLANNING': { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
    'APPROVED': { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
    'EXECUTING': { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
    'COMPLETED': { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' },
    'gathering': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    'planning': { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
    'approved': { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
    'executing': { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
    'completed': { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' }
};

export default function ProgressHeader({
    progress,
    className = "",
    defaultCollapsed = true, // Default to collapsed
    variant = "default"
}: ProgressHeaderProps) {
    const [isExpanded, setIsExpanded] = useState(!defaultCollapsed);
    
    const {
        domain,
        strategy,
        currentStep,
        percentComplete = 0,
        status
    } = progress;

    const strategyLabel = strategy ? (STRATEGY_LABELS[strategy] || strategy) : null;
    const statusLabel = status ? (STATUS_LABELS[status] || status) : null;
    const statusColor = status ? (STATUS_COLORS[status] || STATUS_COLORS['GATHERING']) : null;

    // Determine if we have any content to show
    const hasContent = domain || strategy || currentStep || percentComplete > 0 || status;

    if (!hasContent && variant !== "detailed") {
        return null; // Don't render empty header
    }

    // Render based on variant
    if (variant === "compact") {
        return (
            <div className={`h-12 border-b border-gray-200 bg-white/95 backdrop-blur-sm sticky top-0 z-30 ${className}`}>
                <div className="h-full px-4 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                        {domain && (
                            <div className="flex items-center gap-1.5 text-xs">
                                <MapPin size={12} className="text-gray-400 flex-shrink-0" />
                                <span className="font-medium text-gray-900 truncate">{domain}</span>
                            </div>
                        )}
                        {strategy && (
                            <div className="px-2 py-0.5 rounded-md bg-blue-50 border border-blue-100 text-[10px] font-medium text-blue-700 flex-shrink-0">
                                {strategyLabel}
                            </div>
                        )}
                        {currentStep && (
                            <div className="flex items-center gap-1.5 text-xs text-gray-600 truncate min-w-0">
                                <PlayCircle size={12} className="text-gray-400 flex-shrink-0" />
                                <span className="truncate">{currentStep}</span>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {status && statusColor && (
                            <div className={`px-2 py-0.5 rounded-md ${statusColor.bg} border ${statusColor.border} text-[10px] font-medium ${statusColor.text}`}>
                                {statusLabel}
                            </div>
                        )}
                        <div className="flex items-center gap-2 min-w-[120px]">
                            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500 ease-out"
                                    style={{ width: `${Math.min(100, Math.max(0, percentComplete))}%` }}
                                />
                            </div>
                            <span className="text-xs font-semibold text-gray-700 w-10 text-right">
                                {percentComplete}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Collapsed state - Just progress bar (default)
    if (!isExpanded) {
        return (
            <div className={`h-12 border-b border-gray-200 bg-white/95 backdrop-blur-sm sticky top-0 z-30 transition-all duration-300 ${className}`}>
                <button
                    onClick={() => setIsExpanded(true)}
                    className="w-full h-full px-6 flex items-center justify-between gap-4 hover:bg-gray-50/50 transition-colors group"
                >
                    {/* Left: Progress indicator */}
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <div className="w-1 h-6 bg-blue-500 rounded-full"></div>
                            <span className="text-xs font-medium text-gray-600">
                                {statusLabel || "Progress"}
                            </span>
                        </div>
                        {currentStep && (
                            <span className="text-xs text-gray-500 truncate hidden sm:block">
                                {currentStep}
                            </span>
                        )}
                    </div>

                    {/* Right: Progress bar and percentage */}
                    <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden shadow-inner">
                            <div 
                                className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500 rounded-full transition-all duration-700 ease-out relative overflow-hidden"
                                style={{ width: `${Math.min(100, Math.max(0, percentComplete))}%` }}
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                            </div>
                        </div>
                        <div className="flex items-baseline gap-1 min-w-[3rem]">
                            <span className="text-lg font-bold text-gray-900">
                                {percentComplete}
                            </span>
                            <span className="text-xs font-medium text-gray-500">%</span>
                        </div>
                        <ChevronDown size={16} className="text-gray-400 group-hover:text-gray-600 transition-colors flex-shrink-0" />
                    </div>
                </button>
            </div>
        );
    }

    // Expanded state - Full details
    return (
        <div className={`border-b border-gray-200 bg-gradient-to-b from-white to-gray-50/30 backdrop-blur-sm sticky top-0 z-30 shadow-sm transition-all duration-300 ${className}`}>
            <div className="px-6 py-4">
                {/* Collapse button row */}
                <div className="flex items-center justify-end mb-3">
                    <button
                        onClick={() => setIsExpanded(false)}
                        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors group"
                    >
                        <span>Collapse</span>
                        <ChevronUp size={14} className="text-gray-400 group-hover:text-gray-600 transition-colors" />
                    </button>
                </div>

                {/* Top row: Domain and Strategy */}
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-4">
                        {domain && (
                            <div className="flex items-center gap-2">
                                <Tooltip content="The problem domain or category this workflow addresses">
                                    <div className="p-1.5 rounded-lg bg-blue-50 border border-blue-100 cursor-help">
                                        <MapPin size={16} className="text-blue-600" />
                                    </div>
                                </Tooltip>
                                <div className="flex flex-col">
                                    <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider leading-none mb-0.5">
                                        Domain
                                    </span>
                                    <span className="text-base font-semibold text-gray-900 leading-none">
                                        {domain}
                                    </span>
                                </div>
                            </div>
                        )}

                        {strategy && (
                            <>
                                <div className="w-px h-8 bg-gray-200" />
                                <Tooltip content="The strategy approach being used: Evidence Based (uses existing patterns), Tabula Rasa (starts fresh), or Creative (innovative solutions)">
                                    <div className="px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-100 flex items-center gap-2 cursor-help">
                                        <TrendingUp size={14} className="text-blue-600" />
                                        <span className="text-sm font-semibold text-blue-700">
                                            {strategyLabel}
                                        </span>
                                    </div>
                                </Tooltip>
                            </>
                        )}
                    </div>

                    {/* Status badge */}
                    {status && statusColor && (
                        <Tooltip content={`Workflow status: ${statusLabel}. Shows the current phase of the workflow development process.`}>
                            <div className={`px-3 py-1.5 rounded-lg ${statusColor.bg} border ${statusColor.border} flex items-center gap-2 cursor-help`}>
                                <CheckCircle2 size={14} className={statusColor.text} />
                                <span className={`text-sm font-semibold ${statusColor.text}`}>
                                    {statusLabel}
                                </span>
                            </div>
                        </Tooltip>
                    )}
                </div>

                {/* Bottom row: Current Step and Progress */}
                <div className="flex items-center justify-between gap-4">
                    {currentStep && (
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                            <Tooltip content="The current step being processed in the workflow journey">
                                <PlayCircle size={16} className="text-gray-400 flex-shrink-0 cursor-help" />
                            </Tooltip>
                            <div className="min-w-0 flex-1">
                                <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-0.5">
                                    Current Step
                                </span>
                                <span className="text-sm font-medium text-gray-700 truncate block">
                                    {currentStep}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Progress - right */}
                    <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="text-right">
                            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-1">
                                Progress
                            </span>
                            <div className="flex items-baseline gap-2">
                                <span className="text-2xl font-bold text-gray-900">
                                    {percentComplete}
                                </span>
                                <span className="text-sm font-medium text-gray-500">%</span>
                            </div>
                        </div>
                        <div className="w-32 h-3 bg-gray-100 rounded-full overflow-hidden shadow-inner">
                            <div 
                                className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500 rounded-full transition-all duration-700 ease-out shadow-sm relative overflow-hidden"
                                style={{ width: `${Math.min(100, Math.max(0, percentComplete))}%` }}
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

