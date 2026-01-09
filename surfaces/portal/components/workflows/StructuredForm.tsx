"use client";

import React, { useState } from 'react';
import { CheckCircle, X } from 'lucide-react';

interface FormField {
    id: string;
    label: string;
    type: 'text' | 'textarea' | 'select' | 'separator';
    required?: boolean;
    placeholder?: string;
    pattern?: string;
    value?: string;
    options?: { value: string; label: string }[];
}

interface SubmitButton {
    id: string;
    label: string;
    variant: 'primary' | 'secondary' | 'danger' | 'success' | 'warning';
    action: {
        type: 'api_call' | 'event' | 'navigation';
        endpoint?: string;
        method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
        payload?: any;
    };
    enabled: boolean;
    icon?: string;
}

interface StructuredFormProps {
    formType: string;
    message?: string;
    formFields: FormField[];
    submitButton: SubmitButton;
    sessionId?: number | null;
    onSubmit?: (formData: Record<string, string>) => Promise<any>;
    onSuccess?: (result: any) => void;
    onError?: (error: any) => void;
}

export default function StructuredForm({
    formType,
    message,
    formFields,
    submitButton,
    sessionId,
    onSubmit,
    onSuccess,
    onError
}: StructuredFormProps) {
    const [formData, setFormData] = useState<Record<string, string>>(() => {
        const initial: Record<string, string> = {};
        formFields.forEach(field => {
            if (field.type !== 'separator' && field.value) {
                initial[field.id] = field.value;
            }
        });
        return initial;
    });
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const validateField = (field: FormField, value: string): string | null => {
        if (field.required && !value.trim()) {
            return `${field.label} is required`;
        }
        if (field.pattern && value) {
            const regex = new RegExp(field.pattern);
            if (!regex.test(value)) {
                return `Invalid format for ${field.label}`;
            }
        }
        return null;
    };

    const handleFieldChange = (fieldId: string, value: string) => {
        setFormData(prev => ({ ...prev, [fieldId]: value }));
        // Clear error for this field when user starts typing
        if (errors[fieldId]) {
            setErrors(prev => {
                const newErrors = { ...prev };
                delete newErrors[fieldId];
                return newErrors;
            });
        }
    };

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};
        formFields.forEach(field => {
            if (field.type !== 'separator') {
                const value = formData[field.id] || '';
                const error = validateField(field, value);
                if (error) {
                    newErrors[field.id] = error;
                }
            }
        });
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        setIsSubmitting(true);
        try {
            let result;
            
            if (onSubmit) {
                // Use custom submit handler if provided
                result = await onSubmit(formData);
            } else if (submitButton.action.type === 'api_call' && submitButton.action.endpoint) {
                // Default API call handler
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const endpoint = submitButton.action.endpoint.replace('{session_id}', String(sessionId || ''));
                
                const payload = {
                    ...submitButton.action.payload,
                    form_type: formType,
                    form_data: formData
                };

                const response = await fetch(`${apiUrl}${endpoint}`, {
                    method: submitButton.action.method || 'POST',
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`API call failed: ${response.status} ${response.statusText} - ${errorText}`);
                }

                result = await response.json();
            } else {
                throw new Error('No submit handler available');
            }

            if (onSuccess) {
                onSuccess(result);
            }
        } catch (error: any) {
            console.error('[StructuredForm] Submit error:', error);
            if (onError) {
                onError(error);
            } else {
                // Show error to user
                alert(`Failed to submit form: ${error.message}`);
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    const getVariantStyles = (variant: string) => {
        const styles = {
            primary: "bg-blue-600 text-white hover:bg-blue-700 border border-blue-600 hover:border-blue-700",
            secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 hover:border-gray-400",
            danger: "bg-red-600 text-white hover:bg-red-700 border border-red-600 hover:border-red-700",
            success: "bg-green-600 text-white hover:bg-green-700 border border-green-600 hover:border-green-700",
            warning: "bg-yellow-500 text-white hover:bg-yellow-600 border border-yellow-500 hover:border-yellow-600"
        };
        return styles[variant as keyof typeof styles] || styles.primary;
    };

    return (
        <div className="my-4 p-4 rounded-lg border border-blue-200 bg-blue-50/30 w-full max-w-2xl">
            {message && (
                <p className="text-sm font-medium text-gray-700 mb-4">{message}</p>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-4">
                {formFields.map((field) => {
                    if (field.type === 'separator') {
                        return (
                            <div key={field.id} className="flex items-center my-4">
                                <div className="flex-1 border-t border-gray-300"></div>
                                <span className="px-3 text-sm text-gray-500 font-medium">{field.label}</span>
                                <div className="flex-1 border-t border-gray-300"></div>
                            </div>
                        );
                    }

                    return (
                        <div key={field.id} className="space-y-1">
                            <label htmlFor={field.id} className="block text-sm font-medium text-gray-700">
                                {field.label}
                                {field.required && <span className="text-red-500 ml-1">*</span>}
                            </label>
                            
                            {field.type === 'text' && (
                                <input
                                    type="text"
                                    id={field.id}
                                    value={formData[field.id] || ''}
                                    onChange={(e) => handleFieldChange(field.id, e.target.value)}
                                    placeholder={field.placeholder}
                                    pattern={field.pattern}
                                    required={field.required}
                                    className={`w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                                        errors[field.id] ? 'border-red-500' : 'border-gray-300'
                                    }`}
                                    disabled={isSubmitting}
                                />
                            )}
                            
                            {field.type === 'textarea' && (
                                <textarea
                                    id={field.id}
                                    value={formData[field.id] || ''}
                                    onChange={(e) => handleFieldChange(field.id, e.target.value)}
                                    placeholder={field.placeholder}
                                    required={field.required}
                                    rows={3}
                                    className={`w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y ${
                                        errors[field.id] ? 'border-red-500' : 'border-gray-300'
                                    }`}
                                    disabled={isSubmitting}
                                />
                            )}
                            
                            {field.type === 'select' && field.options && (
                                <select
                                    id={field.id}
                                    value={formData[field.id] || ''}
                                    onChange={(e) => handleFieldChange(field.id, e.target.value)}
                                    required={field.required}
                                    className={`w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                                        errors[field.id] ? 'border-red-500' : 'border-gray-300'
                                    }`}
                                    disabled={isSubmitting}
                                >
                                    <option value="">Select {field.label}</option>
                                    {field.options.map(option => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            )}
                            
                            {errors[field.id] && (
                                <p className="text-xs text-red-600">{errors[field.id]}</p>
                            )}
                        </div>
                    );
                })}
                
                <div className="flex justify-end pt-2">
                    <button
                        type="submit"
                        disabled={!submitButton.enabled || isSubmitting}
                        className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all duration-200 border ${getVariantStyles(submitButton.variant)} ${
                            !submitButton.enabled || isSubmitting 
                                ? 'opacity-50 cursor-not-allowed' 
                                : 'cursor-pointer shadow-sm hover:shadow active:scale-[0.97]'
                        }`}
                    >
                        {submitButton.icon === 'check' && <CheckCircle size={16} />}
                        <span>{isSubmitting ? 'Submitting...' : submitButton.label}</span>
                    </button>
                </div>
            </form>
        </div>
    );
}



