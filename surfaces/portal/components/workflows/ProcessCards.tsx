"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle, Info } from "lucide-react";

interface Step {
    id: string;
    description: string;
    tool_hint?: string;
    tool_matched?: boolean;
    requires_human_review?: boolean;
    is_batch?: boolean;
}

interface Phase {
    id: string;
    name: string;
    description?: string;
    steps: Step[];
}

interface ProcessCardsProps {
    phases: Phase[];
    highlightedSteps?: Array<{
        step_id: string;
        phase_id: string;
        issue_type: "ambiguity" | "missing_info";
        description: string;
        missing_fields?: string[];
    }>;
    onStepClick?: (stepId: string, phaseId: string) => void;
    selectedStepId?: string;
}

export default function ProcessCards({
    phases,
    highlightedSteps = [],
    onStepClick,
    selectedStepId
}: ProcessCardsProps) {
    const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set(phases.map(p => p.id)));

    const togglePhase = (phaseId: string) => {
        setExpandedPhases(prev => {
            const newSet = new Set(prev);
            if (newSet.has(phaseId)) {
                newSet.delete(phaseId);
            } else {
                newSet.add(phaseId);
            }
            return newSet;
        });
    };

    const getStepIssue = (stepId: string) => {
        return highlightedSteps.find(h => h.step_id === stepId);
    };

    const getStepCardClass = (stepId: string) => {
        const issue = getStepIssue(stepId);
        const isSelected = selectedStepId === stepId;
        
        let baseClass = "p-3 rounded-lg border-2 transition-all cursor-pointer hover:shadow-md ";
        
        if (isSelected) {
            baseClass += "border-blue-500 bg-blue-50 ";
        } else if (issue) {
            if (issue.issue_type === "missing_info") {
                baseClass += "border-red-300 bg-red-50 ";
            } else {
                baseClass += "border-yellow-300 bg-yellow-50 ";
            }
        } else {
            baseClass += "border-gray-200 bg-white ";
        }
        
        return baseClass;
    };

    return (
        <div className="h-full overflow-y-auto p-4 space-y-4 custom-scrollbar">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Process Cards</h2>
                <p className="text-sm text-gray-500">Review your workflow phases and steps</p>
            </div>

            {phases.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                    <Info className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No phases available yet</p>
                </div>
            ) : (
                phases.map((phase) => {
                    const isExpanded = expandedPhases.has(phase.id);
                    const phaseSteps = phase.steps || [];
                    
                    return (
                        <div key={phase.id} className="border border-gray-200 rounded-lg bg-white">
                            {/* Phase Header */}
                            <button
                                onClick={() => togglePhase(phase.id)}
                                className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-2 h-2 rounded-full ${isExpanded ? 'bg-blue-500' : 'bg-gray-300'}`} />
                                    <div className="text-left">
                                        <h3 className="font-semibold text-gray-800">{phase.name}</h3>
                                        {phase.description && (
                                            <p className="text-xs text-gray-500 mt-1">{phase.description}</p>
                                        )}
                                    </div>
                                </div>
                                <span className="text-xs text-gray-400">
                                    {phaseSteps.length} step{phaseSteps.length !== 1 ? 's' : ''}
                                </span>
                            </button>

                            {/* Phase Steps */}
                            {isExpanded && (
                                <div className="px-4 pb-4 space-y-2">
                                    {phaseSteps.length === 0 ? (
                                        <p className="text-sm text-gray-400 italic py-2">No steps in this phase</p>
                                    ) : (
                                        phaseSteps.map((step) => {
                                            const issue = getStepIssue(step.id);
                                            const isSelected = selectedStepId === step.id;

                                            return (
                                                <div
                                                    key={step.id}
                                                    className={getStepCardClass(step.id)}
                                                    onClick={() => onStepClick?.(step.id, phase.id)}
                                                >
                                                    <div className="flex items-start gap-2">
                                                        {/* Issue Indicator */}
                                                        {issue ? (
                                                            issue.issue_type === "missing_info" ? (
                                                                <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                                                            ) : (
                                                                <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                                                            )
                                                        ) : (
                                                            <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                                                        )}

                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-sm font-medium text-gray-800">
                                                                {step.description || `Step ${step.id}`}
                                                            </p>
                                                            
                                                            {issue && (
                                                                <div className="mt-1">
                                                                    <p className="text-xs text-gray-600">
                                                                        {issue.description}
                                                                    </p>
                                                                    {issue.missing_fields && issue.missing_fields.length > 0 && (
                                                                        <p className="text-xs text-red-600 mt-1">
                                                                            Missing: {issue.missing_fields.join(", ")}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            )}

                                                            {step.tool_hint && (
                                                                <p className="text-xs text-gray-500 mt-1">
                                                                    Tool: {step.tool_hint}
                                                                    {step.tool_matched ? (
                                                                        <span className="text-green-600 ml-1">✓</span>
                                                                    ) : (
                                                                        <span className="text-yellow-600 ml-1">⚠</span>
                                                                    )}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })
            )}
        </div>
    );
}

