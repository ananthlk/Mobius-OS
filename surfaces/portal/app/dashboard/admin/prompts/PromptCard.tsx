"use client";

import React from "react";
import { Edit, Sparkles, History, Copy, Check, Tag } from "lucide-react";

interface Prompt {
    id: number;
    prompt_key: string;
    module_name: string;
    domain: string | null;
    mode: string | null;
    step: string | null;
    version: number;
    description: string | null;
    created_at: string;
    updated_at: string | null;
}

interface PromptCardProps {
    prompt: Prompt;
    onEdit: () => void;
    onRefine: () => void;
    onViewHistory: () => void;
    onCopyKey: () => void;
    copied: boolean;
}

export default function PromptCard({
    prompt,
    onEdit,
    onRefine,
    onViewHistory,
    onCopyKey,
    copied
}: PromptCardProps) {
    return (
        <div className="bg-[var(--bg-primary)] rounded-xl border border-[var(--border-subtle)] hover:border-[var(--primary-blue)] hover:shadow-[var(--shadow-md)] transition-all p-5">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Tag className="w-4 h-4 text-[var(--primary-blue)] flex-shrink-0" />
                        <span className="text-xs font-mono text-[var(--text-secondary)] truncate" title={prompt.prompt_key}>
                            {prompt.prompt_key}
                        </span>
                        <button
                            onClick={onCopyKey}
                            className="ml-1 p-1 hover:bg-[var(--bg-secondary)] rounded transition-colors"
                            title="Copy prompt key"
                        >
                            {copied ? (
                                <Check className="w-3 h-3 text-[var(--brand-green)]" />
                            ) : (
                                <Copy className="w-3 h-3 text-[var(--text-muted)]" />
                            )}
                        </button>
                    </div>
                    <h3 className="font-semibold text-[var(--text-primary)] truncate">
                        {prompt.module_name}
                        {prompt.domain && (
                            <span className="text-[var(--text-secondary)] font-normal"> • {prompt.domain}</span>
                        )}
                        {prompt.mode && (
                            <span className="text-[var(--text-secondary)] font-normal"> • {prompt.mode}</span>
                        )}
                        {prompt.step && (
                            <span className="text-[var(--text-secondary)] font-normal"> • {prompt.step}</span>
                        )}
                    </h3>
                </div>
                <div className="flex items-center gap-1 bg-[var(--primary-blue-light)] text-[var(--primary-blue-dark)] px-2 py-1 rounded-full text-xs font-semibold">
                    v{prompt.version}
                </div>
            </div>

            {/* Description */}
            {prompt.description && (
                <p className="text-sm text-[var(--text-secondary)] mb-4 line-clamp-2">
                    {prompt.description}
                </p>
            )}

            {/* Metadata */}
            <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)] mb-4">
                {prompt.domain && (
                    <span className="px-2 py-1 bg-[var(--primary-blue-light)] rounded text-[var(--primary-blue-dark)]">
                        {prompt.domain}
                    </span>
                )}
                {prompt.mode && (
                    <span className="px-2 py-1 bg-[var(--brand-yellow-light)] rounded text-[var(--brand-yellow-dark)]">
                        {prompt.mode}
                    </span>
                )}
                {prompt.step && (
                    <span className="px-2 py-1 bg-[var(--brand-green-light)] rounded text-[var(--brand-green-dark)]">
                        {prompt.step}
                    </span>
                )}
                <span>
                    {new Date(prompt.created_at).toLocaleDateString()}
                </span>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-4 border-t border-[var(--border-subtle)]">
                <button
                    onClick={onEdit}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[var(--text-primary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] rounded-[var(--radius-md)] transition-colors"
                >
                    <Edit className="w-4 h-4" />
                    Edit
                </button>
                <button
                    onClick={onRefine}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[var(--primary-blue-dark)] bg-[var(--primary-blue-light)] hover:bg-[var(--primary-blue-light)]/80 rounded-[var(--radius-md)] transition-colors"
                >
                    <Sparkles className="w-4 h-4" />
                    Refine
                </button>
                <button
                    onClick={onViewHistory}
                    className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[var(--text-primary)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] rounded-[var(--radius-md)] transition-colors"
                    title="View version history"
                >
                    <History className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

