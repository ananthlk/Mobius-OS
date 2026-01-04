"use client";

import { useMemo } from "react";

interface MobiusIconProps {
    size?: number; // Size in pixels (width), height will be 60% of width
    className?: string;
    animated?: boolean; // Whether to show animated gradient
}

export default function MobiusIcon({ size, className = "", animated = false }: MobiusIconProps) {
    // Generate unique ID for gradients to avoid conflicts (stable across renders)
    const gradientId1 = useMemo(() => `mobius-gradient-1-${Math.random().toString(36).substr(2, 9)}`, []);
    const gradientId2 = useMemo(() => `mobius-gradient-2-${Math.random().toString(36).substr(2, 9)}`, []);
    const filterId = useMemo(() => `mobius-shadow-${Math.random().toString(36).substr(2, 9)}`, []);
    
    // Calculate dimensions
    const width = size || (className ? undefined : 32);
    const height = width ? width * 0.6 : undefined;
    
    const style = width ? { width: `${width}px`, height: `${height}px` } : undefined;
    const finalClassName = className || (size ? "" : "w-8");
    
    // Standardized stroke width
    const strokeWidth = 6;
    
    return (
        <svg 
            viewBox="0 0 100 60" 
            className={finalClassName}
            style={style}
            xmlns="http://www.w3.org/2000/svg"
        >
            <defs>
                {/* Shadow filter for depth */}
                <filter id={filterId} x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur in="SourceAlpha" stdDeviation="1.5"/>
                    <feOffset dx="1" dy="1" result="offsetblur"/>
                    <feComponentTransfer>
                        <feFuncA type="linear" slope="0.3"/>
                    </feComponentTransfer>
                    <feMerge>
                        <feMergeNode/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
                
                {/* Top loop gradient - shows twist from blue/red to yellow/green */}
                {animated ? (
                    <linearGradient id={gradientId1} x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="objectBoundingBox">
                        <stop offset="0%" stopColor="#4285F4" />
                        <stop offset="25%" stopColor="#EA4335" />
                        <stop offset="50%" stopColor="#FBBC05" />
                        <stop offset="75%" stopColor="#34A853" />
                        <stop offset="100%" stopColor="#4285F4" />
                        <animate attributeName="x1" from="0%" to="100%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="y1" from="0%" to="100%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="x2" from="100%" to="0%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="y2" from="100%" to="0%" dur="4s" repeatCount="indefinite" />
                    </linearGradient>
                ) : (
                    <linearGradient id={gradientId1} x1="0%" y1="0%" x2="100%" y2="100%" gradientUnits="objectBoundingBox">
                        <stop offset="0%" stopColor="#4285F4" />
                        <stop offset="33%" stopColor="#EA4335" />
                        <stop offset="66%" stopColor="#FBBC05" />
                        <stop offset="100%" stopColor="#34A853" />
                    </linearGradient>
                )}
                
                {/* Bottom loop gradient - creates twist effect by using different gradient angle */}
                {animated ? (
                    <linearGradient id={gradientId2} x1="100%" y1="0%" x2="0%" y2="100%" gradientUnits="objectBoundingBox">
                        <stop offset="0%" stopColor="#34A853" />
                        <stop offset="25%" stopColor="#4285F4" />
                        <stop offset="50%" stopColor="#EA4335" />
                        <stop offset="75%" stopColor="#FBBC05" />
                        <stop offset="100%" stopColor="#34A853" />
                        <animate attributeName="x1" from="100%" to="0%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="y1" from="0%" to="100%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="x2" from="0%" to="100%" dur="4s" repeatCount="indefinite" />
                        <animate attributeName="y2" from="100%" to="0%" dur="4s" repeatCount="indefinite" />
                    </linearGradient>
                ) : (
                    <linearGradient id={gradientId2} x1="100%" y1="0%" x2="0%" y2="100%" gradientUnits="objectBoundingBox">
                        <stop offset="0%" stopColor="#34A853" />
                        <stop offset="33%" stopColor="#4285F4" />
                        <stop offset="66%" stopColor="#EA4335" />
                        <stop offset="100%" stopColor="#FBBC05" />
                    </linearGradient>
                )}
            </defs>
            
            {/* Infinity symbol path - top loop */}
            <path 
                d="M30 30 C30 15, 45 15, 50 30 C55 45, 70 45, 70 30"
                stroke={`url(#${gradientId1})`}
                strokeWidth={strokeWidth}
                fill="none"
                strokeLinecap="round"
                filter={`url(#${filterId})`}
            />
            
            {/* Infinity symbol path - bottom loop (twisted) */}
            <path 
                d="M70 30 C70 15, 55 15, 50 30 C45 45, 30 45, 30 30"
                stroke={`url(#${gradientId2})`}
                strokeWidth={strokeWidth}
                fill="none"
                strokeLinecap="round"
                filter={`url(#${filterId})`}
            />
        </svg>
    );
}

