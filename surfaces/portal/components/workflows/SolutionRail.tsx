"use client";

import { useState, useEffect } from "react";
import React from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { DiagnosticResult } from "./ProblemEntry";
import Tooltip from "@/components/Tooltip";

interface SolutionRailProps {
    solutions: DiagnosticResult[];
    selectedId: string | null;
    onSelect: (solution: DiagnosticResult) => void;
    mode?: "matches" | "draft";
    draftPlan?: any;
    sessionId?: number | null;
    onStepUpdate?: (stepId: string, updatedStep: any) => void;
    onStepDelete?: (stepId: string) => void;
    onStepReorder?: (newOrder: any[]) => void;
    onStepCreate?: (newStep: any) => void;
}

export default function SolutionRail({ 
    solutions, 
    selectedId, 
    onSelect, 
    draftPlan,
    sessionId,
    onStepUpdate,
    onStepDelete,
    onStepReorder,
    onStepCreate
}: SolutionRailProps) {
    const [draggedStepId, setDraggedStepId] = useState<string | null>(null);
    const [editingStepId, setEditingStepId] = useState<string | null>(null);
    const [localPhases, setLocalPhases] = useState<any[]>(draftPlan?.phases || []);
    const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
    const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());
    const [isLiveBuilderCollapsed, setIsLiveBuilderCollapsed] = useState(false);
    const [isRepositoryCollapsed, setIsRepositoryCollapsed] = useState(false);

    // Sync local phases with draftPlan prop
    React.useEffect(() => {
        if (draftPlan?.phases) {
            setLocalPhases(draftPlan.phases);
        } else if (draftPlan?.steps) {
            // Fallback: convert old steps format to phases for backward compatibility during transition
            setLocalPhases([{
                id: "phase_1",
                name: "Workflow Steps",
                description: "",
                steps: draftPlan.steps
            }]);
        }
    }, [draftPlan]);

    const handleDragStart = (e: React.DragEvent, stepId: string) => {
        setDraggedStepId(stepId);
        e.dataTransfer.effectAllowed = "move";
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
    };

    const handleDrop = (e: React.DragEvent, targetPhaseId: string, targetStepIndex: number) => {
        e.preventDefault();
        if (!draggedStepId) return;

        // Find the dragged step and its phase
        let draggedPhaseId: string | null = null;
        let draggedStepIndex = -1;
        
        for (const phase of localPhases) {
            const stepIndex = phase.steps?.findIndex((s: any) => s.id === draggedStepId) ?? -1;
            if (stepIndex !== -1) {
                draggedPhaseId = phase.id;
                draggedStepIndex = stepIndex;
                break;
            }
        }

        if (draggedPhaseId === null || (draggedPhaseId === targetPhaseId && draggedStepIndex === targetStepIndex)) {
            setDraggedStepId(null);
            return;
        }

        const newPhases = localPhases.map(phase => {
            if (phase.id === draggedPhaseId) {
                const newSteps = [...(phase.steps || [])];
                const [removed] = newSteps.splice(draggedStepIndex, 1);
                
                if (phase.id === targetPhaseId) {
                    // Same phase, just reorder
                    newSteps.splice(targetStepIndex, 0, removed);
                }
                
                return { ...phase, steps: newSteps };
            } else if (phase.id === targetPhaseId) {
                // Different phase, move step
                const draggedStep = localPhases.find(p => p.id === draggedPhaseId)?.steps?.[draggedStepIndex];
                if (draggedStep) {
                    const newSteps = [...(phase.steps || [])];
                    newSteps.splice(targetStepIndex, 0, draggedStep);
                    return { ...phase, steps: newSteps };
                }
            }
            return phase;
        });

        // Remove step from source phase if moved to different phase
        if (draggedPhaseId !== targetPhaseId) {
            const sourcePhase = newPhases.find(p => p.id === draggedPhaseId);
            if (sourcePhase) {
                sourcePhase.steps = sourcePhase.steps.filter((s: any) => s.id !== draggedStepId);
            }
        }

        setLocalPhases(newPhases);
        setDraggedStepId(null);

        // Persist to backend
        if (onStepReorder) {
            onStepReorder(newPhases);
        }
    };

    const handleDelete = async (stepId: string, phaseId: string) => {
        if (!confirm("Are you sure you want to delete this step?")) return;

        const newPhases = localPhases.map(phase => {
            if (phase.id === phaseId) {
                return {
                    ...phase,
                    steps: (phase.steps || []).filter((s: any) => s.id !== stepId)
                };
            }
            return phase;
        }).filter(phase => phase.steps && phase.steps.length > 0); // Remove empty phases

        setLocalPhases(newPhases);

        if (onStepDelete) {
            onStepDelete(stepId);
        }
    };

    const handleEdit = (step: any) => {
        setEditingStepId(step.id);
    };

    const handleSaveEdit = async (stepId: string, updatedStep: any) => {
        const newPhases = localPhases.map(phase => ({
            ...phase,
            steps: (phase.steps || []).map((s: any) => s.id === stepId ? updatedStep : s)
        }));
        setLocalPhases(newPhases);
        setEditingStepId(null);

        if (onStepUpdate) {
            onStepUpdate(stepId, updatedStep);
        }
    };

    const handleCancelEdit = () => {
        setEditingStepId(null);
    };

    const handleAddStep = (phaseId?: string) => {
        const targetPhaseId = phaseId || (localPhases.length > 0 ? localPhases[0].id : null);
        if (!targetPhaseId) return;

        const newStep = {
            id: `step_${Date.now()}`,
            tool_hint: "new_tool",
            description: "New step",
            solves: "",
            tool_matched: false,
            tool_name: null,
            requires_human_review: false,
            is_batch: false
        };
        
        const newPhases = localPhases.map(phase => {
            if (phase.id === targetPhaseId) {
                return {
                    ...phase,
                    steps: [...(phase.steps || []), newStep]
                };
            }
            return phase;
        });
        
        setLocalPhases(newPhases);
        setEditingStepId(newStep.id);

        if (onStepCreate) {
            onStepCreate(newStep);
        }
    };

    return (
        <div className="w-full bg-white border-r-2 border-gray-300 flex flex-col h-full z-20">
            {/* TOP PANEL: LIVE BUILDER */}
            {!isLiveBuilderCollapsed && (
                <div className={`${isRepositoryCollapsed ? 'flex-[1_1_100%]' : 'flex-[1_1_60%]'} flex flex-col min-h-0 border-b-2 border-gray-300 bg-white`}>
                    <div className="px-4 py-4 border-b-2 border-gray-300 bg-gradient-to-b from-yellow-50/80 to-white flex-shrink-0 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2.5">
                                <Tooltip content={draftPlan ? "Active workflow being built in real-time" : "Waiting for workflow plan"}>
                                    <div className={`w-2 h-2 rounded-full cursor-help ${draftPlan ? 'bg-yellow-500 animate-pulse shadow-md shadow-yellow-500/50' : 'bg-gray-400'}`}></div>
                                </Tooltip>
                                <Tooltip content="The workflow currently being constructed based on your conversation">
                                    <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider cursor-help">
                                        Live Builder
                        </h2>
                                </Tooltip>
                            </div>
                            <button
                                onClick={() => setIsLiveBuilderCollapsed(true)}
                                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                title="Collapse Live Builder"
                            >
                                <ChevronUp size={16} />
                            </button>
                        </div>
                    {draftPlan?.problem_statement && (
                        <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                            <p className="text-sm text-gray-900 leading-relaxed">
                                {draftPlan.problem_statement
                                    .split('\n')
                                    .filter((line: string) => {
                                        // Remove lines that match the workflow name
                                        const trimmedLine = line.trim();
                                        return !trimmedLine || trimmedLine !== draftPlan?.name;
                                    })
                                    .join('\n')
                                    .trim()}
                            </p>
                    </div>
                    )}
                </div>

                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 custom-scrollbar min-h-0">
                    {localPhases.length > 0 ? (
                        <>
                            {localPhases.map((phase: any) => {
                                const isPhaseExpanded = expandedPhases.has(phase.id);
                                const phaseSteps = phase.steps || [];
                                
                                return (
                                    <div key={phase.id} className="space-y-2">
                                        {/* Phase Header */}
                                        <div className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-200">
                                            <div className="flex items-center gap-2 flex-1 min-w-0">
                                                <button
                                                    onClick={() => {
                                                        setExpandedPhases(prev => {
                                                            const newSet = new Set(prev);
                                                            if (newSet.has(phase.id)) {
                                                                newSet.delete(phase.id);
                                                            } else {
                                                                newSet.add(phase.id);
                                                            }
                                                            return newSet;
                                                        });
                                                    }}
                                                    className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                                    title={isPhaseExpanded ? "Collapse phase" : "Expand phase"}
                                                >
                                                    {isPhaseExpanded ? (
                                                        <ChevronUp size={14} />
                                                    ) : (
                                                        <ChevronDown size={14} />
                                                    )}
                                                </button>
                                                <h3 className="text-xs font-semibold text-gray-700 truncate">{phase.name}</h3>
                                                {phase.description && (
                                                    <span className="text-[10px] text-gray-500 truncate">- {phase.description}</span>
                                                )}
                                            </div>
                                            <span className="text-[10px] text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
                                                {phaseSteps.length} {phaseSteps.length === 1 ? 'step' : 'steps'}
                                            </span>
                                        </div>
                                        
                                        {/* Phase Steps */}
                                        {isPhaseExpanded && phaseSteps.length > 0 && (
                                            <div className="space-y-3 pl-2 border-l-2 border-gray-200">
                                                {phaseSteps.map((step: any, stepIdx: number) => {
                                                    const isEditing = editingStepId === step.id;
                                                    const isStepExpanded = expandedSteps.has(step.id);

                                                    return (
                                                        <div
                                                            key={step.id}
                                                            draggable
                                                            onDragStart={(e) => handleDragStart(e, step.id)}
                                                            onDragOver={handleDragOver}
                                                            onDrop={(e) => handleDrop(e, phase.id, stepIdx)}
                                                            className={`flex gap-3 group ${draggedStepId === step.id ? 'opacity-50' : ''} w-full`}
                                                        >
                                                            <div className="flex flex-col items-center flex-shrink-0 pt-0.5">
                                                                <Tooltip content={`Step ${stepIdx + 1} - Drag to reorder steps in the workflow`}>
                                                                    <div className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-semibold flex items-center justify-center cursor-move hover:bg-blue-700 transition-colors">
                                                                        {stepIdx + 1}
                                                                    </div>
                                                                </Tooltip>
                                                                {stepIdx < (phaseSteps.length - 1) && <div className="w-px flex-1 bg-gray-200 my-1"></div>}
                                                            </div>
                                        <div className="flex-1 min-w-0">
                                            {isEditing ? (
                                                <StepEditor
                                                    step={step}
                                                    onSave={(updated) => handleSaveEdit(step.id, updated)}
                                                    onCancel={handleCancelEdit}
                                                />
                                            ) : (
                                                <div className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors relative group/card">
                                                    {/* Header - always visible */}
                                                    <div className="flex items-center justify-between p-4">
                                                        <div className="flex items-center gap-2 flex-1 min-w-0">
                                                            <h4 className="text-sm font-semibold text-gray-900 truncate">{step.tool_name || step.tool_hint || "Step"}</h4>
                                                            {/* Tool Matched Icon */}
                                                            {step.tool_matched ? (
                                                                <div className="flex items-center cursor-help group/icon relative" title="Tool matched">
                                                                    <svg className="w-4 h-4 text-green-600 group-hover/icon:text-green-700 transition-colors" fill="currentColor" viewBox="0 0 20 20">
                                                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                                    </svg>
                                                                    <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2 py-1 bg-gray-900 text-white text-[10px] rounded opacity-0 group-hover/icon:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-10">Tool Matched</span>
                                                                </div>
                                                            ) : (
                                                                <div className="flex items-center cursor-help group/icon relative" title="No tool matched">
                                                                    <svg className="w-4 h-4 text-gray-400 group-hover/icon:text-gray-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                                    </svg>
                                                                    <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2 py-1 bg-gray-900 text-white text-[10px] rounded opacity-0 group-hover/icon:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-10">No Tool</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 flex-shrink-0">
                                                            {/* Action buttons */}
                                                            <div className="flex gap-1 opacity-0 group-hover/card:opacity-100 transition-opacity">
                                                                <button
                                                                    onClick={() => handleEdit(step)}
                                                                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                                                    title="Edit step"
                                                                >
                                                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                    </svg>
                                                                </button>
                                                                <button
                                                                    onClick={() => handleDelete(step.id, phase.id)}
                                                                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                                                    title="Delete step"
                                                                >
                                                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                    </svg>
                                                                </button>
                                                            </div>
                                                            {/* Expand/Collapse button */}
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setExpandedSteps(prev => {
                                                                        const newSet = new Set(prev);
                                                                        if (newSet.has(step.id)) {
                                                                            newSet.delete(step.id);
                                                                        } else {
                                                                            newSet.add(step.id);
                                                                        }
                                                                        return newSet;
                                                                    });
                                                                }}
                                                                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded transition-colors"
                                                                title={isStepExpanded ? "Collapse" : "Expand"}
                                                            >
                                                                {isStepExpanded ? (
                                                                    <ChevronUp size={14} />
                                                                ) : (
                                                                    <ChevronDown size={14} />
                                                                )}
                                                            </button>
                                                        </div>
                                                    </div>

                                                    {/* Collapsible content */}
                                                    {isStepExpanded && (
                                                    <div className="px-4 pb-4 border-t border-gray-100 pt-3 space-y-3">
                                                        {/* Indicators row */}
                                                        <div className="flex items-center gap-2 flex-wrap">
                                                        <div className="flex items-center gap-2 flex-1 min-w-0">
                                                            <h4 className="text-sm font-semibold text-gray-900 truncate">{step.tool_name || step.tool_hint || "Step"}</h4>
                                                            {/* Tool Matched Icon */}
                                                            {step.tool_matched ? (
                                                                <div className="flex items-center cursor-help group/icon relative" title="Tool matched">
                                                                    <svg className="w-4 h-4 text-green-600 group-hover/icon:text-green-700 transition-colors" fill="currentColor" viewBox="0 0 20 20">
                                                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                                    </svg>
                                                                    <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2 py-1 bg-gray-900 text-white text-[10px] rounded opacity-0 group-hover/icon:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-10">Tool Matched</span>
                                                                </div>
                                                            ) : (
                                                                <div className="flex items-center cursor-help group/icon relative" title="No tool matched">
                                                                    <svg className="w-4 h-4 text-gray-400 group-hover/icon:text-gray-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                                    </svg>
                                                                    <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2 py-1 bg-gray-900 text-white text-[10px] rounded opacity-0 group-hover/icon:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-10">No Tool</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                            {/* Human Review Icon */}
                                                            {step.requires_human_review && (
                                                                <Tooltip content="This step requires human review before proceeding">
                                                                    <div className="flex items-center cursor-help">
                                                                        <svg className="w-4 h-4 text-amber-500 hover:text-amber-600 hover:scale-110 transition-all" fill="currentColor" viewBox="0 0 20 20">
                                                                            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                                                                            <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                                                                        </svg>
                                                                    </div>
                                                                </Tooltip>
                                                            )}
                                                            {/* Batch/Real-time Icon */}
                                                            {step.is_batch ? (
                                                                <Tooltip content="This step processes data in batches rather than real-time">
                                                                    <div className="flex items-center cursor-help">
                                                                        <svg className="w-4 h-4 text-blue-500 hover:text-blue-600 hover:scale-110 transition-all" fill="currentColor" viewBox="0 0 20 20">
                                                                            <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                                                                        </svg>
                                                                    </div>
                                                                </Tooltip>
                                                            ) : (
                                                                <Tooltip content="This step processes data in real-time as it arrives">
                                                                    <div className="flex items-center cursor-help">
                                                                        <svg className="w-4 h-4 text-emerald-500 hover:text-emerald-600 hover:scale-110 transition-all" fill="currentColor" viewBox="0 0 20 20">
                                                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                                                                        </svg>
                                                                    </div>
                                                                </Tooltip>
                                                            )}
                                                        </div>

                                                        {/* Description */}
                                                        {step.description && (
                                                            <div>
                                                                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Description</div>
                                                                <div className="text-sm text-gray-700 leading-relaxed">{step.description}</div>
                                                            </div>
                                                        )}
                                                        
                                                        {/* Solves section */}
                                                        {step.solves && (
                                                            <div>
                                                                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">Addresses Problem</div>
                                                                <div className="text-sm text-gray-600 leading-relaxed">{step.solves}</div>
                                                            </div>
                                                        )}
                                                        
                                                        {/* Conditional Execution Indicators */}
                                                        {step.execution_conditions && step.execution_conditions.length > 0 && (
                                                            <div>
                                                                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Execution Conditions</div>
                                                                <div className="flex flex-wrap gap-1.5">
                                                                    {step.execution_conditions.map((condition: any, condIdx: number) => {
                                                                        const conditionIcons: Record<string, { icon: string; label: string; color: string }> = {
                                                                            'if': { icon: '⚡', label: 'If', color: 'blue' },
                                                                            'if_else': { icon: '🔀', label: 'If/Else', color: 'purple' },
                                                                            'on_success': { icon: '✅', label: 'On Success', color: 'green' },
                                                                            'on_failure': { icon: '❌', label: 'On Failure', color: 'red' },
                                                                            'on_error': { icon: '⚠️', label: 'On Error', color: 'amber' },
                                                                            'when': { icon: '⏰', label: 'When', color: 'blue' },
                                                                            'unless': { icon: '🚫', label: 'Unless', color: 'gray' }
                                                                        };
                                                                        
                                                                        const condInfo = conditionIcons[condition.condition_type] || { icon: '⚡', label: condition.condition_type, color: 'blue' };
                                                                        const iconColor = condition.icon_color || condInfo.color;

                        return (
                            <div
                                                                                key={condIdx}
                                                                                className="flex items-center gap-1 cursor-help group/cond relative px-2 py-1 bg-gray-50 rounded border border-gray-200"
                                                                                title={condition.condition_description || `${condInfo.label}: ${condition.condition_expression?.field || 'condition'}`}
                                                                            >
                                                                                <span className="text-xs">{condInfo.icon}</span>
                                                                                <span className="text-[10px] font-medium text-gray-700">{condInfo.label}</span>
                                                                                {/* Tooltip */}
                                                                                <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2 py-1 bg-gray-900 text-white text-[10px] rounded opacity-0 group-hover/cond:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-10">
                                                                                    {condition.condition_description || `${condInfo.label}: ${condition.condition_expression?.field || 'condition'}`}
                                    </span>
                                </div>
                                                                        );
                                                                    })}
                                                                </div>
                                                            </div>
                                                        )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                            </div>
                        );
                    })}
                            {/* Add Step Button */}
                            {localPhases.length > 0 && (
                                <button
                                    onClick={() => handleAddStep(localPhases[0]?.id)}
                                    className="w-full p-3 border border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-all text-sm font-medium flex items-center justify-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                    </svg>
                                    Add Step
                                </button>
                            )}
                        </>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm gap-2">
                            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                                <span className="text-xl">🏗️</span>
                            </div>
                            <p>Start chatting to build a workflow...</p>
                        </div>
                    )}
                </div>
            </div>
            )}

            {/* Collapsed Live Builder - just show header bar */}
            {isLiveBuilderCollapsed && (
                <div 
                    className="px-4 py-3 border-b-2 border-gray-300 bg-gradient-to-b from-yellow-50/80 to-white flex-shrink-0 shadow-sm cursor-pointer hover:bg-yellow-50/50 transition-colors"
                    onClick={() => setIsLiveBuilderCollapsed(false)}
                >
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                            <Tooltip content={draftPlan ? "Active workflow being built in real-time" : "Waiting for workflow plan"}>
                                <div className={`w-2 h-2 rounded-full cursor-help ${draftPlan ? 'bg-yellow-500 animate-pulse shadow-md shadow-yellow-500/50' : 'bg-gray-400'}`}></div>
                            </Tooltip>
                            <Tooltip content="The workflow currently being constructed based on your conversation">
                                <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider cursor-help">
                            Live Builder
                        </h2>
                            </Tooltip>
                        </div>
                        <ChevronDown size={16} className="text-gray-400" />
                    </div>
                </div>
            )}

            {/* BOTTOM PANEL: REPOSITORY */}
            {!isRepositoryCollapsed && (
                <div className={`${isLiveBuilderCollapsed ? 'flex-[1_1_100%]' : 'flex-[0_0_40%]'} flex flex-col min-h-0 border-t-2 border-gray-300 bg-white overflow-hidden`}>
                    <div className="px-4 py-4 border-b-2 border-gray-300 bg-gradient-to-b from-gray-50 to-white flex-shrink-0 shadow-sm">
                        <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center justify-between flex-1 mr-2">
                                <Tooltip content="Existing workflows from the repository that match your problem">
                                    <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider cursor-help">
                                        Repository
                                    </h2>
                                </Tooltip>
                                <span className="text-xs font-semibold text-gray-700 bg-gray-200 px-2.5 py-1 rounded-full border border-gray-300">
                                    {solutions.length}
                                </span>
                            </div>
                            <button
                                onClick={() => setIsRepositoryCollapsed(true)}
                                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                                title="Collapse Repository"
                            >
                                <ChevronDown size={16} />
                            </button>
                        </div>
                    <p className="text-xs font-medium text-gray-600 mt-0.5">
                        Matching workflows
                    </p>
                </div>

                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1.5 custom-scrollbar min-h-0">
                    {solutions.length > 0 ? (
                        <>
                            {solutions.map((sol: DiagnosticResult) => {
                                const isSelected = selectedId === sol.recipe_name;
                                const scorePct = Math.round(sol.match_score * 100);
                                const isExpanded = expandedCards.has(sol.recipe_name);

                                return (
                                    <div
                                        key={sol.recipe_name}
                                        className={`rounded-lg border transition-all duration-200 relative overflow-hidden ${isSelected
                                            ? "bg-blue-50 border-blue-300"
                                            : "bg-white border-gray-200 hover:border-gray-300"
                                            }`}
                                    >
                                        {isSelected && <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-blue-500"></div>}

                                        {/* Compact header - always visible */}
                                        <div 
                                            className="flex items-center justify-between px-2.5 py-2"
                                        >
                                            <div 
                                                onClick={() => onSelect(sol)}
                                                className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer"
                                            >
                                                <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase tracking-wider font-medium flex-shrink-0 ${sol.origin === "standard" ? "bg-emerald-100 text-emerald-700" :
                                                    sol.origin === "ai" ? "bg-purple-100 text-purple-700" :
                                                        "bg-blue-100 text-blue-700"
                                                    }`}>
                                                    {sol.origin === "ai" ? "Synth" : "Std"}
                                                </span>
                                                <h3 className={`font-medium text-xs truncate flex-1 ${isSelected ? "text-blue-900" : "text-gray-900"}`}>
                                                    {sol.recipe_name}
                                                </h3>
                                            </div>
                                            <div className="flex items-center gap-1.5 flex-shrink-0">
                                                <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${scorePct > 75 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                                    {scorePct}%
                                                </span>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setExpandedCards(prev => {
                                                            const newSet = new Set(prev);
                                                            if (newSet.has(sol.recipe_name)) {
                                                                newSet.delete(sol.recipe_name);
                                                            } else {
                                                                newSet.add(sol.recipe_name);
                                                            }
                                                            return newSet;
                                                        });
                                                    }}
                                                    className="p-0.5 text-gray-400 hover:text-gray-600 transition-colors"
                                                    title={isExpanded ? "Collapse" : "Expand"}
                                                >
                                                    {isExpanded ? (
                                                        <ChevronUp size={12} />
                                                    ) : (
                                                        <ChevronDown size={12} />
                                                    )}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Expanded content */}
                                        {isExpanded && (
                                            <div className="px-2.5 pb-2.5 pt-0 border-t border-gray-100">
                                                {sol.goal && (
                                                    <div className="mt-2">
                                                        <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide mb-1">Goal</p>
                                                        <p className="text-xs text-gray-700 leading-relaxed">{sol.goal}</p>
                                                    </div>
                                                )}
                                                {sol.reasoning && (
                                                    <div className="mt-2">
                                                        <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide mb-1">Reasoning</p>
                                                        <p className="text-xs text-gray-700 leading-relaxed">{sol.reasoning}</p>
                                    </div>
                                                )}
                                        </div>
                                        )}
                                    </div>
                                );
                            })}
                        </>
                    ) : (
                        <div className="text-center py-8 text-gray-400 text-sm">
                            No library matches found.
                        </div>
                    )}
                </div>
                </div>
            )}

            {/* Collapsed Repository - just show header bar */}
            {isRepositoryCollapsed && (
                <div 
                    className="px-4 py-3 border-t-2 border-gray-300 bg-gradient-to-b from-gray-50 to-white flex-shrink-0 shadow-sm cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => setIsRepositoryCollapsed(false)}
                >
                    <div className="flex items-center justify-between">
                        <div className="flex items-center justify-between flex-1 mr-2">
                            <Tooltip content="Existing workflows from the repository that match your problem">
                                <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider cursor-help">
                                    Repository
                                </h2>
                            </Tooltip>
                            <span className="text-xs font-semibold text-gray-700 bg-gray-200 px-2.5 py-1 rounded-full border border-gray-300">
                                {solutions.length}
                            </span>
                        </div>
                        <ChevronUp size={16} className="text-gray-400" />
                    </div>
                </div>
            )}
        </div>
    );
}

// Simple inline editor component
function StepEditor({ step, onSave, onCancel }: { step: any; onSave: (step: any) => void; onCancel: () => void }) {
    const [editedStep, setEditedStep] = useState(step);

    return (
        <div className="bg-white p-4 rounded-lg border-2 border-blue-400 w-full">
            <div className="space-y-3">
                <div>
                    <label className="text-xs font-medium text-gray-700 mb-1.5 block">Tool Hint</label>
                    <input
                        type="text"
                        value={editedStep.tool_hint || ""}
                        onChange={(e) => setEditedStep({ ...editedStep, tool_hint: e.target.value })}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        placeholder="e.g. database_lookup"
                    />
                </div>
                <div>
                    <label className="text-xs font-medium text-gray-700 mb-1.5 block">Description</label>
                    <textarea
                        value={editedStep.description || ""}
                        onChange={(e) => setEditedStep({ ...editedStep, description: e.target.value })}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                        rows={3}
                        placeholder="Step description"
                    />
                </div>
                <div>
                    <label className="text-xs font-medium text-gray-700 mb-1.5 block">Solves</label>
                    <textarea
                        value={editedStep.solves || ""}
                        onChange={(e) => setEditedStep({ ...editedStep, solves: e.target.value })}
                        className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                        rows={2}
                        placeholder="How this step addresses the problem"
                    />
                </div>
                <div className="flex gap-2 pt-1">
                    <button
                        onClick={() => onSave(editedStep)}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Save
                    </button>
                    <button
                        onClick={onCancel}
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
