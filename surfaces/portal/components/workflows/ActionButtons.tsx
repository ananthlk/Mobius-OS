"use client";

import React, { useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle, Edit, XCircle, PlusCircle, AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react';

interface ButtonAction {
    type: 'api_call' | 'event' | 'navigation';
    endpoint?: string;
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    payload?: any;
    eventName?: string;
    route?: string;
}

interface ActionButton {
    id: string;
    label: string;
    variant: 'primary' | 'secondary' | 'danger' | 'success' | 'warning';
    action: ButtonAction;
    enabled: boolean;
    tooltip?: string;
    icon?: string; // Optional icon name
}

interface ActionButtonsProps {
    buttons: ActionButton[];
    context?: string;
    message?: string;
    sessionId?: number | null;
    onActionComplete?: (buttonId: string, result: any) => void;
}

export default function ActionButtons({ 
    buttons, 
    context, 
    message, 
    sessionId,
    onActionComplete 
}: ActionButtonsProps) {
    const router = useRouter();
    const [loadingButtonId, setLoadingButtonId] = React.useState<string | null>(null);
    const clickedButtonsRef = useRef<Set<string>>(new Set()); // Track clicked buttons to prevent duplicates

    const handleButtonClick = useCallback(async (button: ActionButton) => {
        // Prevent duplicate clicks
        if (!button.enabled || loadingButtonId) {
            return;
        }
        
        // Check if already clicked (prevent rapid double-clicks)
        if (clickedButtonsRef.current.has(button.id)) {
            return;
        }

        clickedButtonsRef.current.add(button.id);
        setLoadingButtonId(button.id);
        
        try {
            const { action } = button;
            
            if (action.type === 'api_call' && action.endpoint) {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const endpoint = action.endpoint.replace('{session_id}', String(sessionId || ''));
                
                console.log('[ActionButtons] Making API call:', {
                    endpoint: `${apiUrl}${endpoint}`,
                    method: action.method || 'POST',
                    payload: action.payload
                });
                
                try {
                    const response = await fetch(`${apiUrl}${endpoint}`, {
                        method: action.method || 'POST',
                        headers: { "Content-Type": "application/json" },
                        body: action.payload ? JSON.stringify(action.payload) : undefined,
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error('[ActionButtons] API call failed:', {
                            status: response.status,
                            statusText: response.statusText,
                            error: errorText
                        });
                        throw new Error(`API call failed: ${response.status} ${response.statusText}`);
                    }
                    
                    const result = await response.json();
                    console.log('[ActionButtons] API call succeeded:', result);
                    
                    if (onActionComplete) {
                        onActionComplete(button.id, result);
                    }
                } catch (fetchError: any) {
                    console.error('[ActionButtons] API call error:', fetchError);
                    if (onActionComplete) {
                        onActionComplete(button.id, { error: fetchError.message });
                    }
                    throw fetchError;
                }
            } else if (action.type === 'event' && action.eventName) {
                // Emit custom event
                window.dispatchEvent(new CustomEvent(action.eventName, { 
                    detail: { buttonId: button.id, payload: action.payload } 
                }));
                if (onActionComplete) {
                    onActionComplete(button.id, { success: true });
                }
            } else if (action.type === 'navigation' && action.route) {
                // Use Next.js router for client-side navigation
                router.push(action.route);
                if (onActionComplete) {
                    onActionComplete(button.id, { success: true, route: action.route });
                }
            }
        } catch (error: any) {
            console.error(`Action button ${button.id} failed:`, error);
            if (onActionComplete) {
                onActionComplete(button.id, { error: error.message });
            }
        } finally {
            setLoadingButtonId(null);
            // Don't remove from clickedButtonsRef - keep it clicked to prevent re-clicks
        }
    }, [router, loadingButtonId, sessionId, onActionComplete]);

    const getVariantStyles = (variant: string) => {
        const styles = {
            primary: "bg-blue-600 text-white hover:bg-blue-700 border border-blue-600 hover:border-blue-700",
            secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 hover:border-gray-400",
            danger: "bg-red-600 text-white hover:bg-red-700 border border-red-600 hover:border-red-700",
            success: "bg-green-600 text-white hover:bg-green-700 border border-green-600 hover:border-green-700",
            warning: "bg-yellow-500 text-white hover:bg-yellow-600 border border-yellow-500 hover:border-yellow-600"
        };
        return styles[variant as keyof typeof styles] || styles.secondary;
    };

    const getVariantInlineStyles = (variant: string, isDisabled: boolean): React.CSSProperties => {
        const styles: React.CSSProperties = {
            position: 'relative',
            zIndex: 10,
            pointerEvents: isDisabled ? 'none' : 'auto',
        };

        if (variant === 'primary') {
            styles.backgroundColor = isDisabled ? '#9ca3af' : '#2563eb';
            styles.color = '#ffffff';
            styles.borderColor = '#2563eb';
        } else if (variant === 'secondary') {
            styles.backgroundColor = isDisabled ? '#e5e7eb' : '#f3f4f6';
            styles.color = '#1f2937';
            styles.borderColor = '#d1d5db';
        } else if (variant === 'danger') {
            styles.backgroundColor = isDisabled ? '#9ca3af' : '#dc2626';
            styles.color = '#ffffff';
            styles.borderColor = '#dc2626';
        } else if (variant === 'success') {
            styles.backgroundColor = isDisabled ? '#9ca3af' : '#16a34a';
            styles.color = '#ffffff';
            styles.borderColor = '#16a34a';
        } else if (variant === 'warning') {
            styles.backgroundColor = isDisabled ? '#9ca3af' : '#eab308';
            styles.color = '#ffffff';
            styles.borderColor = '#eab308';
        }

        return styles;
    };

    const getIcon = (iconName?: string, isLoading?: boolean) => {
        if (isLoading) {
            return <RefreshCw size={12} className="animate-spin" />;
        }
        
        const icons: Record<string, React.ReactNode> = {
            check: <CheckCircle size={12} />,
            edit: <Edit size={12} />,
            cancel: <XCircle size={12} />,
            add: <PlusCircle size={12} />,
            warning: <AlertTriangle size={12} />,
            arrow: <ArrowRight size={12} />
        };
        return iconName ? icons[iconName] : null;
    };

    if (buttons.length === 0) return null;

    return (
        <div className={`my-3 p-3 rounded-lg border border-gray-200 relative z-10 w-full ${
            context === 'planning_phase_decision' 
                ? 'bg-blue-50/50 border-blue-200' 
                : context === 'planning_phase_options'
                ? 'bg-white border-gray-200'
                : 'bg-gray-50/50 border-gray-200'
        }`} style={{ zIndex: 10 }}>
            {message && (
                <p className="text-xs font-medium text-gray-600 mb-2.5">{message}</p>
            )}
            <div className="flex flex-wrap items-center gap-2 w-full">
                {buttons.map((button) => {
                    const isLoading = loadingButtonId === button.id;
                    const isDisabled = !button.enabled || isLoading;
                    
                    return (
                        <button
                            key={button.id}
                            type="button"
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                handleButtonClick(button);
                            }}
                            disabled={isDisabled}
                            className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md font-medium text-xs transition-all duration-200 border min-h-[28px] ${getVariantStyles(button.variant)} ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer shadow-sm hover:shadow active:scale-[0.97]'}`}
                            style={getVariantInlineStyles(button.variant, isDisabled)}
                            title={button.tooltip || button.label}
                        >
                            {getIcon(button.icon, isLoading)}
                            <span className="whitespace-normal text-center break-words">{button.label}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

