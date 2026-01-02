"use client";

import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, Settings, Zap } from "lucide-react";

interface GenerationConfigSectionProps {
    sectionKey: string;
    value: any;
    description?: string;
    onChange: (value: any) => void;
    onValidationChange?: (isValid: boolean) => void;
}

const PRESETS = {
    conservative: {
        temperature: 0.3,
        max_output_tokens: 4096,
        top_p: 0.9,
        top_k: 20
    },
    balanced: {
        temperature: 0.7,
        max_output_tokens: 8192,
        top_p: 0.95,
        top_k: 40
    },
    creative: {
        temperature: 1.0,
        max_output_tokens: 8192,
        top_p: 0.98,
        top_k: 60
    }
};

export default function GenerationConfigSection({
    sectionKey,
    value,
    description,
    onChange,
    onValidationChange
}: GenerationConfigSectionProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    const [config, setConfig] = useState<{
        temperature: number;
        max_output_tokens: number;
        top_p: number;
        top_k: number;
        [key: string]: any;
    }>({
        temperature: value?.temperature ?? 0.7,
        max_output_tokens: value?.max_output_tokens ?? 8192,
        top_p: value?.top_p ?? 0.95,
        top_k: value?.top_k ?? 40,
        ...value
    });

    useEffect(() => {
        onChange(config);
        onValidationChange?.(true);
    }, [config]);

    const handleChange = (key: string, newValue: number) => {
        setConfig((prev: typeof config) => ({ ...prev, [key]: newValue }));
    };

    const applyPreset = (presetName: keyof typeof PRESETS) => {
        setConfig((prev: typeof config) => ({ ...prev, ...PRESETS[presetName] }));
    };

    return (
        <div className="border border-gray-200 rounded-lg bg-white">
            {/* Section Header */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <Settings className="w-5 h-5 text-blue-600" />
                    <div>
                        <h3 className="font-semibold text-gray-900">{sectionKey}</h3>
                        {description && (
                            <p className="text-xs text-gray-500 mt-0.5">{description}</p>
                        )}
                    </div>
                </div>
                {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
            </div>

            {/* Section Content */}
            {isExpanded && (
                <div className="p-4 border-t border-gray-200 space-y-4">
                    {/* Presets */}
                    <div className="flex gap-2">
                        <button
                            onClick={() => applyPreset('conservative')}
                            className="px-3 py-1.5 text-xs font-medium bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                        >
                            Conservative
                        </button>
                        <button
                            onClick={() => applyPreset('balanced')}
                            className="px-3 py-1.5 text-xs font-medium bg-indigo-100 hover:bg-indigo-200 rounded-lg transition-colors"
                        >
                            Balanced
                        </button>
                        <button
                            onClick={() => applyPreset('creative')}
                            className="px-3 py-1.5 text-xs font-medium bg-purple-100 hover:bg-purple-200 rounded-lg transition-colors"
                        >
                            Creative
                        </button>
                    </div>

                    {/* Temperature */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Temperature: {config.temperature.toFixed(2)}
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={config.temperature}
                            onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
                            className="w-full"
                        />
                            <div className="flex justify-between text-xs text-gray-500 mt-1">
                                <span>Focused (0.0)</span>
                                <span>Balanced (1.0)</span>
                                <span>Creative (2.0)</span>
                            </div>
                    </div>

                    {/* Max Output Tokens */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Max Output Tokens: {config.max_output_tokens}
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="32768"
                            step="512"
                            value={config.max_output_tokens}
                            onChange={(e) => handleChange('max_output_tokens', parseInt(e.target.value) || 8192)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        />
                    </div>

                    {/* Top P */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Top P: {config.top_p.toFixed(2)}
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={config.top_p}
                            onChange={(e) => handleChange('top_p', parseFloat(e.target.value))}
                            className="w-full"
                        />
                    </div>

                    {/* Top K */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Top K: {config.top_k}
                        </label>
                        <input
                            type="number"
                            min="1"
                            max="100"
                            value={config.top_k}
                            onChange={(e) => handleChange('top_k', parseInt(e.target.value) || 40)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

