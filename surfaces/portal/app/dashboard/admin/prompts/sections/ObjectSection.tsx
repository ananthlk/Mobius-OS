"use client";

import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, Code, Copy, Check } from "lucide-react";

interface ObjectSectionProps {
    sectionKey: string;
    value: any;
    description?: string;
    onChange: (value: any) => void;
    onValidationChange?: (isValid: boolean) => void;
}

export default function ObjectSection({
    sectionKey,
    value,
    description,
    onChange,
    onValidationChange
}: ObjectSectionProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [jsonString, setJsonString] = useState("");
    const [isValid, setIsValid] = useState(true);
    const [jsonError, setJsonError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        try {
            const formatted = JSON.stringify(value, null, 2);
            setJsonString(formatted);
            setIsValid(true);
            setJsonError(null);
        } catch (e) {
            setJsonString("");
            setIsValid(false);
        }
    }, [value]);

    const handleJsonChange = (newJson: string) => {
        setJsonString(newJson);
        try {
            const parsed = JSON.parse(newJson);
            setIsValid(true);
            setJsonError(null);
            onChange(parsed);
            onValidationChange?.(true);
        } catch (e: any) {
            setIsValid(false);
            setJsonError(e.message || "Invalid JSON");
            onValidationChange?.(false);
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(jsonString);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    // Get a summary of keys in the object
    const getSummary = () => {
        if (!value || typeof value !== 'object') return "Empty object";
        const keys = Object.keys(value);
        if (keys.length === 0) return "Empty object";
        if (keys.length <= 3) return keys.join(", ");
        return `${keys.slice(0, 3).join(", ")} + ${keys.length - 3} more`;
    };

    return (
        <div className="border border-gray-200 rounded-lg bg-white">
            {/* Section Header */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <Code className="w-5 h-5 text-purple-600" />
                    <div>
                        <h3 className="font-semibold text-gray-900">{sectionKey}</h3>
                        {description && (
                            <p className="text-xs text-gray-500 mt-0.5">{description}</p>
                        )}
                        {!isExpanded && (
                            <p className="text-xs text-gray-400 mt-1">Keys: {getSummary()}</p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {isExpanded && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleCopy();
                            }}
                            className="p-1.5 hover:bg-gray-100 rounded transition-colors"
                            title="Copy JSON"
                        >
                            {copied ? (
                                <Check className="w-4 h-4 text-green-600" />
                            ) : (
                                <Copy className="w-4 h-4 text-gray-400" />
                            )}
                        </button>
                    )}
                    {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                </div>
            </div>

            {/* Section Content */}
            {isExpanded && (
                <div className="p-4 border-t border-gray-200">
                    <textarea
                        value={jsonString}
                        onChange={(e) => handleJsonChange(e.target.value)}
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm ${
                            isValid ? 'border-gray-300' : 'border-red-300 bg-red-50'
                        }`}
                        rows={Math.max(8, Math.ceil(jsonString.split('\n').length))}
                        spellCheck={false}
                    />
                    {!isValid && jsonError && (
                        <p className="mt-2 text-xs text-red-600">
                            ✗ Invalid JSON: {jsonError}
                        </p>
                    )}
                    {isValid && (
                        <p className="mt-2 text-xs text-green-600">
                            ✓ Valid JSON
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}





