"use client";

import React, { useState, useEffect } from "react";
import { Plus, Search, Filter, FileText, Copy, Check } from "lucide-react";
import PromptCard from "./PromptCard";
import PromptEditor from "./PromptEditor";
import PromptRefiner from "./PromptRefiner";
import VersionHistory from "./VersionHistory";

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

export default function PromptsPage() {
    const [prompts, setPrompts] = useState<Prompt[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [filterModule, setFilterModule] = useState<string>("");
    const [filterDomain, setFilterDomain] = useState<string>("");
    const [filterMode, setFilterMode] = useState<string>("");
    const [filterStep, setFilterStep] = useState<string>("");
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
    const [refiningPrompt, setRefiningPrompt] = useState<Prompt | null>(null);
    const [viewingHistory, setViewingHistory] = useState<string | null>(null);
    const [copiedKey, setCopiedKey] = useState<string | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const fetchPrompts = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterModule) params.append("module_name", filterModule);
            if (filterDomain) params.append("domain", filterDomain);
            if (filterMode) params.append("mode", filterMode);
            if (filterStep) params.append("step", filterStep);
            params.append("active_only", "true");

            const res = await fetch(`${API_URL}/api/admin/prompts?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                setPrompts(data);
            }
        } catch (e) {
            console.error("Failed to fetch prompts", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPrompts();
    }, [filterModule, filterDomain, filterMode, filterStep]);

    const handleCreate = () => {
        setEditingPrompt(null);
        setShowCreateModal(true);
    };

    const handleEdit = (prompt: Prompt) => {
        setEditingPrompt(prompt);
        setShowCreateModal(true);
    };

    const handleRefine = (prompt: Prompt) => {
        setRefiningPrompt(prompt);
    };

    const handleViewHistory = (promptKey: string) => {
        setViewingHistory(promptKey);
    };

    const handleCopyKey = (key: string) => {
        navigator.clipboard.writeText(key);
        setCopiedKey(key);
        setTimeout(() => setCopiedKey(null), 2000);
    };

    const handleCloseModal = () => {
        setShowCreateModal(false);
        setEditingPrompt(null);
        fetchPrompts();
    };

    const handleCloseRefiner = () => {
        setRefiningPrompt(null);
        fetchPrompts();
    };

    const handleCloseHistory = () => {
        setViewingHistory(null);
    };

    // Get unique values for filters
    const modules = Array.from(new Set(prompts.map(p => p.module_name))).sort();
    const domains = Array.from(new Set(prompts.map(p => p.domain).filter(Boolean))).sort();
    const modes = Array.from(new Set(prompts.map(p => p.mode).filter(Boolean))).sort();
    const steps = Array.from(new Set(prompts.map(p => p.step).filter(Boolean))).sort();

    // Filter prompts by search term
    const filteredPrompts = prompts.filter(p => {
        const matchesSearch = !searchTerm || 
            p.prompt_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
            p.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            p.module_name.toLowerCase().includes(searchTerm.toLowerCase());
        return matchesSearch;
    });

    return (
        <div className="h-full flex flex-col p-8">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">Prompt Management</h1>
                        <p className="text-gray-500">Manage and refine prompts for all agents</p>
                    </div>
                    <button
                        onClick={handleCreate}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                        <Plus size={20} />
                        Create Prompt
                    </button>
                </div>

                {/* Filters */}
                <div className="flex gap-4 items-center">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search prompts..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        />
                    </div>
                    <select
                        value={filterModule}
                        onChange={(e) => setFilterModule(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">All Modules</option>
                        {modules.map(m => (
                            <option key={m} value={m}>{m}</option>
                        ))}
                    </select>
                    <select
                        value={filterDomain}
                        onChange={(e) => setFilterDomain(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">All Domains</option>
                        {domains.map(d => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>
                    <select
                        value={filterMode}
                        onChange={(e) => setFilterMode(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">All Modes</option>
                        {modes.map(m => (
                            <option key={m} value={m}>{m}</option>
                        ))}
                    </select>
                    <select
                        value={filterStep}
                        onChange={(e) => setFilterStep(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="">All Steps</option>
                        {steps.map(s => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Prompts Grid */}
            {loading ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="text-gray-500">Loading prompts...</div>
                </div>
            ) : filteredPrompts.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="text-center">
                        <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p className="text-gray-500">No prompts found</p>
                    </div>
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredPrompts.map((prompt) => (
                            <PromptCard
                                key={prompt.id}
                                prompt={prompt}
                                onEdit={() => handleEdit(prompt)}
                                onRefine={() => handleRefine(prompt)}
                                onViewHistory={() => handleViewHistory(prompt.prompt_key)}
                                onCopyKey={() => handleCopyKey(prompt.prompt_key)}
                                copied={copiedKey === prompt.prompt_key}
                            />
                        ))}
                    </div>
                </div>
            )}

            {/* Modals */}
            {showCreateModal && (
                <PromptEditor
                    prompt={editingPrompt}
                    onClose={handleCloseModal}
                    onSave={fetchPrompts}
                />
            )}

            {refiningPrompt && (
                <PromptRefiner
                    prompt={refiningPrompt}
                    onClose={handleCloseRefiner}
                    onRefined={fetchPrompts}
                />
            )}

            {viewingHistory && (
                <VersionHistory
                    promptKey={viewingHistory}
                    onClose={handleCloseHistory}
                />
            )}
        </div>
    );
}

