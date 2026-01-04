"use client";

import React from 'react';
import { CheckCircle, Clock, Play, Pause, XCircle, AlertCircle, Wrench } from 'lucide-react';

export interface PlanState {
    status: 'draft' | 'user_review' | 'user_approved' | 'planned_for_execution' | 'executing' | 'completed' | 'failed' | 'cancelled';
    phases: PhaseState[];
}

export interface PhaseState {
    id: string;
    name: string;
    status: 'planned' | 'user_approved' | 'ready' | 'in_progress' | 'completed' | 'skipped' | 'failed';
    steps: StepState[];
}

export interface StepState {
    id: string;
    description: string;
    status: 'planned' | 'user_approved' | 'tool_configured' | 'ready' | 'executing' | 'completed' | 'failed' | 'skipped';
    tool?: {
        tool_name: string;
        inputs: Record<string, string>;
        outputs: Record<string, string>;
    };
    metadata?: {
        tool_configured: boolean;
        enhanced_by_agents: string[];
        execution_result?: any;
        execution_error?: string;
    };
}

interface PlanStateDisplayProps {
    planState: PlanState;
    onApprove?: (planId: number) => void;
    onPhaseApprove?: (phaseId: string) => void;
    onStepApprove?: (stepId: string) => void;
    planId?: number;
}

export default function PlanStateDisplay({
    planState,
    onApprove,
    onPhaseApprove,
    onStepApprove,
    planId
}: PlanStateDisplayProps) {
    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
            case 'user_approved':
                return <CheckCircle size={16} className="text-[var(--brand-green)]" />;
            case 'executing':
            case 'in_progress':
                return <Play size={16} className="text-[var(--primary-blue)]" />;
            case 'ready':
            case 'tool_configured':
                return <Clock size={16} className="text-[var(--brand-yellow)]" />;
            case 'failed':
                return <XCircle size={16} className="text-[var(--brand-red)]" />;
            case 'paused':
                return <Pause size={16} className="text-[var(--text-secondary)]" />;
            default:
                return <AlertCircle size={16} className="text-[var(--text-muted)]" />;
        }
    };

    const getStatusBadge = (status: string) => {
        const colors = {
            'completed': 'bg-[var(--brand-green-light)] text-[var(--brand-green-dark)]',
            'user_approved': 'bg-[var(--primary-blue-light)] text-[var(--primary-blue-dark)]',
            'executing': 'bg-[var(--primary-blue-light)] text-[var(--primary-blue-dark)]',
            'in_progress': 'bg-[var(--primary-blue-light)] text-[var(--primary-blue-dark)]',
            'ready': 'bg-[var(--brand-yellow-light)] text-[var(--brand-yellow-dark)]',
            'tool_configured': 'bg-[var(--brand-yellow-light)] text-[var(--brand-yellow-dark)]',
            'planned': 'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
            'failed': 'bg-[var(--brand-red-light)] text-[var(--brand-red-dark)]',
            'cancelled': 'bg-[var(--bg-secondary)] text-[var(--text-primary)]'
        };
        return colors[status as keyof typeof colors] || 'bg-[var(--bg-secondary)] text-[var(--text-primary)]';
    };

    return (
        <div className="space-y-4">
            {/* Plan-level status */}
            <div className="p-4 bg-[var(--bg-primary)] border-2 border-[var(--border-subtle)] rounded-[var(--radius-lg)]">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {getStatusIcon(planState.status)}
                        <span className="font-semibold">Plan Status</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(planState.status)}`}>
                            {planState.status.replace('_', ' ').toUpperCase()}
                        </span>
                    </div>
                    {planState.status === 'draft' && onApprove && planId && (
                        <button
                            onClick={() => onApprove(planId)}
                            className="px-4 py-2 bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)]"
                        >
                            Approve Plan
                        </button>
                    )}
                </div>
            </div>

            {/* Phases */}
            {planState.phases.map((phase) => (
                <div key={phase.id} className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            {getStatusIcon(phase.status)}
                            <h3 className="font-semibold">{phase.name}</h3>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(phase.status)}`}>
                                {phase.status.replace('_', ' ').toUpperCase()}
                            </span>
                        </div>
                        {phase.status === 'planned' && onPhaseApprove && (
                            <button
                                onClick={() => onPhaseApprove(phase.id)}
                                className="px-3 py-1 text-sm bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded hover:bg-[var(--primary-blue-dark)]"
                            >
                                Approve
                            </button>
                        )}
                    </div>

                    {/* Steps */}
                    <div className="space-y-2 ml-6">
                        {phase.steps.map((step) => (
                            <div
                                key={step.id}
                                className={`p-3 rounded border ${
                                    step.status === 'completed' ? 'bg-[var(--brand-green-light)] border-[var(--brand-green)]' :
                                    step.status === 'executing' ? 'bg-[var(--primary-blue-light)] border-[var(--primary-blue)]' :
                                    step.status === 'failed' ? 'bg-[var(--brand-red-light)] border-[var(--brand-red)]' :
                                    'bg-[var(--bg-secondary)] border-[var(--border-subtle)]'
                                }`}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            {getStatusIcon(step.status)}
                                            <span className="text-sm font-medium">{step.description}</span>
                                            <span className={`px-2 py-0.5 rounded text-xs ${getStatusBadge(step.status)}`}>
                                                {step.status.replace('_', ' ')}
                                            </span>
                                        </div>

                                        {/* Tool configuration */}
                                        {step.tool && (
                                            <div className="mt-2 p-2 bg-[var(--bg-primary)] rounded border border-[var(--border-subtle)]">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <Wrench size={14} className="text-[var(--primary-blue)]" />
                                                    <span className="text-sm font-medium text-[var(--primary-blue)]">
                                                        {step.tool.tool_name}
                                                    </span>
                                                </div>
                                                
                                                {Object.keys(step.tool.inputs).length > 0 && (
                                                    <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                        <strong>Inputs:</strong>
                                                        <ul className="ml-4 list-disc">
                                                            {Object.entries(step.tool.inputs).map(([key, value]) => (
                                                                <li key={key}>{key}: {value}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}

                                                {Object.keys(step.tool.outputs).length > 0 && (
                                                    <div className="text-xs text-[var(--text-secondary)]">
                                                        <strong>Outputs:</strong>
                                                        <ul className="ml-4 list-disc">
                                                            {Object.entries(step.tool.outputs).map(([key, value]) => (
                                                                <li key={key}>{key}: {value}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Agent enhancements */}
                                        {step.metadata?.enhanced_by_agents && step.metadata.enhanced_by_agents.length > 0 && (
                                            <div className="mt-2 text-xs text-[var(--text-secondary)]">
                                                Enhanced by: {step.metadata.enhanced_by_agents.join(', ')}
                                            </div>
                                        )}

                                        {/* Execution error */}
                                        {step.metadata?.execution_error && (
                                            <div className="mt-2 text-xs text-[var(--brand-red)]">
                                                Error: {step.metadata.execution_error}
                                            </div>
                                        )}
                                    </div>

                                    {step.status === 'planned' && onStepApprove && (
                                        <button
                                            onClick={() => onStepApprove(step.id)}
                                            className="px-2 py-1 text-xs bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded hover:bg-[var(--primary-blue-dark)]"
                                        >
                                            Approve
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

