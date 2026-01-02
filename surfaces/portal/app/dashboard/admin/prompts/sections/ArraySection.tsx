"use client";

import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, List, Plus, X } from "lucide-react";

interface ArraySectionProps {
    sectionKey: string;
    value: string[];
    description?: string;
    onChange: (value: string[]) => void;
    onValidationChange?: (isValid: boolean) => void;
}

export default function ArraySection({
    sectionKey,
    value,
    description,
    onChange,
    onValidationChange
}: ArraySectionProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    // Ensure value is always an array
    const normalizedValue = Array.isArray(value) ? value : [];
    const [items, setItems] = useState<string[]>(normalizedValue);
    
    // Sync when value prop changes
    React.useEffect(() => {
        const normalized = Array.isArray(value) ? value : [];
        setItems(normalized);
    }, [value]);

    const handleItemChange = (index: number, newValue: string) => {
        const updated = [...items];
        updated[index] = newValue;
        setItems(updated);
        onChange(updated);
        onValidationChange?.(true);
    };

    const handleAddItem = () => {
        const updated = [...items, ""];
        setItems(updated);
        onChange(updated);
    };

    const handleRemoveItem = (index: number) => {
        const updated = items.filter((_, i) => i !== index);
        setItems(updated);
        onChange(updated);
    };

    return (
        <div className="border border-gray-200 rounded-lg bg-white">
            {/* Section Header */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <div className="flex items-center gap-3">
                    <List className="w-5 h-5 text-orange-600" />
                    <div>
                        <h3 className="font-semibold text-gray-900">{sectionKey}</h3>
                        {description && (
                            <p className="text-xs text-gray-500 mt-0.5">{description}</p>
                        )}
                        {!isExpanded && (
                            <p className="text-xs text-gray-400 mt-1">
                                {items.length} {items.length === 1 ? 'item' : 'items'}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">
                        {items.length} {items.length === 1 ? 'item' : 'items'}
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
                <div className="p-4 border-t border-gray-200 space-y-2">
                    {items.map((item, index) => (
                        <div key={index} className="flex items-center gap-2">
                            <input
                                type="text"
                                value={item}
                                onChange={(e) => handleItemChange(index, e.target.value)}
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                                placeholder={`Constraint ${index + 1}...`}
                            />
                            <button
                                onClick={() => handleRemoveItem(index)}
                                className="p-2 text-red-400 hover:bg-red-50 rounded-lg transition-colors"
                                title="Remove item"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    ))}
                    <button
                        onClick={handleAddItem}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-dashed border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm text-gray-600"
                    >
                        <Plus className="w-4 h-4" />
                        Add Item
                    </button>
                    {items.length === 0 && (
                        <p className="text-xs text-gray-400 text-center">No items yet</p>
                    )}
                </div>
            )}
        </div>
    );
}

