"use client";

import React from "react";

interface SchemaField {
    allowed?: any[] | string;
    default?: any;
    min?: number;
    max?: number;
}

interface TaskFormFieldsProps {
    sectionKey: string;
    schema: any;
    formData: any;
    onChange: (path: string[], value: any) => void;
    tasks?: Array<{ task_key: string; name: string }>; // For dependency fields
}

export default function TaskFormFields({
    sectionKey,
    schema,
    formData,
    onChange,
    tasks = [],
}: TaskFormFieldsProps) {
    const renderField = (
        fieldKey: string,
        fieldSchema: SchemaField,
        currentValue: any,
        path: string[]
    ) => {
        const fieldPath = [...path, fieldKey];
        const fieldId = fieldPath.join(".");

        // Handle array[string] type
        if (fieldSchema.allowed === "array[string]") {
            // Special handling for task_key arrays (dependencies)
            if (fieldKey.includes("task_keys") && tasks.length > 0) {
                return (
                    <div key={fieldKey} className="space-y-2">
                        <label
                            htmlFor={fieldId}
                            className="block text-sm font-medium text-gray-700"
                        >
                            {fieldKey
                                .split("_")
                                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                                .join(" ")}
                        </label>
                        <select
                            id={fieldId}
                            multiple
                            value={Array.isArray(currentValue) ? currentValue : []}
                            onChange={(e) => {
                                const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                                onChange(fieldPath, selected);
                            }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            size={Math.min(5, tasks.length)}
                        >
                            {tasks.map((task) => (
                                <option key={task.task_key} value={task.task_key}>
                                    {task.name} ({task.task_key})
                                </option>
                            ))}
                        </select>
                        <p className="text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                    </div>
                );
            }

            // Regular comma-separated array input
            return (
                <div key={fieldKey} className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                        {fieldKey
                            .split("_")
                            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                            .join(" ")}
                    </label>
                    <textarea
                        value={Array.isArray(currentValue) ? currentValue.join(", ") : ""}
                        onChange={(e) => {
                            const values = e.target.value
                                .split(",")
                                .map((v) => v.trim())
                                .filter((v) => v);
                            onChange(fieldPath, values);
                        }}
                        rows={2}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                        placeholder="Enter values separated by commas"
                    />
                </div>
            );
        }

        // Handle boolean fields
        if (Array.isArray(fieldSchema.allowed) && fieldSchema.allowed.length === 2 &&
            fieldSchema.allowed.includes(true) && fieldSchema.allowed.includes(false)) {
            return (
                <div key={fieldKey} className="flex items-center gap-3">
                    <input
                        type="checkbox"
                        id={fieldId}
                        checked={currentValue === true}
                        onChange={(e) => onChange(fieldPath, e.target.checked)}
                        className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                    />
                    <label
                        htmlFor={fieldId}
                        className="text-sm font-medium text-gray-700 cursor-pointer"
                    >
                        {fieldKey
                            .split("_")
                            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                            .join(" ")}
                    </label>
                </div>
            );
        }

        // Handle number fields with min/max
        if (fieldSchema.min !== undefined || fieldSchema.max !== undefined) {
            return (
                <div key={fieldKey} className="space-y-1">
                    <label
                        htmlFor={fieldId}
                        className="block text-sm font-medium text-gray-700"
                    >
                        {fieldKey
                            .split("_")
                            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                            .join(" ")}
                    </label>
                    <input
                        type="number"
                        id={fieldId}
                        value={currentValue ?? fieldSchema.default ?? ""}
                        min={fieldSchema.min}
                        max={fieldSchema.max}
                        step={fieldSchema.min !== undefined && fieldSchema.min < 1 ? 0.1 : 1}
                        onChange={(e) => {
                            const val = fieldSchema.min !== undefined && fieldSchema.min < 1
                                ? parseFloat(e.target.value) || 0
                                : parseInt(e.target.value) || 0;
                            onChange(fieldPath, val);
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                </div>
            );
        }

        // Handle enum/array fields (dropdowns)
        if (Array.isArray(fieldSchema.allowed)) {
            // Check if this should be a multi-select (default is array)
            const isMultiSelect = Array.isArray(fieldSchema.default);

            return (
                <div key={fieldKey} className="space-y-1">
                    <label
                        htmlFor={fieldId}
                        className="block text-sm font-medium text-gray-700"
                    >
                        {fieldKey
                            .split("_")
                            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                            .join(" ")}
                    </label>
                    <select
                        id={fieldId}
                        value={isMultiSelect ? (Array.isArray(currentValue) ? currentValue : fieldSchema.default || []) : (currentValue ?? fieldSchema.default ?? "")}
                        onChange={(e) => {
                            if (isMultiSelect) {
                                const selected = Array.from(e.target.selectedOptions, (opt) => opt.value);
                                onChange(fieldPath, selected);
                            } else {
                                onChange(fieldPath, e.target.value);
                            }
                        }}
                        multiple={isMultiSelect}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        size={isMultiSelect ? Math.min(5, fieldSchema.allowed.length) : undefined}
                    >
                        {fieldSchema.allowed.map((option: any) => {
                            const optionValue = String(option);
                            const isSelected = isMultiSelect
                                ? Array.isArray(currentValue) && currentValue.includes(optionValue)
                                : currentValue === optionValue;
                            return (
                                <option key={option} value={option} selected={isSelected}>
                                    {optionValue
                                        .split("_")
                                        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                                        .join(" ")}
                                </option>
                            );
                        })}
                    </select>
                    {isMultiSelect && (
                        <p className="text-xs text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                    )}
                </div>
            );
        }

        // Default: text input
        return (
            <div key={fieldKey} className="space-y-1">
                <label
                    htmlFor={fieldId}
                    className="block text-sm font-medium text-gray-700"
                >
                    {fieldKey
                        .split("_")
                        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                        .join(" ")}
                </label>
                <input
                    type="text"
                    id={fieldId}
                    value={currentValue ?? fieldSchema.default ?? ""}
                    onChange={(e) => onChange(fieldPath, e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
            </div>
        );
    };

    const renderNestedField = (
        fieldKey: string,
        fieldSchema: any,
        currentValue: any,
        path: string[]
    ) => {
        // Check if this is a leaf field (has allowed, min, max, or default directly)
        const isLeafField = 
            fieldSchema.allowed !== undefined || 
            fieldSchema.min !== undefined || 
            fieldSchema.max !== undefined ||
            (typeof fieldSchema === 'object' && fieldSchema !== null && 'default' in fieldSchema && Object.keys(fieldSchema).length <= 2);

        if (isLeafField && typeof fieldSchema === 'object' && fieldSchema !== null) {
            // This is a leaf field with schema definition
            return renderField(fieldKey, fieldSchema, currentValue, path);
        }

        // This is a nested object
        if (typeof fieldSchema === 'object' && fieldSchema !== null && !Array.isArray(fieldSchema)) {
            return (
                <div key={fieldKey} className="space-y-3 pt-2 border-t border-gray-100">
                    <h4 className="text-sm font-semibold text-gray-800">
                        {fieldKey
                            .split("_")
                            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                            .join(" ")}
                    </h4>
                    <div className="pl-4 space-y-3">
                        {Object.entries(fieldSchema).map(([nestedKey, nestedSchema]: [string, any]) => {
                            const nestedPath = [...path, fieldKey];
                            const nestedValue = currentValue && typeof currentValue === 'object' ? currentValue[nestedKey] : undefined;
                            return renderNestedField(nestedKey, nestedSchema, nestedValue, nestedPath);
                        })}
                    </div>
                </div>
            );
        }

        // Fallback: treat as leaf field
        return renderField(fieldKey, { default: fieldSchema }, currentValue, path);
    };

    const sectionSchema = schema[sectionKey];
    if (!sectionSchema) {
        return null;
    }

    const sectionData = formData[sectionKey] || {};

    return (
        <div className="space-y-4">
            {Object.entries(sectionSchema).map(([fieldKey, fieldSchema]: [string, any]) => {
                // Skip schema metadata fields
                if (fieldKey === "intent_examples" || fieldKey === "question_intent_examples") {
                    return null;
                }

                return renderNestedField(fieldKey, fieldSchema, sectionData[fieldKey], [sectionKey]);
            })}
        </div>
    );
}

