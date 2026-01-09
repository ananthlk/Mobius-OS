"use client";

import Link from "next/link";
import { Server, FileText, Users, CheckSquare, Settings, Database } from "lucide-react";
import AdminChat from "@/components/admin/AdminChat";

export default function AdminPage() {
    return (
        <div className="h-full flex flex-col md:flex-row">
            {/* Left Side: Chat Interface (60-70% on desktop) */}
            <div className="flex-1 md:w-[65%] h-full border-r border-[var(--border-subtle)]">
                <AdminChat 
                    placeholder="Ask about system configuration, admin tasks, or get help..."
                    emptyStateTitle="Admin Assistant"
                    emptyStateDescription="I can help you manage system configuration, troubleshoot issues, or answer questions about the admin panel."
                />
            </div>

            {/* Right Side: Admin Section Links (30-40% on desktop) */}
            <div className="md:w-[35%] h-full overflow-y-auto pattern-board-light p-6">
                <div className="mb-6">
                    <div className="flex items-center gap-3 mb-2">
                        <Settings className="w-6 h-6 text-[var(--text-secondary)]" />
                        <h1 className="text-xl font-semibold text-[var(--text-primary)]">Admin Sections</h1>
                    </div>
                    <p className="text-sm text-[var(--text-secondary)]">
                        Quick access to system administration tools
                    </p>
                </div>

                <div className="space-y-4">
                    {/* Client Management */}
                    <Link href="/dashboard/admin/clients">
                        <div className="p-5 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] hover:border-[var(--primary-blue)] hover:shadow-[var(--shadow-md)] transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <Users className="w-6 h-6 text-[var(--primary-blue)]" />
                                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Client Management</h3>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Manage users, roles, and permissions
                            </p>
                        </div>
                    </Link>

                    {/* LLM Management */}
                    <Link href="/dashboard/admin/llms">
                        <div className="p-5 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] hover:border-[var(--primary-blue)] hover:shadow-[var(--shadow-md)] transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <Server className="w-6 h-6 text-[var(--primary-blue)]" />
                                <h3 className="text-lg font-semibold text-[var(--text-primary)]">LLM Management</h3>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Configure AI providers, models, and governance rules
                            </p>
                        </div>
                    </Link>

                    {/* Task Catalog */}
                    <Link href="/dashboard/admin/tasks">
                        <div className="p-5 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] hover:border-[var(--primary-blue)] hover:shadow-[var(--shadow-md)] transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <CheckSquare className="w-6 h-6 text-[var(--primary-blue)]" />
                                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Task Catalog</h3>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Manage task catalog - master reference for all workflow tasks
                            </p>
                        </div>
                    </Link>

                    {/* Prompt Management */}
                    <Link href="/dashboard/admin/prompts">
                        <div className="p-5 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] hover:border-[var(--primary-blue)] hover:shadow-[var(--shadow-md)] transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <FileText className="w-6 h-6 text-[var(--primary-blue)]" />
                                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Prompt Management</h3>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Create, edit, and refine prompts for all agents
                            </p>
                        </div>
                    </Link>

                    {/* Database Explorer */}
                    <Link href="/dashboard/admin/db">
                        <div className="p-5 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] hover:border-[var(--primary-blue)] hover:shadow-[var(--shadow-md)] transition-all cursor-pointer">
                            <div className="flex items-center gap-3 mb-2">
                                <Database className="w-6 h-6 text-[var(--primary-blue)]" />
                                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Database Explorer</h3>
                            </div>
                            <p className="text-sm text-[var(--text-secondary)]">
                                Browse tables, execute SELECT queries, and search by session ID
                            </p>
                        </div>
                    </Link>
                </div>
            </div>
        </div>
    );
}
