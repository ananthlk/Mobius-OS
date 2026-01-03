"use client";

import Link from "next/link";
import { ArrowLeft, Users, Building2 } from "lucide-react";

export default function ClientsPage() {
    return (
        <div className="h-full flex flex-col items-center justify-center p-8">
            <div className="w-16 h-16 bg-slate-100 text-slate-600 rounded-2xl flex items-center justify-center mb-6">
                <Users className="w-8 h-8" />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Client Management</h1>
            <p className="text-gray-500 max-w-md mb-8 text-center">
                Manage users and organizations. This feature is currently under development.
            </p>
            
            <div className="bg-white border border-gray-200 rounded-xl p-6 max-w-md mb-8">
                <div className="flex items-start gap-4">
                    <Building2 className="w-6 h-6 text-indigo-600 mt-1" />
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-2">Coming Soon</h3>
                        <p className="text-sm text-gray-500">
                            Client management will include:
                        </p>
                        <ul className="mt-3 space-y-2 text-sm text-gray-600">
                            <li className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full"></span>
                                User account management
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full"></span>
                                Organization management
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 bg-indigo-600 rounded-full"></span>
                                Access control and permissions
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <Link href="/dashboard/admin">
                <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                    <ArrowLeft className="w-4 h-4" />
                    Back to Admin Dashboard
                </button>
            </Link>
        </div>
    );
}

