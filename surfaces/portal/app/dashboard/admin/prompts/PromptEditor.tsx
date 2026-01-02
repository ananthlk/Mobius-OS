"use client";

import React, { useState, useEffect } from "react";
import { X, Save, AlertCircle, Code, Layout, CheckCircle } from "lucide-react";
import { parsePromptConfig, reconstructPromptConfig, PromptSection } from "./PromptSectionParser";
import StringSection from "./sections/StringSection";
import ObjectSection from "./sections/ObjectSection";
import ArraySection from "./sections/ArraySection";
import GenerationConfigSection from "./sections/GenerationConfigSection";

interface Prompt {
    id: number;
    prompt_key: string;
    module_name: string;
    domain: string | null;
    mode: string | null;
    step: string | null;
    version: number;
    description: string | null;
}

interface PromptEditorProps {
    prompt: Prompt | null;
    onClose: () => void;
    onSave: () => void;
}

type ViewMode = "structured" | "raw";

export default function PromptEditor({ prompt, onClose, onSave }: PromptEditorProps) {
    const [moduleName, setModuleName] = useState("");
    const [domain, setDomain] = useState("");
    const [mode, setMode] = useState("");
    const [step, setStep] = useState("");
    const [description, setDescription] = useState("");
    const [promptConfig, setPromptConfig] = useState("");
    const [sections, setSections] = useState<PromptSection[]>([]);
    const [viewMode, setViewMode] = useState<ViewMode>("structured");
    const [error, setError] = useState<string | null>(null);
    const [jsonError, setJsonError] = useState<string | null>(null);
    const [isValidJson, setIsValidJson] = useState(false);
    const [saving, setSaving] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [rawJsonSnapshot, setRawJsonSnapshot] = useState<string>(""); // Preserve original raw JSON

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Initialize from prompt or defaults
    useEffect(() => {
        if (prompt) {
            // Editing existing prompt - fetch full details
            fetch(`${API_URL}/api/admin/prompts/${encodeURIComponent(prompt.prompt_key)}`)
                .then(res => {
                    if (!res.ok) {
                        return res.text().then(text => {
                            throw new Error(`Failed to fetch prompt: ${res.status} ${text}`);
                        });
                    }
                    return res.json();
                })
                .then(data => {
                    if (!data.prompt_config) {
                        console.error("No prompt_config in response:", data);
                        setError("Prompt configuration not found in response");
                        return;
                    }
                    setModuleName(data.module_name);
                    setDomain(data.domain || "");
                    setMode(data.mode || "");
                    setStep(data.step || "");
                    setDescription(data.description || "");
                    
                    // Parse into sections
                    const parsedSections = parsePromptConfig(data.prompt_config);
                    setSections(parsedSections);
                    
                    // Also set raw JSON
                    const configStr = JSON.stringify(data.prompt_config, null, 2);
                    setPromptConfig(configStr);
                    setRawJsonSnapshot(configStr); // Preserve original order
                    validateJSON(configStr);
                })
                .catch(err => {
                    console.error("Failed to fetch prompt", err);
                    setError(err.message || "Failed to load prompt details");
                });
        } else {
            // Creating new prompt - set defaults
            setModuleName("");
            setDomain("");
            setMode("");
            setStep("");
            setDescription("");
            const defaultConfig = {
                "ROLE": "You are a helpful AI assistant.",
                "CONTEXT": "Provide context for the prompt here.",
                "GENERATION_CONFIG": {
                    "temperature": 0.7,
                    "max_output_tokens": 8192,
                    "top_p": 0.95,
                    "top_k": 40
                }
            };
            const configStr = JSON.stringify(defaultConfig, null, 2);
            setPromptConfig(configStr);
            const parsedSections = parsePromptConfig(defaultConfig);
            setSections(parsedSections);
            validateJSON(configStr);
        }
    }, [prompt, API_URL]);

    // Sync sections to raw JSON when sections change (but only if user is actively in structured mode)
    // We skip this auto-sync to avoid reordering when user is editing in raw mode
    // The sync happens explicitly when switching views instead
    // useEffect(() => {
    //     if (sections.length > 0 && viewMode === "structured") {
    //         try {
    //             const reconstructed = reconstructPromptConfig(sections);
    //             const jsonStr = JSON.stringify(reconstructed, null, 2);
    //             setPromptConfig(jsonStr);
    //             validateJSON(jsonStr);
    //         } catch (e) {
    //             console.error("Failed to reconstruct JSON from sections", e);
    //         }
    //     }
    // }, [sections, viewMode]);

    // Sync raw JSON to sections when raw JSON changes
    const syncRawToSections = (jsonStr: string) => {
        try {
            const parsed = JSON.parse(jsonStr);
            const parsedSections = parsePromptConfig(parsed);
            setSections(parsedSections);
        } catch (e) {
            // Invalid JSON, don't update sections
        }
    };

    const validateJSON = (jsonString: string | undefined): boolean => {
        if (!jsonString || typeof jsonString !== 'string' || jsonString.trim() === "") {
            setJsonError(null);
            setIsValidJson(false);
            return false;
        }
        try {
            JSON.parse(jsonString);
            setJsonError(null);
            setIsValidJson(true);
            return true;
        } catch (e: any) {
            const errorMsg = e?.message || "Invalid JSON";
            setJsonError(errorMsg);
            setIsValidJson(false);
            return false;
        }
    };

    const handleSectionChange = (sectionKey: string, newValue: any) => {
        setSections(prev => prev.map(section => 
            section.key === sectionKey 
                ? { ...section, value: newValue }
                : section
        ));
    };

    const handleSave = async () => {
        setError(null);
        setSuccessMessage(null);

        // Get the final config (from raw JSON if in raw mode, or reconstruct from sections)
        let config;
        try {
            if (viewMode === "raw") {
                config = JSON.parse(promptConfig);
            } else {
                config = reconstructPromptConfig(sections);
            }
        } catch (e: any) {
            setError("Invalid JSON format. Please check your prompt configuration.");
            return;
        }

        // Validate required fields
        if (!moduleName.trim()) {
            setError("Module name is required");
            return;
        }
        if (!domain.trim()) {
            setError("Domain is required");
            return;
        }
        if (!mode.trim()) {
            setError("Mode is required");
            return;
        }
        if (!step.trim()) {
            setError("Step is required");
            return;
        }

        setSaving(true);

        try {
            if (prompt) {
                // Update existing prompt
                const res = await fetch(`${API_URL}/api/admin/prompts/${prompt.prompt_key}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "X-User-ID": "admin"
                    },
                    body: JSON.stringify({
                        prompt_config: config,
                        change_reason: "Updated via admin UI"
                    })
                });

                if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || "Failed to update prompt");
                }
                
                const responseData = await res.json();
                const newVersion = responseData.version || "updated";
                setSuccessMessage(`✅ Prompt updated successfully! New version: ${newVersion}`);
            } else {
                // Create new prompt
                const res = await fetch(`${API_URL}/api/admin/prompts`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-User-ID": "admin"
                    },
                    body: JSON.stringify({
                        module_name: moduleName.trim(),
                        domain: domain.trim(),
                        mode: mode.trim(),
                        step: step.trim(),
                        prompt_config: config,
                        description: description.trim() || null
                    })
                });

                if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || "Failed to create prompt");
                }
                
                const responseData = await res.json();
                setSuccessMessage(`✅ Prompt created successfully! (ID: ${responseData.id})`);
            }

            // Wait a moment to show success message, then refresh and close
            setTimeout(() => {
                onSave();
                onClose();
            }, 1500);
        } catch (err: any) {
            setError(err.message || "Failed to save prompt");
            setSaving(false);
        }
    };

    const renderSection = (section: PromptSection) => {
        if (section.key === "GENERATION_CONFIG") {
            return (
                <GenerationConfigSection
                    key={section.key}
                    sectionKey={section.key}
                    value={section.value}
                    description={section.description}
                    onChange={(value) => handleSectionChange(section.key, value)}
                    onValidationChange={(isValid) => {
                        if (!isValid) setIsValidJson(false);
                    }}
                />
            );
        }

        switch (section.type) {
            case 'string':
                // Ensure string value
                const stringValue = typeof section.value === 'string' 
                    ? section.value 
                    : String(section.value || '');
                return (
                    <StringSection
                        key={section.key}
                        sectionKey={section.key}
                        value={stringValue}
                        description={section.description}
                        onChange={(value) => handleSectionChange(section.key, value)}
                        onValidationChange={(isValid) => {
                            if (!isValid) setIsValidJson(false);
                        }}
                    />
                );
            case 'array':
                // Ensure array values are strings (for CONSTRAINTS)
                const arrayValue = Array.isArray(section.value) 
                    ? section.value.map(v => typeof v === 'string' ? v : String(v))
                    : [];
                return (
                    <ArraySection
                        key={section.key}
                        sectionKey={section.key}
                        value={arrayValue}
                        description={section.description}
                        onChange={(value) => handleSectionChange(section.key, value)}
                        onValidationChange={(isValid) => {
                            if (!isValid) setIsValidJson(false);
                        }}
                    />
                );
            case 'object':
            default:
                return (
                    <ObjectSection
                        key={section.key}
                        sectionKey={section.key}
                        value={section.value}
                        description={section.description}
                        onChange={(value) => handleSectionChange(section.key, value)}
                        onValidationChange={(isValid) => {
                            if (!isValid) setIsValidJson(false);
                        }}
                    />
                );
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <h2 className="text-2xl font-bold text-gray-900">
                        {prompt ? "Edit Prompt" : "Create Prompt"}
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {error && (
                        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
                            <AlertCircle className="w-5 h-5" />
                            <span>{error}</span>
                        </div>
                    )}
                    {successMessage && (
                        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700">
                            <CheckCircle className="w-5 h-5" />
                            <span>{successMessage}</span>
                        </div>
                    )}

                    {/* Basic Info */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Module Name *
                            </label>
                            <input
                                type="text"
                                value={moduleName}
                                onChange={(e) => setModuleName(e.target.value)}
                                disabled={!!prompt}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                                placeholder="e.g., workflow, chat"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Domain *
                            </label>
                            <input
                                type="text"
                                value={domain}
                                onChange={(e) => setDomain(e.target.value)}
                                disabled={!!prompt}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                                placeholder="e.g., eligibility, crm"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Mode *
                            </label>
                            <input
                                type="text"
                                value={mode}
                                onChange={(e) => setMode(e.target.value)}
                                disabled={!!prompt}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                                placeholder="e.g., TABULA_RASA, EVIDENCE_BASED"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Step *
                            </label>
                            <input
                                type="text"
                                value={step}
                                onChange={(e) => setStep(e.target.value)}
                                disabled={!!prompt}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100"
                                placeholder="e.g., gate, clarification, planning"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            rows={2}
                            placeholder="Brief description of this prompt..."
                        />
                    </div>

                    {/* View Mode Tabs */}
                    <div className="border-b border-gray-200">
                        <div className="flex gap-1">
                            <button
                                onClick={() => {
                                    // Always sync raw JSON to sections when switching to structured
                                    // This ensures sections reflect the current raw JSON state
                                    if (promptConfig && promptConfig.trim() !== "") {
                                        syncRawToSections(promptConfig);
                                    }
                                    setViewMode("structured");
                                }}
                                className={`flex items-center gap-2 px-4 py-2 font-medium text-sm transition-colors ${
                                    viewMode === "structured"
                                        ? "text-indigo-600 border-b-2 border-indigo-600"
                                        : "text-gray-500 hover:text-gray-700"
                                }`}
                            >
                                <Layout className="w-4 h-4" />
                                Structured View
                            </button>
                            <button
                                onClick={() => {
                                    setViewMode("raw");
                                    // Restore the original raw JSON snapshot if it exists
                                    // This preserves the exact order the user typed
                                    if (rawJsonSnapshot && rawJsonSnapshot.trim() !== "") {
                                        setPromptConfig(rawJsonSnapshot);
                                        validateJSON(rawJsonSnapshot);
                                    } else if (!promptConfig || promptConfig.trim() === "") {
                                        // Only reconstruct if no raw JSON exists
                                        if (sections.length > 0) {
                                            const reconstructed = reconstructPromptConfig(sections);
                                            const jsonStr = JSON.stringify(reconstructed, null, 2);
                                            setPromptConfig(jsonStr);
                                            validateJSON(jsonStr);
                                        }
                                    }
                                }}
                                className={`flex items-center gap-2 px-4 py-2 font-medium text-sm transition-colors ${
                                    viewMode === "raw"
                                        ? "text-indigo-600 border-b-2 border-indigo-600"
                                        : "text-gray-500 hover:text-gray-700"
                                }`}
                            >
                                <Code className="w-4 h-4" />
                                Raw JSON
                            </button>
                        </div>
                    </div>

                    {/* Prompt Config - Structured View */}
                    {viewMode === "structured" && (
                        <div className="space-y-4">
                            {sections.length === 0 ? (
                                <div className="text-center py-8 text-gray-500">
                                    No sections found. Switch to Raw JSON view to edit.
                                </div>
                            ) : (
                                sections.map(section => renderSection(section))
                            )}
                        </div>
                    )}

                    {/* Prompt Config - Raw JSON View */}
                    {viewMode === "raw" && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Prompt Configuration (JSON) *
                            </label>
                            <textarea
                                value={promptConfig}
                                onChange={(e) => {
                                    const value = e.target.value || "";
                                    setPromptConfig(value);
                                    // Update snapshot whenever user types in raw mode
                                    setRawJsonSnapshot(value);
                                    setError(null);
                                    validateJSON(value);
                                }}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                                rows={20}
                                spellCheck={false}
                            />
                            <p className="mt-1 text-xs">
                                {!promptConfig || promptConfig.trim() === "" ? (
                                    <span className="text-gray-500">Enter JSON configuration</span>
                                ) : isValidJson ? (
                                    <span className="text-green-600">✓ Valid JSON</span>
                                ) : (
                                    <span className="text-red-600">
                                        ✗ Invalid JSON {jsonError && `: ${jsonError}`}
                                    </span>
                                )}
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
                    <button
                        onClick={handleSave}
                        disabled={saving || !isValidJson || !moduleName.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                        <Save className="w-4 h-4" />
                        {saving ? "Saving..." : "Save"}
                    </button>
                </div>
            </div>
        </div>
    );
}
