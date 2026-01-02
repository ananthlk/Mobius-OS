"use client";

import React, { useState, useEffect } from "react";
import { X, Sparkles, Save, AlertCircle, Loader } from "lucide-react";

interface Prompt {
    id: number;
    prompt_key: string;
    module_name: string;
    strategy: string | null;
    sub_level: string | null;
    version: number;
    description: string | null;
}

interface PromptRefinerProps {
    prompt: Prompt;
    onClose: () => void;
    onRefined: () => void;
}

export default function PromptRefiner({ prompt, onClose, onRefined }: PromptRefinerProps) {
    const [situation, setSituation] = useState("");
    const [requirements, setRequirements] = useState("");
    const [whatWorks, setWhatWorks] = useState("");
    const [whatDoesntWork, setWhatDoesntWork] = useState("");
    const [refinedPrompt, setRefinedPrompt] = useState<any>(null);
    const [refining, setRefining] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentPromptConfig, setCurrentPromptConfig] = useState<any>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    useEffect(() => {
        // Fetch current prompt config
        fetch(`${API_URL}/api/admin/prompts/${prompt.prompt_key}`)
            .then(res => res.json())
            .then(data => {
                setCurrentPromptConfig(data.prompt_config);
            })
            .catch(err => {
                console.error("Failed to fetch prompt", err);
                setError("Failed to load prompt details");
            });
    }, [prompt, API_URL]);

    const handleRefine = async () => {
        if (!situation.trim() || !requirements.trim()) {
            setError("Situation and Requirements are required");
            return;
        }

        setRefining(true);
        setError(null);

        try {
            const res = await fetch(`${API_URL}/api/admin/prompts/${prompt.prompt_key}/refine`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": "admin"
                },
                body: JSON.stringify({
                    situation: situation.trim(),
                    requirements: requirements.trim(),
                    what_works: whatWorks.trim() || "N/A",
                    what_doesnt_work: whatDoesntWork.trim() || "N/A"
                })
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || "Failed to refine prompt");
            }

            const data = await res.json();
            setRefinedPrompt(data.refined_prompt);
        } catch (err: any) {
            setError(err.message || "Failed to refine prompt");
        } finally {
            setRefining(false);
        }
    };

    const handleSave = async () => {
        if (!refinedPrompt) return;

        setSaving(true);
        setError(null);

        try {
            const res = await fetch(`${API_URL}/api/admin/prompts/${prompt.prompt_key}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": "admin"
                },
                body: JSON.stringify({
                    prompt_config: refinedPrompt,
                    change_reason: `LLM refinement: ${situation.substring(0, 100)}`
                })
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || "Failed to save refined prompt");
            }

            onRefined();
            onClose();
        } catch (err: any) {
            setError(err.message || "Failed to save refined prompt");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                        <Sparkles className="w-6 h-6 text-indigo-600" />
                        <h2 className="text-2xl font-bold text-gray-900">Refine Prompt</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {error && (
                        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
                            <AlertCircle className="w-5 h-5" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Prompt Info */}
                    <div className="p-4 bg-gray-50 rounded-lg">
                        <p className="text-sm font-medium text-gray-700 mb-1">Prompt Key</p>
                        <p className="text-sm font-mono text-gray-600">{prompt.prompt_key}</p>
                        <p className="text-sm font-medium text-gray-700 mt-3 mb-1">Current Version</p>
                        <p className="text-sm text-gray-600">v{prompt.version}</p>
                    </div>

                    {/* Refinement Form */}
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Situation *
                            </label>
                            <textarea
                                value={situation}
                                onChange={(e) => setSituation(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                rows={3}
                                placeholder="Describe the current situation, context, or use case..."
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Requirements *
                            </label>
                            <textarea
                                value={requirements}
                                onChange={(e) => setRequirements(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                rows={3}
                                placeholder="What should the prompt accomplish? What are the key requirements?"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                What's Working
                            </label>
                            <textarea
                                value={whatWorks}
                                onChange={(e) => setWhatWorks(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                rows={2}
                                placeholder="What aspects of the current prompt are working well?"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                What's Not Working
                            </label>
                            <textarea
                                value={whatDoesntWork}
                                onChange={(e) => setWhatDoesntWork(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                rows={2}
                                placeholder="What issues are you experiencing? What needs improvement?"
                            />
                        </div>
                    </div>

                    {/* Refine Button */}
                    {!refinedPrompt && (
                        <button
                            onClick={handleRefine}
                            disabled={refining || !situation.trim() || !requirements.trim()}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                            {refining ? (
                                <>
                                    <Loader className="w-5 h-5 animate-spin" />
                                    Refining with LLM...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-5 h-5" />
                                    Generate Refined Prompt
                                </>
                            )}
                        </button>
                    )}

                    {/* Refined Prompt Preview */}
                    {refinedPrompt && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-gray-900">Refined Prompt</h3>
                                <span className="text-sm text-green-600 font-medium">✓ Ready to save</span>
                            </div>
                            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 max-h-96 overflow-y-auto">
                                <pre className="text-sm font-mono text-gray-800 whitespace-pre-wrap">
                                    {JSON.stringify(refinedPrompt, null, 2)}
                                </pre>
                            </div>
                            <p className="text-xs text-gray-500">
                                Review the refined prompt above. Click "Save Refined Prompt" to update the prompt with this version.
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                        Cancel
                    </button>
                    {refinedPrompt && (
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                            <Save className="w-4 h-4" />
                            {saving ? "Saving..." : "Save Refined Prompt"}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

