"use client";

import React, { useState, useCallback } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';

export interface RouterOption {
    id: string;
    label: string;
    value: string;
    type: 'button' | 'nested' | 'input' | 'llm_parse';
    icon?: string;
    description?: string;
    tooltip?: string;
    sub_options?: RouterOption[];
    input_type?: string;
    input_placeholder?: string;
    input_required?: boolean;
    requires_llm_parsing?: boolean;
    action?: 'continue' | 'stop' | 'show_sub_options' | 'request_input';
    action_target?: string;
    metadata?: Record<string, any>;
}

export interface DynamicRouterProps {
    options: RouterOption[];
    message?: string;
    onSelect: (optionId: string, value?: any) => void;
    selectedPath?: string[]; // Track selected path for nested options
    disabled?: boolean;
}

export default function DynamicRouter({
    options,
    message,
    onSelect,
    selectedPath = [],
    disabled = false
}: DynamicRouterProps) {
    const [expandedOptions, setExpandedOptions] = useState<Set<string>>(new Set());
    const [inputValues, setInputValues] = useState<Record<string, string>>({});

    const handleOptionClick = useCallback((option: RouterOption) => {
        if (disabled) return;

        // Toggle expansion for nested options
        if (option.type === 'nested' && option.sub_options) {
            setExpandedOptions(prev => {
                const newSet = new Set(prev);
                if (newSet.has(option.id)) {
                    newSet.delete(option.id);
                } else {
                    newSet.add(option.id);
                }
                return newSet;
            });
        }

        // Handle input options
        if (option.type === 'input') {
            // Show input field - handled by rendering
            return;
        }

        // Call onSelect with option (type is not 'input' at this point)
        const value = option.value;
        onSelect(option.id, value);
    }, [disabled, inputValues, onSelect]);

    const handleInputChange = useCallback((optionId: string, value: string) => {
        setInputValues(prev => ({ ...prev, [optionId]: value }));
    }, []);

    const handleInputSubmit = useCallback((option: RouterOption) => {
        const value = inputValues[option.id];
        if (value && (!option.input_required || option.input_required)) {
            onSelect(option.id, value);
        }
    }, [inputValues, onSelect]);

    const getIcon = (iconName?: string) => {
        const icons: Record<string, string> = {
            '📋': '📋',
            '📅': '📅',
            '💰': '💰',
            '🔄': '🔄',
            '✅': '✅',
            '❌': '❌',
            '⚠️': '⚠️'
        };
        return iconName && icons[iconName] ? icons[iconName] : null;
    };

    const renderOption = (option: RouterOption, level: number = 0) => {
        const isExpanded = expandedOptions.has(option.id);
        const hasSubOptions = option.sub_options && option.sub_options.length > 0;
        const inputValue = inputValues[option.id] || '';

        return (
            <div key={option.id} className={`${level > 0 ? 'ml-6 mt-2' : ''}`}>
                <div className="flex items-center gap-2">
                    {hasSubOptions && (
                        <button
                            onClick={() => {
                                setExpandedOptions(prev => {
                                    const newSet = new Set(prev);
                                    if (newSet.has(option.id)) {
                                        newSet.delete(option.id);
                                    } else {
                                        newSet.add(option.id);
                                    }
                                    return newSet;
                                });
                            }}
                            className="p-1 hover:bg-[var(--bg-secondary)] rounded"
                        >
                            {isExpanded ? (
                                <ChevronDown size={16} className="text-[var(--text-secondary)]" />
                            ) : (
                                <ChevronRight size={16} className="text-[var(--text-secondary)]" />
                            )}
                        </button>
                    )}
                    
                    {option.type === 'input' ? (
                        <div className="flex-1 flex gap-2">
                            <input
                                type={option.input_type || 'text'}
                                placeholder={option.input_placeholder}
                                value={inputValue}
                                onChange={(e) => handleInputChange(option.id, e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && inputValue) {
                                        handleInputSubmit(option);
                                    }
                                }}
                                className="flex-1 px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:outline-none focus:ring-2 focus:ring-[var(--primary-blue)]"
                                disabled={disabled}
                            />
                            {option.input_required && inputValue && (
                                <button
                                    onClick={() => handleInputSubmit(option)}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                                    disabled={disabled}
                                >
                                    Submit
                                </button>
                            )}
                        </div>
                    ) : (
                        <button
                            onClick={() => handleOptionClick(option)}
                            disabled={disabled}
                            className={`
                                flex-1 text-left px-4 py-3 rounded-lg border-2 transition-all
                                ${selectedPath.includes(option.id)
                                    ? 'bg-[var(--primary-blue-light)] border-[var(--primary-blue)] text-[var(--primary-blue-dark)]'
                                    : 'bg-[var(--bg-primary)] border-[var(--border-subtle)] hover:border-[var(--primary-blue)] hover:bg-[var(--primary-blue-light)]'
                                }
                                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            `}
                            title={option.tooltip || option.description}
                        >
                            <div className="flex items-center gap-2">
                                {option.icon && (
                                    <span className="text-lg">{getIcon(option.icon)}</span>
                                )}
                                <div className="flex-1">
                                    <div className="font-medium">{option.label}</div>
                                    {option.description && (
                                        <div className="text-sm text-[var(--text-secondary)] mt-1">
                                            {option.description}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </button>
                    )}
                </div>

                {/* Render sub-options if expanded */}
                {hasSubOptions && isExpanded && option.sub_options && (
                    <div className="mt-2 space-y-2">
                        {option.sub_options.map(subOption => renderOption(subOption, level + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="my-4 p-4 rounded-xl border-2 bg-[var(--bg-primary)] border-[var(--border-subtle)]">
            {message && (
                <p className="text-sm font-medium text-[var(--text-primary)] mb-4">{message}</p>
            )}
            <div className="space-y-2">
                {options.map(option => renderOption(option))}
            </div>
        </div>
    );
}

