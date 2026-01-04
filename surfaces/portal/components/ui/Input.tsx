"use client";

import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    size?: "sm" | "md" | "lg";
    error?: boolean;
    icon?: React.ReactNode;
    iconPosition?: "left" | "right";
}

export default function Input({
    size = "md",
    error = false,
    icon,
    iconPosition = "left",
    className = "",
    ...props
}: InputProps) {
    const baseStyles = "w-full bg-white border outline-none transition-all duration-200 focus:ring-2 focus:ring-offset-0";
    
    const sizeStyles = {
        sm: "px-3 py-1.5 text-sm rounded-[var(--radius-sm)]",
        md: "px-4 py-2 text-sm rounded-[var(--radius-md)]",
        lg: "px-5 py-3 text-base rounded-[var(--radius-lg)]"
    };
    
    const borderStyles = error 
        ? "border-[var(--brand-red)] focus:border-[var(--brand-red)] focus:ring-[var(--brand-red)]"
        : "border-[var(--border-subtle)] focus:border-[var(--primary-blue)] focus:ring-[var(--primary-blue)]";
    
    const iconPadding = icon 
        ? (iconPosition === "left" 
            ? (size === "sm" ? "pl-9" : size === "md" ? "pl-10" : "pl-12")
            : (size === "sm" ? "pr-9" : size === "md" ? "pr-10" : "pr-12"))
        : "";
    
    const combinedClassName = `${baseStyles} ${sizeStyles[size]} ${borderStyles} ${iconPadding} ${className}`;
    
    return (
        <div className="relative w-full">
            {icon && iconPosition === "left" && (
                <div className={`absolute left-0 top-0 bottom-0 flex items-center ${size === "sm" ? "pl-3" : size === "md" ? "pl-4" : "pl-5"} text-[var(--text-muted)] pointer-events-none`}>
                    {icon}
                </div>
            )}
            <input
                className={combinedClassName}
                {...props}
            />
            {icon && iconPosition === "right" && (
                <div className={`absolute right-0 top-0 bottom-0 flex items-center ${size === "sm" ? "pr-3" : size === "md" ? "pr-4" : "pr-5"} text-[var(--text-muted)] pointer-events-none`}>
                    {icon}
                </div>
            )}
        </div>
    );
}

