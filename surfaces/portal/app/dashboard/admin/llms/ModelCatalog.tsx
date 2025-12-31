"use client";

import React, { useState, useEffect } from "react";
import { RefreshCw, Zap, Brain, Terminal, Shield, Check } from "lucide-react";

interface Model {
    id: number;
    model_id: string;
    display_name: string;
    description: string;
    latency_tier: string;
    input_cost_per_1k: number;
    output_cost_per_1k: number;
    capabilities: string[];
}

interface ProviderCatalog {
    id: number;
    name: string;
    models: Model[];
}

export default function ModelCatalog() {
    const [catalog, setCatalog] = useState<ProviderCatalog[]>([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);

    // State for setting defaults
    // TODO: Fetch existing defaults to highlight them

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchCatalog = async () => {
        try {
            const res = await fetch(`${API_URL}/api/admin/ai/catalog`);
            if (res.ok) {
                const data = await res.json();
                setCatalog(data);
            }
        } catch (e) {
            console.error("Failed to fetch catalog", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        try {
            await fetch(`${API_URL}/api/admin/ai/catalog/sync`, { method: "POST" });
            fetchCatalog();
        } catch (e) {
            alert("Sync Failed");
        } finally {
            setSyncing(false);
        }
    };

    const handleSetDefault = async (ruleType: string, moduleId: string, modelId: number) => {
        try {
            const res = await fetch(`${API_URL}/api/admin/ai/defaults`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    rule_type: ruleType,
                    module_id: moduleId,
                    model_id: modelId
                })
            });
            if (res.ok) {
                alert(`Set ${ruleType} rule for ${moduleId} successfully!`);
            }
        } catch (e) {
            alert("Failed to set default");
        }
    };

    useEffect(() => {
        fetchCatalog();
    }, []);

    const getLatencyIcon = (tier: string) => {
        switch (tier) {
            case "fast": return <Zap size={14} className="text-yellow-500" />;
            case "balanced": return <Brain size={14} className="text-blue-500" />;
            default: return <Terminal size={14} className="text-purple-500" />;
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <Shield className="text-purple-500" size={24} />
                        Model Governance Rules
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 max-w-2xl">
                        Configure the "Rules". Decide which model powers which part of Mobius OS.
                        "Global" is the fallback; "Module" overrides specific areas.
                    </p>
                </div>
                <div className="flex flex-col items-end">
                    <button
                        onClick={handleSync}
                        disabled={syncing}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors border border-slate-200 dark:border-slate-700"
                        title="Resets the catalog to the system's curated list of recommended models."
                    >
                        <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
                        {syncing ? "Restoring..." : "Reset to Recommended Defaults"}
                    </button>
                    <span className="text-[10px] text-slate-400 mt-1">
                        *Restores curated model list for active providers.
                    </span>
                </div>
            </div>

            {loading ? (
                <div className="p-8 text-center text-slate-400">Loading Governance Rules...</div>
            ) : (
                <div className="space-y-4">
                    {catalog.map(provider => (
                        <div key={provider.id} className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
                            <div className="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                                <h3 className="font-semibold text-slate-700 dark:text-slate-200">{provider.name} Models</h3>
                                <span className="text-xs text-slate-400">{provider.models.length} Curated Models</span>
                            </div>
                            <div className="divide-y divide-slate-100 dark:divide-slate-800">
                                {provider.models.map(model => (
                                    <div key={model.id} className="p-4 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="font-medium text-lg">{model.display_name}</span>
                                                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-xs">
                                                        {getLatencyIcon(model.latency_tier)}
                                                        <span className="capitalize">{model.latency_tier}</span>
                                                    </div>
                                                </div>
                                                <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">{model.description}</p>
                                                <div className="flex gap-4 text-xs text-slate-400 font-mono">
                                                    <span>In: ${model.input_cost_per_1k}/1k</span>
                                                    <span>Out: ${model.output_cost_per_1k}/1k</span>
                                                    <span>ID: {model.model_id}</span>
                                                </div>
                                            </div>

                                            <div className="flex flex-col gap-2">
                                                <button
                                                    onClick={() => handleSetDefault("GLOBAL", "all", model.id)}
                                                    className="px-3 py-1 text-xs border border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400 rounded-md hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                                                >
                                                    Set as Global Default
                                                </button>
                                                <button
                                                    onClick={() => handleSetDefault("MODULE", "chat", model.id)}
                                                    className="px-3 py-1 text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-md hover:bg-slate-50 dark:hover:bg-slate-700"
                                                >
                                                    Set as Chat Default
                                                </button>
                                                <button
                                                    onClick={() => handleSetDefault("MODULE", "workflow", model.id)}
                                                    className="px-3 py-1 text-xs border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-md hover:bg-slate-50 dark:hover:bg-slate-700"
                                                >
                                                    Set as Workflow Default
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {provider.models.length === 0 && (
                                    <div className="p-4 text-center text-sm text-slate-400 italic">
                                        No models synced. Click 'Sync Catalog' to fetch defaults.
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
