"use client";

import React from "react";

interface BrandNameProps {
    variant?: "default" | "withOS"; // "Möbius" or "Möbius OS"
    size?: "xs" | "sm" | "md" | "lg" | "xl";
    className?: string;
    gradient?: boolean; // Whether to apply gradient to text
}

export default function BrandName({ 
    variant = "default", 
    size = "md",
    className = "",
    gradient = false 
}: BrandNameProps) {
    const sizeClasses = {
        xs: "text-xs",
        sm: "text-sm",
        md: "text-base",
        lg: "text-lg",
        xl: "text-xl"
    };
    
    const brandText = variant === "withOS" ? "Möbius OS" : "Möbius";
    const gradientClass = gradient ? "mobius-gradient-text" : "";
    
    return (
        <span 
            className={`font-semibold ${sizeClasses[size]} ${gradientClass} ${className}`}
            style={{ fontFamily: "var(--font-family)" }}
        >
            {brandText}
        </span>
    );
}




