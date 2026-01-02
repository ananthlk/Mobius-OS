"use client";

import { useMemo } from "react";

interface MobiusIconProps {
    size?: number; // Size in pixels (width), height will be 60% of width
    className?: string;
    animated?: boolean; // Whether to show animated gradient
}

export default function MobiusIcon({ size, className = "", animated = false }: MobiusIconProps) {
    // Generate unique ID for gradient to avoid conflicts (stable across renders)
    const gradientId = useMemo(() => `mobius-gradient-${Math.random().toString(36).substr(2, 9)}`, []);
    
    // Calculate dimensions
    const width = size || (className ? undefined : 32);
    const height = width ? width * 0.6 : undefined;
    
    const style = width ? { width: `${width}px`, height: `${height}px` } : undefined;
    const finalClassName = className || (size ? "" : "w-8");
    
    return (
        <svg 
            viewBox="0 0 100 60" 
            className={finalClassName}
            style={style}
        >
            <defs>
                {animated ? (
                    <linearGradient id={gradientId} x1="0%" y1="0%" x2="200%" y2="0%">
                        <stop offset="0%" stopColor="#4285F4" />
                        <stop offset="12.5%" stopColor="#EA4335" />
                        <stop offset="25%" stopColor="#FBBC05" />
                        <stop offset="37.5%" stopColor="#34A853" />
                        <stop offset="50%" stopColor="#4285F4" />
                        <stop offset="62.5%" stopColor="#EA4335" />
                        <stop offset="75%" stopColor="#FBBC05" />
                        <stop offset="87.5%" stopColor="#34A853" />
                        <stop offset="100%" stopColor="#4285F4" />
                        <animate attributeName="x1" from="0%" to="-100%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="x2" from="200%" to="100%" dur="4s" repeatCount="indefinite" />
                    </linearGradient>
                ) : (
                    <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#4285F4" />
                        <stop offset="33%" stopColor="#EA4335" />
                        <stop offset="66%" stopColor="#FBBC05" />
                        <stop offset="100%" stopColor="#34A853" />
                    </linearGradient>
                )}
            </defs>
            <path 
                d="M30 30 C30 15, 45 15, 50 30 C55 45, 70 45, 70 30 C70 15, 55 15, 50 30 C45 45, 30 45, 30 30"
                stroke={`url(#${gradientId})`}
                strokeWidth="5"
                fill="none"
                strokeLinecap="round"
            />
        </svg>
    );
}

