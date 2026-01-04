"use client";

import Link from "next/link";
import { ArrowRight, Shield } from "lucide-react";
import MobiusIcon from "@/components/MobiusIcon";

export default function Home() {
    return (
        <main className="min-h-screen flex flex-col bg-[var(--bg-primary)] text-[var(--text-primary)] relative overflow-hidden font-sans selection:bg-blue-100">

            {/* Top Navigation - Minimal */}
            <nav className="absolute top-0 right-0 p-8 z-50">
                <Link
                    href="/auth/signin"
                    className="text-[14px] text-[var(--text-muted)] hover:text-[var(--text-primary)] font-medium transition-colors duration-200"
                >
                    Sign In
                </Link>
            </nav>

            {/* Main Content */}
            <div className="flex-1 flex flex-col items-center w-full max-w-4xl mx-auto px-6">

                {/* Logo Section */}
                <div className="mt-[10vh] mb-8 animate-in fade-in zoom-in-95 duration-1000">
                    <div className="h-[80px] w-auto aspect-[100/60] mx-auto relative group">
                        <div className="absolute inset-0 bg-blue-500 opacity-0 group-hover:opacity-10 blur-xl rounded-full transition-opacity duration-700"></div>
                        <div className="h-full w-full drop-shadow-sm">
                            <MobiusIcon className="h-full w-full" animated={true} />
                        </div>
                    </div>
                </div>

                {/* Hero Text */}
                <h1 className="text-4xl md:text-5xl tracking-tight text-[var(--text-primary)] mb-12 text-center">
                    <span className="font-semibold">Organize the</span> <span className="mobius-gradient-text font-bold">Continuum.</span>
                </h1>

                {/* Command Bar Interaction */}
                <div className="w-full max-w-[600px] relative group">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Facilitating dignity and flow..."
                            className="w-full h-[56px] px-6 py-4 bg-[var(--bg-primary)] rounded-xl border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--primary-blue)] focus:ring-4 focus:ring-[var(--primary-blue)]/10 transition-all duration-300 shadow-[var(--shadow-soft)] hover:shadow-[var(--shadow-float)] text-lg"
                        />
                    </div>

                    {/* Status Indicator */}
                    <div className="mt-3 ml-1 flex items-center gap-1.5 text-[var(--text-secondary)] text-[12px] font-medium opacity-80">
                        <Shield className="w-3 h-3" />
                        <span>Secure Channel</span>
                    </div>
                </div>

                {/* Primary CTA */}
                <div className="mt-10">
                    <Link
                        href="/dashboard"
                        className="group inline-flex items-center gap-2 text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--primary-blue)] transition-colors py-2 px-4"
                    >
                        <span>Enter Continuum</span>
                        <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                </div>

            </div>

            {/* Compliance Footer */}
            <footer className="flex-none py-6 w-full text-center">
                <div className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-medium flex items-center justify-center gap-4">
                    <span className="flex items-center gap-1.5">
                        <Shield className="w-3 h-3" />
                        HIPAA Compliant
                    </span>
                    <span className="w-px h-3 bg-[var(--border-subtle)]"></span>
                    <span>End-to-End Encrypted</span>
                    <span className="w-px h-3 bg-[var(--border-subtle)]"></span>
                    <span>© 2024 Möbius OS</span>
                </div>
            </footer>

        </main>
    );
}
