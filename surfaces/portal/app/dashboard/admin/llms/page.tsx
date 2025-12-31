"use client";

import React, { useState, useEffect } from "react";
import { Plus, Shield, CheckCircle, Key, Server, RefreshCw, Power } from "lucide-react";
import GovernanceBoard from "./GovernanceBoard";

// Types
interface Provider {
    id: number;
    name: string;
    provider_type: string;
    base_url?: string;
    is_active: boolean;
}

const ProviderCard = ({
    provider,
    onTest,
    onManage,
    onDelete,
    onBenchmark,
    onToggleModel,
    catalog
}: {
    provider: Provider;
    onTest: (p: Provider) => void;
    onManage: (p: Provider) => void;
    onDelete: (p: Provider) => void;
    onBenchmark: (modelId: number) => void;
    onToggleModel: (modelId: number, active: boolean) => void;
    catalog: any[];
}) => {
    const [expanded, setExpanded] = useState(false);

    // Find models for this provider
    const providerCatalog = catalog.find(c => c.name === provider.name);
    const models = providerCatalog ? providerCatalog.models : [];

    const getLatencyIcon = (tier: string) => {
        switch (tier) {
            case "fast": return <span className="text-yellow-500">⚡</span>;
            case "balanced": return <span className="text-blue-500">⚖️</span>;
            default: return <span className="text-purple-500">🧠</span>;
        }
    };

    return (
        <div className="group rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 dark:hover:border-indigo-500 transition-all shadow-sm overflow-hidden">
            <div className="p-5 flex justify-between items-start">
                <div className="flex gap-4">
                    <div className={`p-3 rounded-lg ${provider.provider_type === 'vertex' ? 'bg-blue-50 text-blue-600' : 'bg-green-50 text-green-600'}`}>
                        <Server size={20} />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg">{provider.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500">
                                {provider.provider_type}
                            </span>
                            {provider.base_url && (
                                <span className="text-xs text-slate-400 font-mono">{provider.base_url}</span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${provider.is_active ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400' : 'bg-gray-100 text-gray-500'}`}>
                        <CheckCircle size={14} />
                        {provider.is_active ? 'Connected' : 'Inactive'}
                    </div>

                    <button onClick={() => onTest(provider)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg border border-transparent hover:border-blue-200 transition-all" title="Test Connection">
                        <CheckCircle size={18} />
                    </button>
                    <button onClick={() => onManage(provider)} className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg border border-transparent hover:border-slate-200 transition-all" title="Manage Secrets">
                        <Key size={18} />
                    </button>
                    <button onClick={() => onDelete(provider)} className="p-2 text-red-400 hover:bg-red-50 hover:text-red-600 rounded-lg border border-transparent hover:border-red-200 transition-all" title="Delete Provider">
                        <Plus size={18} className="rotate-45" /> {/* Reuse Plus as Close/Delete */}
                    </button>
                </div>
            </div>

            {/* Inventory Toggle */}
            <div
                className="px-5 py-2 bg-slate-50 dark:bg-slate-900/30 border-t border-slate-100 dark:border-slate-700/50 flex justify-between items-center cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Inventory ({models.length} Models)
                </span>
                <span className="text-xs text-indigo-500 font-medium">
                    {expanded ? "Hide Models" : "View Models"}
                </span>
            </div>

            {/* Expandable Inventory */}
            {expanded && (
                <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50">
                    <div className="grid grid-cols-[2fr_1fr_1fr_1fr_0.5fr] px-6 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700/50">
                        <span>Model Name</span>
                        <span>Latency</span>
                        <span>Input Cost</span>
                        <span>Output Cost</span>
                        <span className="text-right">Action</span>
                    </div>
                    {models.length > 0 ? models.map((m: any) => (
                        <div key={m.id} className={`grid grid-cols-[2fr_1fr_1fr_1fr_0.5fr] px-6 py-3 text-sm border-b border-slate-100 dark:border-slate-700/50 hover:bg-white dark:hover:bg-slate-800 transition-colors ${m.is_active ? '' : 'opacity-60 bg-slate-50 dark:bg-slate-900/40'}`}>
                            <div>
                                <div className="flex items-center gap-2">
                                    <div className={`font-medium ${m.is_recommended ? 'text-slate-700 dark:text-slate-200' : 'text-slate-500 dark:text-slate-500'}`}>{m.display_name}</div>
                                    {m.is_recommended && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-medium">
                                            Verified {m.last_verified_at ? new Date(m.last_verified_at).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' }) : ''}
                                        </span>
                                    )}
                                    {!m.is_active && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-500 font-medium">Inactive</span>
                                    )}
                                </div>
                                <div className="font-mono text-xs text-slate-400">{m.model_id}</div>
                            </div>
                            <div className="flex items-center gap-2">
                                {m.is_active ? getLatencyIcon(m.latency_tier) : <span className="grayscale opacity-50">{getLatencyIcon(m.latency_tier)}</span>}
                                <span className="capitalize text-slate-500">
                                    {m.last_latency_ms ? `${m.last_latency_ms} ms` : m.latency_tier}
                                </span>
                            </div>
                            <div className="font-mono text-slate-500">${m.input_cost_per_1k}/1k</div>
                            <div className="font-mono text-slate-500">${m.output_cost_per_1k}/1k</div>
                            <div className="flex justify-end gap-2">
                                {m.is_active ? (
                                    <>
                                        <button
                                            onClick={() => onBenchmark(m.id)}
                                            className="p-1.5 text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                                            title="Benchmark Latency"
                                        >
                                            <RefreshCw size={14} />
                                        </button>
                                        <button
                                            onClick={() => onToggleModel(m.id, false)}
                                            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                            title="Deactivate Model"
                                        >
                                            <Power size={14} />
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={() => onToggleModel(m.id, true)}
                                        className="p-1.5 text-slate-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                                        title="Activate Model"
                                    >
                                        <Plus size={14} />
                                    </button>
                                )}
                            </div>
                        </div>
                    )) : (
                        <div className="p-6 text-sm text-slate-400 italic text-center col-span-5">No models synced. Please reset defaults in Governance Board.</div>
                    )}
                </div>
            )}
        </div>
    );
};

export default function LLMAdminPage() {
    const [providers, setProviders] = useState<Provider[]>([]);
    const [catalog, setCatalog] = useState<any[]>([]);

    // Key Management State
    const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
    const [keys, setKeys] = useState<{ key: string; value: string }[]>([]);

    // Vertex specific defaults
    const [vProjectId, setVProjectId] = useState("");
    const [vLocation, setVLocation] = useState("us-central1");
    // Generic default
    const [apiKey, setApiKey] = useState("");

    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);

    // Form State
    const [newName, setNewName] = useState("");
    const [newType, setNewType] = useState("vertex"); // default
    const [newBaseUrl, setNewBaseUrl] = useState("");

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchData = async () => {
        if (providers.length === 0) setLoading(true);
        try {
            const [provRes, catRes] = await Promise.all([
                fetch(`${API_URL}/api/admin/ai/providers`),
                fetch(`${API_URL}/api/admin/ai/catalog`)
            ]);

            if (provRes.ok) setProviders(await provRes.json());
            if (catRes.ok) setCatalog(await catRes.json());

        } catch (e) {
            console.error("Failed to fetch data", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleCreate = async () => {
        try {
            const res = await fetch(`${API_URL}/api/admin/ai/providers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: newName,
                    provider_type: newType,
                    base_url: newBaseUrl || null,
                }),
            });
            if (res.ok) {
                setShowAddModal(false);
                fetchData();
                setNewName("");
            }
        } catch (e) {
            alert("Failed to create provider");
        }
    };

    const handleDelete = async (p: Provider) => {
        if (!confirm(`Are you sure you want to delete ${p.name}? This will remove all associated models and configs.`)) return;

        try {
            const res = await fetch(`${API_URL}/api/admin/ai/providers/${p.id}`, {
                method: "DELETE"
            });
            if (res.ok) {
                fetchData();
            } else {
                alert("Failed to delete provider");
            }
        } catch (e) {
            console.error(e);
            alert("Delete failed");
        }
    };

    const handleBenchmark = async (modelId: number) => {
        try {
            const res = await fetch(`${API_URL}/api/admin/ai/models/${modelId}/benchmark`, {
                method: "POST"
            });
            const data = await res.json();
            if (data.status === "success") {
                fetchData(); // Refresh to show new latency
            } else {
                alert("Benchmark failed");
            }
        } catch (e) {
            alert("Benchmark failed: Network Error");
        }
    };

    const handleToggle = async (modelId: number, active: boolean) => {
        try {
            await fetch(`${API_URL}/api/admin/ai/models/${modelId}/toggle`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ is_active: active })
            });
            fetchData();
        } catch (e) {
            alert("Toggle failed");
        }
    };

    const openKeyModal = (p: Provider) => {
        setSelectedProvider(p);
        // Reset fields
        setVProjectId("");
        setVLocation("us-central1");
        setApiKey("");
    };

    const handleSaveSecret = async (key: string, value: string) => {
        if (!selectedProvider) return;
        try {
            await fetch(`${API_URL}/api/admin/ai/secrets`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    provider_id: selectedProvider.id,
                    key: key,
                    value: value,
                    is_secret: key !== "location" // location is public config
                }),
            });
        } catch (e) {
            console.error(e);
        }
    };

    const handleSubmitKeys = async () => {
        if (!selectedProvider) return;

        if (selectedProvider.provider_type === "vertex") {
            if (vProjectId) await handleSaveSecret("project_id", vProjectId);
            if (vLocation) await handleSaveSecret("location", vLocation);
            if (apiKey) await handleSaveSecret("api_key", apiKey);
        } else {
            if (apiKey) await handleSaveSecret("api_key", apiKey);
        }
        alert("Configuration Saved!");
        setSelectedProvider(null);
    };

    const handleTestConnection = async (p: Provider) => {
        try {
            const res = await fetch(`${API_URL}/api/admin/ai/providers/test`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ provider_id: p.id })
            });
            const data = await res.json();
            if (data.status === "success") {
                alert(`✅ Success!\nModel: ${data.model}\nReply: ${data.reply}`);
            } else {
                alert(`❌ Failed: ${data.message}`);
            }
        } catch (e) {
            alert("Network Error");
        }
    };

    return (
        <div className="h-full w-full p-8 overflow-y-auto bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100">
            <header className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
                        AI Gateway
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Manage your LLM connections and secure credentials.
                    </p>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-md transition-all"
                >
                    <Plus size={18} />
                    Add Provider
                </button>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="p-6 rounded-2xl bg-white dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-xl text-green-600 dark:text-green-400">
                            <Server size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-500">Active Providers</p>
                            <h3 className="text-2xl font-bold">{providers.filter(p => p.is_active).length}</h3>
                        </div>
                    </div>
                </div>
                <div className="p-6 rounded-2xl bg-white dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-xl text-blue-600 dark:text-blue-400">
                            <Shield size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-500">Encryption Status</p>
                            <h3 className="text-2xl font-bold">AES-256</h3>
                        </div>
                    </div>
                </div>
                <div className="p-6 rounded-2xl bg-white dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl text-purple-600 dark:text-purple-400">
                            <Key size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-500">Managed Keys</p>
                            <h3 className="text-2xl font-bold">Secure</h3>
                        </div>
                    </div>
                </div>
            </div>

            {/* 1. Connections Section */}
            <section className="mb-12 border-b border-slate-200 dark:border-slate-800 pb-12">
                <div className="mb-6">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        <Server className="text-blue-500" size={24} />
                        Provider Connections
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 max-w-2xl">
                        Configure the "Pipes". Add your API Keys and Project IDs here.
                        Expand the cards to view the **Inventory** of available models.
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-4">
                    {loading ? (
                        <div className="text-center py-12 text-slate-500">Loading Configuration...</div>
                    ) : (
                        providers.map((provider) => (
                            <ProviderCard
                                key={provider.id}
                                provider={provider}
                                onTest={handleTestConnection}
                                onManage={openKeyModal}
                                onDelete={handleDelete}
                                onBenchmark={handleBenchmark}
                                onToggleModel={handleToggle}
                                catalog={catalog}
                            />
                        ))
                    )}
                </div>
            </section>

            {/* 2. Governance Board */}
            <div className="mb-12">
                <GovernanceBoard />
            </div>

            {/* Add Modal */}
            {showAddModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-2xl border border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-bold mb-4">Add AI Provider</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Name (ID)</label>
                                <input
                                    type="text"
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                    placeholder="e.g. vertex-prod"
                                    className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Type</label>
                                <select
                                    value={newType}
                                    onChange={(e) => setNewType(e.target.value)}
                                    className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                >
                                    <option value="vertex">Google Vertex AI</option>
                                    <option value="openai_compatible">OpenAI / Groq / Ollama</option>
                                </select>
                            </div>
                            {newType === "openai_compatible" && (
                                <div>
                                    <label className="block text-sm font-medium mb-1">Base URL (Optional)</label>
                                    <input
                                        type="text"
                                        value={newBaseUrl}
                                        onChange={(e) => setNewBaseUrl(e.target.value)}
                                        placeholder="https://api.groq.com/openai/v1"
                                        className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                    />
                                </div>
                            )}
                        </div>
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowAddModal(false)}
                                className="px-4 py-2 text-slate-500 hover:text-slate-700"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium"
                            >
                                Create Provider
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Key Management Modal */}
            {selectedProvider && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                    <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-2xl border border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-bold mb-1">Configure {selectedProvider.name}</h2>
                        <p className="text-sm text-slate-500 mb-6">Secrets are encrypted before storage (AES-256).</p>

                        <div className="space-y-4">
                            {selectedProvider.provider_type === "vertex" ? (
                                <>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Google Cloud Project ID</label>
                                        <input
                                            type="text"
                                            value={vProjectId}
                                            onChange={(e) => setVProjectId(e.target.value)}
                                            placeholder="mobiusos-482817"
                                            className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Region (Location)</label>
                                        <input
                                            type="text"
                                            value={vLocation}
                                            onChange={(e) => setVLocation(e.target.value)}
                                            placeholder="us-central1"
                                            className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                        />
                                    </div>
                                    <div className="relative py-2">
                                        <div className="absolute inset-0 flex items-center">
                                            <span className="w-full border-t border-slate-200 dark:border-slate-700" />
                                        </div>
                                        <div className="relative flex justify-center text-xs uppercase">
                                            <span className="bg-white dark:bg-slate-800 px-2 text-slate-500">Or use AI Studio</span>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-1">API Key (Optional)</label>
                                        <input
                                            type="password"
                                            value={apiKey}
                                            onChange={(e) => setApiKey(e.target.value)}
                                            placeholder="AQ..."
                                            className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                        />
                                        <p className="text-xs text-slate-500 mt-1">Overrides Project ID for simple auth.</p>
                                    </div>
                                </>
                            ) : (
                                <div>
                                    <label className="block text-sm font-medium mb-1">API Key</label>
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder="sk-..."
                                        className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent"
                                    />
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setSelectedProvider(null)}
                                className="px-4 py-2 text-slate-500 hover:text-slate-700"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmitKeys}
                                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium"
                            >
                                Save Configuration
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
