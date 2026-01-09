"use client";

import React from "react";

interface MobiusIconProps {
    size?: number;
    className?: string;
    animated?: boolean;
}

export default function MobiusIcon({ 
    size = 32, 
    className = "", 
    animated = false 
}: MobiusIconProps) {
    // Möbius strip SVG - simplified representation
    const viewBox = "0 0 100 60";
    
    return (
        <svg
            width={size}
            height={size * 0.6}
            viewBox={viewBox}
            className={className}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <defs>
                <linearGradient id="mobiusGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity="1" />
                    <stop offset="50%" stopColor="#8B5CF6" stopOpacity="1" />
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity="1" />
                </linearGradient>
            </defs>
            <path
                d="M 10 30 Q 25 10, 50 30 T 90 30"
                stroke="url(#mobiusGradient)"
                strokeWidth="3"
                fill="none"
                className={animated ? "animate-pulse" : ""}
            />
            <path
                d="M 10 30 Q 25 50, 50 30 T 90 30"
                stroke="url(#mobiusGradient)"
                strokeWidth="3"
                fill="none"
                className={animated ? "animate-pulse" : ""}
                style={animated ? { animationDelay: "0.5s" } : {}}
            />
            <circle cx="50" cy="30" r="8" fill="url(#mobiusGradient)" opacity="0.6" />
        </svg>
    );
}
