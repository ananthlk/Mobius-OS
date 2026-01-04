"use client";

import { useSession } from "next-auth/react";
import { Plus, MessageSquare, GitBranch, Database, Settings, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import MobiusIcon from "@/components/MobiusIcon";
import BrandName from "@/components/BrandName";
import { useEnsureUser } from "@/hooks/useEnsureUser";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { data: session } = useSession();
    // Ensure user exists in backend database
    useEnsureUser();
    const pathname = usePathname();

    const isActive = (path: string) => pathname?.startsWith(path);

    const [recentActivity, setRecentActivity] = useState<any[]>([]);

    useEffect(() => {
        const fetchActivity = async () => {
            const moduleType = isActive('/dashboard/workflows') ? 'WORKFLOW' : 'CHAT';
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/api/activity?module=${moduleType}`);
                const data = await res.json();
                setRecentActivity(data);
            } catch (e) {
                console.error("Failed to fetch activity", e);
            }
        };

        fetchActivity();

        // Listen for refresh events (e.g., from ProblemEntry)
        const handleRefresh = () => fetchActivity();
        window.addEventListener('refresh-sidebar', handleRefresh);

        return () => window.removeEventListener('refresh-sidebar', handleRefresh);
    }, [pathname]); // Re-fetch when path changes

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    return (
        <div className="flex h-screen bg-[var(--bg-primary)] font-sans text-[var(--text-primary)]">
            {/* Sidebar (Navigation Rail) - Collapsible */}
            <aside
                className={`
                    pattern-board-light p-4 flex flex-col hidden md:flex rounded-r-2xl m-2 ml-0 transition-all duration-300 ease-in-out border-r border-[var(--border-subtle)]
                    ${isSidebarOpen ? 'w-[280px] opacity-100 translate-x-0' : 'w-0 p-0 opacity-0 -translate-x-4 overflow-hidden border-none m-0'}
                `}
            >
                <div className="flex items-center gap-3 px-4 mb-8 mt-2 min-w-max">
                    <MobiusIcon size={32} />
                    <BrandName size="lg" />
                </div>

                {/* Modules Section */}
                <div className="px-4 py-2 text-xs font-semibold text-[#5F6368] uppercase tracking-wider mb-2 min-w-max">Modules</div>
                <nav className="space-y-1 mb-8 min-w-max">
                    <Link href="/dashboard/chat">
                        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-colors ${isActive('/dashboard/chat') ? 'bg-white text-[#1a73e8] shadow-sm' : 'text-[#444746] hover:bg-white/60'}`}>
                            <MessageSquare className={`w-5 h-5 ${isActive('/dashboard/chat') ? 'text-[#1a73e8]' : 'text-[#5F6368]'}`} />
                            <span className="text-sm font-medium">Chat</span>
                        </div>
                    </Link>
                    <Link href="/dashboard/workflows">
                        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-colors ${isActive('/dashboard/workflows') ? 'bg-white text-purple-600 shadow-sm' : 'text-[#444746] hover:bg-white/60'}`}>
                            <GitBranch className={`w-5 h-5 ${isActive('/dashboard/workflows') ? 'text-purple-600' : 'text-[#5F6368]'}`} />
                            <span className="text-sm font-medium">Workflows</span>
                        </div>
                    </Link>
                    <Link href="/dashboard/knowledge">
                        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-colors ${isActive('/dashboard/knowledge') ? 'bg-white text-orange-600 shadow-sm' : 'text-[#444746]/60 hover:bg-white/60'}`}>
                            <Database className={`w-5 h-5 ${isActive('/dashboard/knowledge') ? 'text-orange-600' : 'text-[#5F6368]/60'}`} />
                            <span className="text-sm font-medium">Knowledge</span>
                        </div>
                    </Link>
                    <Link href="/dashboard/admin">
                        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-colors ${isActive('/dashboard/admin') ? 'bg-white text-slate-800 shadow-sm' : 'text-[#444746]/60 hover:bg-white/60'}`}>
                            <Settings className={`w-5 h-5 ${isActive('/dashboard/admin') ? 'text-slate-800' : 'text-[#5F6368]/60'}`} />
                            <span className="text-sm font-medium">Admin</span>
                        </div>
                    </Link>
                </nav>

                <div className="px-4 py-2 text-xs font-semibold text-[#5F6368] uppercase tracking-wider mb-2 min-w-max">
                    {isActive('/dashboard/workflows') ? 'Recent Workflows' : 'Recent Chats'}
                </div>
                <nav className="flex-1 space-y-1 overflow-y-auto min-w-max">
                    {recentActivity.map((item: any) => (
                        <SidebarItem key={item.id} label={item.title} />
                    ))}
                </nav>

                <div className="mt-auto mb-2 px-4">
                    <ModelBadge pathname={pathname} />
                </div>

                <div className="flex items-center gap-3 px-2 py-3 hover:bg-white rounded-xl cursor-pointer transition-colors min-w-max">
                    {session?.user?.image ? (
                        <img src={session.user.image} className="w-8 h-8 rounded-full" />
                    ) : (
                        <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold">
                            {session?.user?.name?.[0] || "U"}
                        </div>
                    )}
                    <div className="text-sm font-medium overflow-hidden text-ellipsis whitespace-nowrap max-w-[140px]">
                        {session?.user?.email}
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col relative bg-[var(--bg-primary)] m-2 rounded-2xl shadow-sm border border-[var(--border-subtle)] overflow-hidden transition-all duration-300">
                {/* Toggle Button - Positioned on the left edge, always visible */}
                <button
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className="absolute top-6 left-0 z-50 p-2 rounded-r-lg bg-gray-100 hover:bg-gray-200 text-gray-600 hover:text-gray-800 border border-gray-300 border-l-0 shadow-md transition-all duration-200"
                    title={isSidebarOpen ? "Hide Sidebar" : "Show Sidebar"}
                >
                    {isSidebarOpen ? (
                        <ChevronLeft className="w-5 h-5" />
                    ) : (
                        <ChevronRight className="w-5 h-5" />
                    )}
                </button>

                {children}
            </main>
        </div>
    );
}

function ModelBadge({ pathname }: { pathname: string }) {
    const [modelInfo, setModelInfo] = useState<{ model_id: string; source: string } | null>(null);

    useEffect(() => {
        const fetchModel = async () => {
            let module = 'global';
            if (pathname.startsWith('/dashboard/chat')) module = 'chat';
            else if (pathname.startsWith('/dashboard/workflows')) module = 'workflow';
            // else global/default

            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${API_URL}/api/admin/ai/resolve?module=${module}`);
                if (res.ok) {
                    const data = await res.json();
                    setModelInfo(data);
                }
            } catch (e) {
                console.error("Failed to resolve model", e);
            }
        };
        fetchModel();
    }, [pathname]);

    if (!modelInfo) return null;

    let color = "bg-slate-100 text-slate-600 border-slate-200";
    if (modelInfo.source.includes("user")) color = "bg-purple-50 text-purple-600 border-purple-200";
    if (modelInfo.source.includes("module")) color = "bg-blue-50 text-blue-600 border-blue-200";

    return (
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-white border border-slate-100 shadow-sm" title={`Source: ${modelInfo.source}`}>
            <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                <div className={`w-1.5 h-1.5 rounded-full ${modelInfo.source.includes("fail") ? "bg-red-500" : "bg-green-500"}`}></div>
                Active Model
            </div>
            <div className="text-xs font-semibold text-slate-700 truncate">{modelInfo.model_id}</div>
        </div>
    );
}

function SidebarItem({ label, active = false }: { label: string, active?: boolean }) {
    return (
        <div className={`px-4 py-3 rounded-full cursor-pointer text-sm font-medium transition-colors ${active ? 'bg-[#E8F0FE] text-[#1967D2]' : 'text-[#444746] hover:bg-gray-100'}`}>
            {label}
        </div>
    )
}
