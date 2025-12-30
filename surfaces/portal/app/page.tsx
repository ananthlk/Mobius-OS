"use client";

import Link from "next/link";
import { ArrowRight, Shield } from "lucide-react";

export default function Home() {
    return (
        <main className="min-h-screen flex flex-col bg-[#ffffff] text-[#202124] relative overflow-hidden font-sans selection:bg-blue-100">

            {/* Top Navigation - Minimal */}
            <nav className="absolute top-0 right-0 p-8 z-50">
                <Link
                    href="/auth/signin"
                    className="text-[14px] text-[#9aa0a6] hover:text-[#202124] font-medium transition-colors duration-200"
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
                        <svg viewBox="0 0 100 60" className="h-full w-full drop-shadow-sm">
                            <defs>
                                <linearGradient id="flow-hero" x1="0%" y1="0%" x2="200%" y2="0%">
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
                            </defs>
                            <path d="M30 30 C30 15, 45 15, 50 30 C55 45, 70 45, 70 30 C70 15, 55 15, 50 30 C45 45, 30 45, 30 30"
                                stroke="url(#flow-hero)" strokeWidth="5" fill="none" strokeLinecap="round" />
                        </svg>
                    </div>
                </div>

                {/* Hero Text */}
                <h1 className="text-4xl md:text-5xl tracking-tight text-[#202124] mb-12 text-center">
                    <span className="font-semibold">Organize the</span> <span className="mobius-gradient-text font-bold">Continuum.</span>
                </h1>

                {/* Command Bar Interaction */}
                <div className="w-full max-w-[600px] relative group">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Facilitating dignity and flow..."
                            className="w-full h-[56px] px-6 py-4 bg-white rounded-xl border border-[#e0e0e0] text-[#202124] placeholder-gray-400 outline-none focus:border-blue-400 focus:ring-4 focus:ring-blue-500/10 transition-all duration-300 shadow-[0_10px_30px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_40px_rgba(0,0,0,0.08)] text-lg"
                        />
                    </div>

                    {/* Status Indicator */}
                    <div className="mt-3 ml-1 flex items-center gap-1.5 text-[#666] text-[12px] font-medium opacity-80">
                        <Shield className="w-3 h-3" />
                        <span>Secure Channel</span>
                    </div>
                </div>

                {/* Primary CTA */}
                <div className="mt-10">
                    <Link
                        href="/auth/signin"
                        className="group inline-flex items-center gap-2 text-sm font-medium text-[#5f6368] hover:text-[#1a73e8] transition-colors py-2 px-4"
                    >
                        <span>Enter Continuum</span>
                        <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                </div>

            </div>

            {/* Compliance Footer */}
            <footer className="flex-none py-6 w-full text-center">
                <div className="text-[11px] text-[#999] uppercase tracking-wider font-medium flex items-center justify-center gap-4">
                    <span className="flex items-center gap-1.5">
                        <Shield className="w-3 h-3" />
                        HIPAA Compliant
                    </span>
                    <span className="w-px h-3 bg-[#e0e0e0]"></span>
                    <span>End-to-End Encrypted</span>
                    <span className="w-px h-3 bg-[#e0e0e0]"></span>
                    <span>© 2024 Mobius OS</span>
                </div>
            </footer>

        </main>
    );
}
