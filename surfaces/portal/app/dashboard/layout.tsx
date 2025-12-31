"use client";

import { useSession } from "next-auth/react";
import { Plus, MessageSquare, GitBranch, Database, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { data: session } = useSession();
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
    }, [pathname]); // Re-fetch when path changes

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    return (
        <div className="flex h-screen bg-[#F8F9FA] font-sans text-[#202124]">
            {/* Sidebar (Navigation Rail) - Collapsible */}
            <aside
                className={`
                    bg-[#F0F4F8] p-4 flex flex-col hidden md:flex rounded-r-2xl m-2 ml-0 transition-all duration-300 ease-in-out border-r border-gray-100/50
                    ${isSidebarOpen ? 'w-[280px] opacity-100 translate-x-0' : 'w-0 p-0 opacity-0 -translate-x-4 overflow-hidden border-none m-0'}
                `}
            >
                <div className="flex items-center gap-3 px-4 mb-8 mt-2 min-w-max">
                    <div className="w-8 h-8 rounded-full border-[3px] border-l-[#4285F4] border-t-[#EA4335] border-r-[#FBBC05] border-b-[#34A853]"></div>
                    <span className="font-semibold text-xl text-[#5F6368]">Mobius</span>
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

                <div className="mt-auto flex items-center gap-3 px-2 py-3 hover:bg-white rounded-xl cursor-pointer transition-colors min-w-max">
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
            <main className="flex-1 flex flex-col relative bg-white m-2 rounded-2xl shadow-sm border border-gray-100 overflow-hidden transition-all duration-300">
                {/* Toggle Button (Absolute Pinned) */}
                <button
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className="absolute top-4 left-4 z-50 p-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 transition-colors"
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>
                {children}
            </main>
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
