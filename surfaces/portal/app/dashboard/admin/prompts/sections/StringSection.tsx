"use client";

import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";

interface StringSectionProps {
    sectionKey: string;
    value: string;
    description?: string;
    onChange: (value: string) => void;
    onValidationChange?: (isValid: boolean) => void;
}

export default function StringSection({
    sectionKey,
    value,
    description,
    onChange,
    onValidationChange
}: StringSectionProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    // Ensure value is always a string
    const normalizedValue = typeof value === 'string' ? value : String(value || '');
    const [localValue, setLocalValue] = useState(normalizedValue);
    
    // Sync when value prop changes
    React.useEffect(() => {
        const normalized = typeof value === 'string' ? value : String(value || '');
        setLocalValue(normalized);
    }, [value]);

    const handleChange = (newValue: string) => {
        setLocalValue(newValue);
        onChange(newValue);
        onValidationChange?.(true); // String values are always valid
    };

    const wordCount = localValue.trim().split(/\s+/).filter(Boolean).length;
    const charCount = localValue.length;

    return (
        <div className="border border-gray-200 rounded-lg bg-white">
            {/* Section Header */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-indigo-600" />
                    <div>
                        <h3 className="font-semibold text-gray-900">{sectionKey}</h3>
                        {description && (
                            <p className="text-xs text-gray-500 mt-0.5">{description}</p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">
                        {wordCount} words • {charCount} chars
                    </span>
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
                        value={localValue}
                        onChange={(e) => handleChange(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                        rows={Math.max(4, Math.ceil(localValue.split('\n').length))}
                        placeholder={`Enter ${sectionKey.toLowerCase()}...`}
                    />
                </div>
            )}
        </div>
    );
}

