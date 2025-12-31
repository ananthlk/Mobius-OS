"use client";

import React, { useState, useEffect } from "react";
import { Plus, Shield, CheckCircle, Key, Server } from "lucide-react";

// Types
interface Provider {
    id: number;
    name: string;
    provider_type: string;
    base_url?: string;
    is_active: boolean;
}

export default function LLMAdminPage() {
    const [providers, setProviders] = useState<Provider[]>([]);
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

    const fetchProviders = async () => {
        try {
            const res = await fetch(`${API_URL}/api/admin/ai/providers`);
            if (res.ok) {
                const data = await res.json();
                setProviders(data);
            }
        } catch (e) {
            console.error("Failed to fetch providers", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProviders();
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
                fetchProviders();
                setNewName("");
            }
        } catch (e) {
            alert("Failed to create provider");
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

            {/* Providers List */}
            <div className="grid grid-cols-1 gap-4">
                {loading ? (
                    <div className="text-center py-12 text-slate-500">Loading Configuration...</div>
                ) : (
                    providers.map((provider) => (
                        <div
                            key={provider.id}
                            className="group p-5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 dark:hover:border-indigo-500 transition-all shadow-sm"
                        >
                            <div className="flex justify-between items-start">
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
                                    <div className="flex items-center gap-1.5 px-3 py-1 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-full text-sm font-medium">
                                        <CheckCircle size={14} />
                                        Active
                                    </div>
                                    <button
                                        onClick={() => handleTestConnection(provider)}
                                        className="px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors border border-blue-200 dark:border-blue-800"
                                    >
                                        Test
                                    </button>
                                    <button
                                        onClick={() => openKeyModal(provider)}
                                        className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors border border-slate-200 dark:border-slate-700"
                                    >
                                        Manage Keys
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))
                )}
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
