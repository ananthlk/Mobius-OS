"use client";

import Link from "next/link";
import { Server, FileText, Users, CheckSquare, Settings } from "lucide-react";
import AdminChat from "@/components/admin/AdminChat";

export default function AdminPage() {
    return (
        <div className="h-full flex flex-col md:flex-row">
            {/* Left Side: Chat Interface (60-70% on desktop) */}
            <div className="flex-1 md:w-[65%] h-full border-r border-gray-100">
                <AdminChat 
                    placeholder="Ask about system configuration, admin tasks, or get help..."
                    emptyStateTitle="Admin Assistant"
                    emptyStateDescription="I can help you manage system configuration, troubleshoot issues, or answer questions about the admin panel."
                />
            </div>

            {/* Right Side: Admin Section Links (30-40% on desktop) */}
            <div className="md:w-[35%] h-full overflow-y-auto bg-[#F8F9FA] p-6">
                <div className="mb-6">
                    <div className="flex items-center gap-3 mb-2">
                        <Settings className="w-6 h-6 text-slate-600" />
                        <h1 className="text-xl font-semibold text-gray-900">Admin Sections</h1>
                    </div>
                    <p className="text-sm text-gray-500">
                        Quick access to system administration tools
                    </p>
                </div>

                <div className="space-y-4">
                    {/* Client Management */}
                    <Link href="/dashboard/admin/clients">
                        <div className="p-5 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <Users className="w-6 h-6 text-indigo-600" />
                                <h3 className="text-lg font-semibold text-gray-900">Client Management</h3>
                            </div>
                            <p className="text-sm text-gray-500 mb-2">
                                Manage users and organizations
                            </p>
                            <span className="inline-block text-xs px-2 py-1 bg-amber-50 text-amber-700 rounded-md">
                                Coming Soon
                            </span>
                        </div>
                    </Link>

                    {/* LLM Management */}
                    <Link href="/dashboard/admin/llms">
                        <div className="p-5 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <Server className="w-6 h-6 text-indigo-600" />
                                <h3 className="text-lg font-semibold text-gray-900">LLM Management</h3>
                            </div>
                            <p className="text-sm text-gray-500">
                                Configure AI providers, models, and governance rules
                            </p>
                        </div>
                    </Link>

                    {/* Task Catalog */}
                    <Link href="/dashboard/admin/tasks">
                        <div className="p-5 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <CheckSquare className="w-6 h-6 text-indigo-600" />
                                <h3 className="text-lg font-semibold text-gray-900">Task Catalog</h3>
                            </div>
                            <p className="text-sm text-gray-500">
                                Manage task catalog - master reference for all workflow tasks
                            </p>
                        </div>
                    </Link>

                    {/* Prompt Management */}
                    <Link href="/dashboard/admin/prompts">
                        <div className="p-5 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <FileText className="w-6 h-6 text-indigo-600" />
                                <h3 className="text-lg font-semibold text-gray-900">Prompt Management</h3>
                            </div>
                            <p className="text-sm text-gray-500">
                                Create, edit, and refine prompts for all agents
                            </p>
                        </div>
                    </Link>
                </div>
            </div>
        </div>
    );
}
