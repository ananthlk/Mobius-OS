"use client";

import React, { useState, useEffect } from "react";
import { X, Clock, User, FileText } from "lucide-react";

interface VersionHistoryProps {
    promptKey: string;
    onClose: () => void;
}

interface HistoryItem {
    version: number;
    prompt_config: any;
    changed_by: string | null;
    change_reason: string | null;
    created_at: string;
}

export default function VersionHistory({ promptKey, onClose }: VersionHistoryProps) {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
    const [currentPrompt, setCurrentPrompt] = useState<any>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    useEffect(() => {
        // Fetch version history
        fetch(`${API_URL}/api/admin/prompts/${promptKey}/history`)
            .then(res => res.json())
            .then(data => {
                setHistory(data);
                if (data.length > 0) {
                    setSelectedVersion(data[0].version);
                }
            })
            .catch(err => {
                console.error("Failed to fetch history", err);
            })
            .finally(() => {
                setLoading(false);
            });

        // Fetch current prompt
        fetch(`${API_URL}/api/admin/prompts/${promptKey}`)
            .then(res => res.json())
            .then(data => {
                setCurrentPrompt(data);
            })
            .catch(err => {
                console.error("Failed to fetch current prompt", err);
            });
    }, [promptKey, API_URL]);

    const getSelectedVersionData = () => {
        if (selectedVersion === null && currentPrompt) {
            return {
                version: currentPrompt.version,
                prompt_config: currentPrompt.prompt_config,
                changed_by: currentPrompt.created_by,
                change_reason: "Current version",
                created_at: currentPrompt.updated_at || currentPrompt.created_at
            };
        }
        return history.find(h => h.version === selectedVersion);
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Version History</h2>
                        <p className="text-sm text-gray-500 mt-1 font-mono">{promptKey}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden flex">
                    {/* Version List */}
                    <div className="w-64 border-r border-gray-200 overflow-y-auto p-4 space-y-2">
                        {currentPrompt && (
                            <div
                                onClick={() => setSelectedVersion(null)}
                                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                                    selectedVersion === null
                                        ? "bg-indigo-50 border-2 border-indigo-500"
                                        : "bg-gray-50 hover:bg-gray-100 border-2 border-gray-300"
                                }`}
                            >
                                <div className="flex items-center gap-2 mb-1">
                                    <Clock className="w-4 h-4 text-gray-500" />
                                    <span className="font-semibold text-sm">v{currentPrompt.version}</span>
                                    <span className="text-xs text-green-600 font-medium">Current</span>
                                </div>
                                <p className="text-xs text-gray-500">
                                    {new Date(currentPrompt.updated_at || currentPrompt.created_at).toLocaleDateString()}
                                </p>
                            </div>
                        )}

                        {loading ? (
                            <div className="text-sm text-gray-500">Loading history...</div>
                        ) : history.length === 0 ? (
                            <div className="text-sm text-gray-500">No version history</div>
                        ) : (
                            history.map((item) => (
                                <div
                                    key={item.version}
                                    onClick={() => setSelectedVersion(item.version)}
                                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                                        selectedVersion === item.version
                                            ? "bg-indigo-50 border-2 border-indigo-500"
                                            : "bg-gray-50 hover:bg-gray-100 border-2 border-gray-300"
                                    }`}
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <Clock className="w-4 h-4 text-gray-500" />
                                        <span className="font-semibold text-sm">v{item.version}</span>
                                    </div>
                                    <p className="text-xs text-gray-500 mb-1">
                                        {new Date(item.created_at).toLocaleDateString()}
                                    </p>
                                    {item.changed_by && (
                                        <div className="flex items-center gap-1 text-xs text-gray-400">
                                            <User className="w-3 h-3" />
                                            {item.changed_by}
                                        </div>
                                    )}
                                    {item.change_reason && (
                                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                            {item.change_reason}
                                        </p>
                                    )}
                                </div>
                            ))
                        )}
                    </div>

                    {/* Version Details */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {getSelectedVersionData() ? (
                            <div className="space-y-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Version {getSelectedVersionData()?.version}</h3>
                                    <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                                        <div className="flex items-center gap-1">
                                            <Clock className="w-4 h-4" />
                                            {new Date(getSelectedVersionData()?.created_at || "").toLocaleString()}
                                        </div>
                                        {getSelectedVersionData()?.changed_by && (
                                            <div className="flex items-center gap-1">
                                                <User className="w-4 h-4" />
                                                {getSelectedVersionData()?.changed_by}
                                            </div>
                                        )}
                                    </div>
                                    {getSelectedVersionData()?.change_reason && (
                                        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg mb-4">
                                            <p className="text-sm font-medium text-blue-900 mb-1">Change Reason</p>
                                            <p className="text-sm text-blue-700">{getSelectedVersionData()?.change_reason}</p>
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <div className="flex items-center gap-2 mb-2">
                                        <FileText className="w-5 h-5 text-gray-500" />
                                        <h4 className="font-semibold text-gray-900">Prompt Configuration</h4>
                                    </div>
                                    <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                                        <pre className="text-sm font-mono text-gray-800 whitespace-pre-wrap overflow-x-auto">
                                            {JSON.stringify(getSelectedVersionData()?.prompt_config, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-full text-gray-500">
                                Select a version to view details
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}



