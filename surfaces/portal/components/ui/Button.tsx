"use client";

import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "danger" | "success" | "warning";
    size?: "sm" | "md" | "lg";
    icon?: React.ReactNode;
    iconPosition?: "left" | "right";
    loading?: boolean;
    children: React.ReactNode;
}

export default function Button({
    variant = "primary",
    size = "md",
    icon,
    iconPosition = "left",
    loading = false,
    disabled,
    className = "",
    children,
    ...props
}: ButtonProps) {
    const baseStyles = "inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
    
    const variantStyles = {
        primary: "bg-[var(--primary-blue)] text-white hover:bg-[var(--primary-blue-dark)] focus:ring-[var(--primary-blue)] border border-[var(--primary-blue)]",
        secondary: "bg-white text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] border border-[var(--border-subtle)] hover:border-[var(--border-medium)] focus:ring-[var(--border-subtle)]",
        danger: "bg-[var(--brand-red)] text-white hover:bg-[var(--brand-red-dark)] focus:ring-[var(--brand-red)] border border-[var(--brand-red)]",
        success: "bg-[var(--brand-green)] text-white hover:bg-[var(--brand-green-dark)] focus:ring-[var(--brand-green)] border border-[var(--brand-green)]",
        warning: "bg-[var(--brand-yellow)] text-white hover:bg-[var(--brand-yellow-dark)] focus:ring-[var(--brand-yellow)] border border-[var(--brand-yellow)]"
    };
    
    const sizeStyles = {
        sm: "px-3 py-1.5 text-xs rounded-[var(--radius-md)]",
        md: "px-4 py-2 text-sm rounded-[var(--radius-md)]",
        lg: "px-6 py-3 text-base rounded-[var(--radius-lg)]"
    };
    
    const iconSpacing = icon ? (size === "sm" ? "gap-1.5" : size === "md" ? "gap-2" : "gap-2.5") : "";
    
    const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${iconSpacing} ${className}`;
    
    return (
        <button
            className={combinedClassName}
            disabled={disabled || loading}
            {...props}
        >
            {loading ? (
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            ) : icon && iconPosition === "left" ? (
                <span className="flex-shrink-0">{icon}</span>
            ) : null}
            
            <span>{children}</span>
            
            {!loading && icon && iconPosition === "right" && (
                <span className="flex-shrink-0">{icon}</span>
            )}
        </button>
    );
}






