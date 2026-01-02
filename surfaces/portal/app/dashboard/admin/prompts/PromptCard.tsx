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
        <div className="bg-white rounded-xl border border-gray-200 hover:border-indigo-300 hover:shadow-md transition-all p-5">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <Tag className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                        <span className="text-xs font-mono text-gray-500 truncate" title={prompt.prompt_key}>
                            {prompt.prompt_key}
                        </span>
                        <button
                            onClick={onCopyKey}
                            className="ml-1 p-1 hover:bg-gray-100 rounded transition-colors"
                            title="Copy prompt key"
                        >
                            {copied ? (
                                <Check className="w-3 h-3 text-green-600" />
                            ) : (
                                <Copy className="w-3 h-3 text-gray-400" />
                            )}
                        </button>
                    </div>
                    <h3 className="font-semibold text-gray-900 truncate">
                        {prompt.module_name}
                        {prompt.domain && (
                            <span className="text-gray-500 font-normal"> • {prompt.domain}</span>
                        )}
                        {prompt.mode && (
                            <span className="text-gray-500 font-normal"> • {prompt.mode}</span>
                        )}
                        {prompt.step && (
                            <span className="text-gray-500 font-normal"> • {prompt.step}</span>
                        )}
                    </h3>
                </div>
                <div className="flex items-center gap-1 bg-indigo-50 text-indigo-700 px-2 py-1 rounded-full text-xs font-semibold">
                    v{prompt.version}
                </div>
            </div>

            {/* Description */}
            {prompt.description && (
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {prompt.description}
                </p>
            )}

            {/* Metadata */}
            <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
                {prompt.domain && (
                    <span className="px-2 py-1 bg-blue-100 rounded text-blue-700">
                        {prompt.domain}
                    </span>
                )}
                {prompt.mode && (
                    <span className="px-2 py-1 bg-purple-100 rounded text-purple-700">
                        {prompt.mode}
                    </span>
                )}
                {prompt.step && (
                    <span className="px-2 py-1 bg-green-100 rounded text-green-700">
                        {prompt.step}
                    </span>
                )}
                <span>
                    {new Date(prompt.created_at).toLocaleDateString()}
                </span>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-4 border-t border-gray-100">
                <button
                    onClick={onEdit}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                    <Edit className="w-4 h-4" />
                    Edit
                </button>
                <button
                    onClick={onRefine}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                >
                    <Sparkles className="w-4 h-4" />
                    Refine
                </button>
                <button
                    onClick={onViewHistory}
                    className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                    title="View version history"
                >
                    <History className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

