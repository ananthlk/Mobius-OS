"use client";

import Link from "next/link";
import { Server, FileText, Settings } from "lucide-react";

export default function AdminPage() {
    return (
        <div className="h-full flex flex-col items-center justify-center p-8">
            <div className="w-16 h-16 bg-slate-100 text-slate-600 rounded-2xl flex items-center justify-center mb-6">
                <Settings className="w-8 h-8" />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">System Administration</h1>
            <p className="text-gray-500 max-w-md mb-8">
                Manage system configuration, LLM providers, and prompts.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
                <Link href="/dashboard/admin/llms">
                    <div className="p-6 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer">
                        <div className="flex items-center gap-3 mb-2">
                            <Server className="w-6 h-6 text-indigo-600" />
                            <h3 className="text-lg font-semibold text-gray-900">LLM Management</h3>
                        </div>
                        <p className="text-sm text-gray-500">
                            Configure AI providers, models, and governance rules
                        </p>
                    </div>
                </Link>

                <Link href="/dashboard/admin/prompts">
                    <div className="p-6 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-md transition-all cursor-pointer">
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
    );
}
