"use client";

import React, { useState, useEffect } from "react";
import { Shield, Save, RefreshCw } from "lucide-react";

interface Model {
    id: number;
    model_id: string;
    display_name: string;
    provider_id: number;
}

interface ProviderCatalog {
    id: number;
    name: string;
    models: Model[];
}

interface GovernanceRules {
    [key: string]: { model_id: string; provider_name: string } | null;
}

export default function GovernanceBoard() {
    const [catalog, setCatalog] = useState<ProviderCatalog[]>([]);
    const [rules, setRules] = useState<GovernanceRules>({});
    const [loading, setLoading] = useState(true);

    // Staging changes
    const [stagedRules, setStagedRules] = useState<{ [key: string]: number }>({}); // module -> model_pk
    const [saving, setSaving] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchData = async () => {
        setLoading(true);
        try {
            const [catRes, rulesRes] = await Promise.all([
                fetch(`${API_URL}/api/admin/ai/catalog`),
                fetch(`${API_URL}/api/admin/ai/rules`)
            ]);

            if (catRes.ok && rulesRes.ok) {
                setCatalog(await catRes.json());
                setRules(await rulesRes.json());
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            await fetch(`${API_URL}/api/admin/ai/catalog/sync`, { method: "POST" });
            // After sync, refresh data to get new models
            await fetchData();
        } catch (e) {
            alert("Sync failed");
        } finally {
            setIsSyncing(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleChange = (module: string, modelId: string) => {
        // Find PK
        let modelPk = 0;
        catalog.forEach(p => {
            const m = p.models.find(x => x.model_id === modelId);
            if (m) modelPk = m.id;
        });

        if (modelPk) {
            setStagedRules(prev => ({ ...prev, [module]: modelPk }));
        }
    };

    const handleSave = async (module: string) => {
        const modelPk = stagedRules[module];
        if (!modelPk) return;

        setSaving(true);
        try {
            const ruleType = module === "GLOBAL" ? "GLOBAL" : "MODULE";
            const moduleId = module === "GLOBAL" ? "all" : module;

            await fetch(`${API_URL}/api/admin/ai/defaults`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    rule_type: ruleType,
                    module_id: moduleId,
                    model_id: modelPk
                })
            });

            // Clear stage and refresh
            const newStaged = { ...stagedRules };
            delete newStaged[module];
            setStagedRules(newStaged);
            fetchData();

        } catch (e) {
            alert("Failed to save rule");
        } finally {
            setSaving(false);
        }
    };

    const contexts = ["GLOBAL", "chat", "workflow", "coding"]; // Defined contexts

    // Flatten models for dropdown
    const allModels = catalog.flatMap(p => p.models.map(m => ({ ...m, provider: p.name })));

    if (loading) return <div className="text-center py-8 text-slate-500">Loading Governance Matrix...</div>;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <Shield className="text-purple-500" size={24} />
                        Governance Board
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400">
                        Define the AI Strategy. Map Models to Contexts.
                    </p>
                </div>
                <button
                    onClick={handleSync}
                    disabled={isSyncing}
                    className={`p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-all ${isSyncing ? 'animate-spin text-indigo-500' : ''}`}
                    title="Sync Catalog (Discover New Models)"
                >
                    <RefreshCw size={18} />
                </button>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-50 dark:bg-slate-900/50 text-xs uppercase tracking-wider text-slate-500">
                            <th className="p-4 border-b dark:border-slate-700">Context</th>
                            <th className="p-4 border-b dark:border-slate-700">Current Strategy</th>
                            <th className="p-4 border-b dark:border-slate-700">Target Model</th>
                            <th className="p-4 border-b dark:border-slate-700 w-24">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {contexts.map(ctx => {
                            const current = rules[ctx];
                            const staged = stagedRules[ctx];

                            // Find current model obj
                            const currentModel = current ? allModels.find(m => m.model_id === current.model_id) : null;
                            const isGlobal = ctx === "GLOBAL";

                            return (
                                <tr key={ctx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                    <td className="p-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`
                                                w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold
                                                ${isGlobal ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'}
                                            `}>
                                                {ctx.substring(0, 2).toUpperCase()}
                                            </div>
                                            <div>
                                                <div className="font-semibold capitalize">{ctx.toLowerCase()}</div>
                                                <div className="text-xs text-slate-400">
                                                    {isGlobal ? "System Fallback" : "Module Override"}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="p-4">
                                        {current ? (
                                            <div className="flex items-center gap-2">
                                                <span className="font-mono text-sm">{current.model_id}</span>
                                                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500">
                                                    {current.provider_name}
                                                </span>
                                            </div>
                                        ) : (
                                            <span className="text-slate-400 italic text-sm">Inherits Global</span>
                                        )}
                                    </td>
                                    <td className="p-4">
                                        <select
                                            className="w-full max-w-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                                            onChange={(e) => handleChange(ctx, e.target.value)}
                                            value={staged ? allModels.find(m => m.id === staged)?.model_id : (current?.model_id || "")}
                                        >
                                            <option value="" disabled>Select Strategy...</option>
                                            {catalog.map(provider => (
                                                <optgroup key={provider.id} label={provider.name}>
                                                    {provider.models.map(m => (
                                                        <option key={m.id} value={m.model_id}>
                                                            {m.display_name} ({m.model_id})
                                                        </option>
                                                    ))}
                                                </optgroup>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="p-4">
                                        {staged && (
                                            <button
                                                onClick={() => handleSave(ctx)}
                                                disabled={saving}
                                                className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition-colors shadow-sm"
                                            >
                                                <Save size={14} />
                                                Save
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
