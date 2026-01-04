"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Users, Plus, Edit, Trash2, Shield, Mail, User as UserIcon, Eye, ChevronDown, ChevronRight } from "lucide-react";
import { useSession } from "next-auth/react";

interface User {
    id: number;
    auth_id: string;
    email: string;
    name: string | null;
    role: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

interface UserProfiles {
    basic: any;
    professional: any;
    communication: any;
    use_case: any;
    ai_preference: any;
    query_history: any;
}

interface SessionLink {
    id: number;
    session_id: number;
    query_text: string;
    module: string;
    workflow_name: string | null;
    strategy: string | null;
    session_status: string | null;
    consultant_strategy: string | null;
    created_at: string;
}

export default function ClientsPage() {
    const { data: session } = useSession();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [roleFilter, setRoleFilter] = useState<string>("");
    const [activeOnly, setActiveOnly] = useState(true);
    const [expandedUser, setExpandedUser] = useState<number | null>(null);
    const [userProfiles, setUserProfiles] = useState<Record<number, UserProfiles>>({});
    const [sessionLinks, setSessionLinks] = useState<Record<number, SessionLink[]>>({});
    const [loadingProfiles, setLoadingProfiles] = useState<Record<number, boolean>>({});
    const [editTab, setEditTab] = useState<"basic" | "profiles">("basic");
    const [profileFormData, setProfileFormData] = useState<any>({});

    // Form state
    const [formData, setFormData] = useState({
        auth_id: "",
        email: "",
        name: "",
        role: "user",
        is_active: true
    });

    useEffect(() => {
        fetchUsers();
    }, [roleFilter, activeOnly, session]);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const params = new URLSearchParams();
            if (roleFilter) params.append("role", roleFilter);
            params.append("active_only", activeOnly.toString());

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users?${params.toString()}`, {
                headers: {
                    "X-User-ID": session?.user?.id || ""
                }
            });

            if (!response.ok) {
                throw new Error("Failed to fetch users");
            }

            const data = await response.json();
            // The endpoint returns a list directly, not wrapped in a users property
            setUsers(Array.isArray(data) ? data : (data.users || []));
        } catch (error) {
            console.error("Error fetching users:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify({
                    auth_id: formData.auth_id,
                    email: formData.email,
                    name: formData.name || null,
                    role: formData.role
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Failed to create user");
            }

            await fetchUsers();
            setShowCreateModal(false);
            setFormData({ auth_id: "", email: "", name: "", role: "user", is_active: true });
        } catch (error) {
            console.error("Error creating user:", error);
            alert(error instanceof Error ? error.message : "Failed to create user");
        }
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser) return;

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users/${editingUser.id}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify({
                    email: formData.email || undefined,
                    name: formData.name || undefined,
                    role: formData.role || undefined,
                    is_active: formData.is_active
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Failed to update user");
            }

            await fetchUsers();
            setEditingUser(null);
            setFormData({ auth_id: "", email: "", name: "", role: "user", is_active: true });
        } catch (error) {
            console.error("Error updating user:", error);
            alert(error instanceof Error ? error.message : "Failed to update user");
        }
    };

    const handleDeleteUser = async (userId: number) => {
        if (!confirm("Are you sure you want to delete this user? This will deactivate their account.")) {
            return;
        }

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users/${userId}`, {
                method: "DELETE",
                headers: {
                    "X-User-ID": session?.user?.id || ""
                }
            });

            if (!response.ok) {
                throw new Error("Failed to delete user");
            }

            await fetchUsers();
        } catch (error) {
            console.error("Error deleting user:", error);
            alert("Failed to delete user");
        }
    };

    const openEditModal = async (user: User) => {
        setEditingUser(user);
        setFormData({
            auth_id: user.auth_id,
            email: user.email,
            name: user.name || "",
            role: user.role,
            is_active: user.is_active
        });
        setEditTab("basic");
        // Load user profiles for editing
        const profiles = await fetchUserProfiles(user.id);
        if (profiles) {
            setProfileFormData(profiles);
        }
    };

    const closeModals = () => {
        setShowCreateModal(false);
        setEditingUser(null);
        setFormData({ auth_id: "", email: "", name: "", role: "user", is_active: true });
        setProfileFormData({});
        setEditTab("basic");
    };

    const handleUpdateProfile = async (profileType: string, updates: any) => {
        if (!editingUser) return;
        
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const endpoint = `/api/users/${editingUser.id}/profiles/${profileType}`;
            const response = await fetch(`${apiUrl}${endpoint}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify(updates)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `Failed to update ${profileType} profile`);
            }

            // Refresh profiles and update form data
            const updatedProfiles = await fetchUserProfiles(editingUser.id);
            if (updatedProfiles) {
                setProfileFormData(updatedProfiles);
            }
            alert(`${profileType} profile updated successfully!`);
        } catch (error) {
            console.error(`Error updating ${profileType} profile:`, error);
            alert(error instanceof Error ? error.message : `Failed to update ${profileType} profile`);
        }
    };

    const getRoleBadgeColor = (role: string) => {
        switch (role) {
            case "admin":
                return "bg-red-100 text-red-800 border-red-200";
            case "user":
                return "bg-blue-100 text-blue-800 border-blue-200";
            case "viewer":
                return "bg-gray-100 text-gray-800 border-gray-200";
            default:
                return "bg-gray-100 text-gray-800 border-gray-200";
        }
    };

    const fetchUserProfiles = async (userId: number) => {
        if (userProfiles[userId]) {
            return userProfiles[userId];
        }
        
        setLoadingProfiles(prev => ({ ...prev, [userId]: true }));
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const [profilesRes, linksRes] = await Promise.all([
                fetch(`${apiUrl}/api/users/${userId}/profiles/all`, {
                    headers: { "X-User-ID": session?.user?.id || "" }
                }),
                fetch(`${apiUrl}/api/users/${userId}/session-links?limit=20`, {
                    headers: { "X-User-ID": session?.user?.id || "" }
                })
            ]);
            
            if (profilesRes.ok) {
                const profiles = await profilesRes.json();
                // Parse JSONB fields that might be strings
                if (profiles.query_history?.interaction_stats && typeof profiles.query_history.interaction_stats === "string") {
                    try {
                        profiles.query_history.interaction_stats = JSON.parse(profiles.query_history.interaction_stats || "{}");
                    } catch (e) {
                        console.warn("Failed to parse interaction_stats:", e);
                    }
                }
                if (profiles.query_history?.most_common_queries && typeof profiles.query_history.most_common_queries === "string") {
                    try {
                        profiles.query_history.most_common_queries = JSON.parse(profiles.query_history.most_common_queries || "[]");
                    } catch (e) {
                        console.warn("Failed to parse most_common_queries:", e);
                    }
                }
                if (profiles.use_case?.primary_workflows && typeof profiles.use_case.primary_workflows === "string") {
                    try {
                        profiles.use_case.primary_workflows = JSON.parse(profiles.use_case.primary_workflows || "[]");
                    } catch (e) {
                        console.warn("Failed to parse primary_workflows:", e);
                    }
                }
                setUserProfiles(prev => ({ ...prev, [userId]: profiles }));
                return profiles;
            }
            
            if (linksRes.ok) {
                const linksData = await linksRes.json();
                setSessionLinks(prev => ({ ...prev, [userId]: linksData.links || [] }));
            }
            return null;
        } catch (error) {
            console.error("Error fetching user profiles:", error);
            return null;
        } finally {
            setLoadingProfiles(prev => ({ ...prev, [userId]: false }));
        }
    };

    const handleToggleExpand = (userId: number) => {
        if (expandedUser === userId) {
            setExpandedUser(null);
        } else {
            setExpandedUser(userId);
            fetchUserProfiles(userId);
        }
    };

    const formatJsonValue = (value: any): string => {
        if (value === null || value === undefined) return "—";
        if (typeof value === "object") {
            return JSON.stringify(value, null, 2);
        }
        return String(value);
    };

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="border-b border-[var(--border-subtle)] p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/dashboard/admin">
                            <button className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors">
                                <ArrowLeft className="w-5 h-5 text-[var(--text-secondary)]" />
                            </button>
                        </Link>
                        <div>
                            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Client Management</h1>
                            <p className="text-sm text-[var(--text-secondary)] mt-1">Manage users and organizations</p>
                        </div>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        Add User
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="border-b border-[var(--border-subtle)] p-4 bg-[var(--bg-secondary)]">
                <div className="flex items-center gap-4">
                    <select
                        value={roleFilter}
                        onChange={(e) => setRoleFilter(e.target.value)}
                        className="px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                    >
                        <option value="">All Roles</option>
                        <option value="admin">Admin</option>
                        <option value="user">User</option>
                        <option value="viewer">Viewer</option>
                    </select>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={activeOnly}
                            onChange={(e) => setActiveOnly(e.target.checked)}
                            className="rounded"
                        />
                        <span className="text-sm text-[var(--text-secondary)]">Active only</span>
                    </label>
                </div>
            </div>

            {/* Users List */}
            <div className="flex-1 overflow-y-auto p-6">
                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="text-[var(--text-secondary)]">Loading users...</div>
                    </div>
                ) : users.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64">
                        <Users className="w-16 h-16 text-[var(--text-tertiary)] mb-4" />
                        <p className="text-[var(--text-secondary)]">No users found</p>
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {users.map((user) => (
                            <div
                                key={user.id}
                                className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg hover:border-[var(--primary-blue)] transition-colors"
                            >
                                <div className="p-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-4 flex-1">
                                            <button
                                                onClick={() => handleToggleExpand(user.id)}
                                                className="p-1 hover:bg-[var(--bg-hover)] rounded transition-colors"
                                            >
                                                {expandedUser === user.id ? (
                                                    <ChevronDown className="w-4 h-4 text-[var(--text-secondary)]" />
                                                ) : (
                                                    <ChevronRight className="w-4 h-4 text-[var(--text-secondary)]" />
                                                )}
                                            </button>
                                            <div className="w-10 h-10 bg-[var(--primary-blue)] rounded-full flex items-center justify-center">
                                                <UserIcon className="w-5 h-5 text-white" />
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <h3 className="font-semibold text-[var(--text-primary)]">
                                                        {user.name || user.email}
                                                    </h3>
                                                    <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getRoleBadgeColor(user.role)}`}>
                                                        {user.role}
                                                    </span>
                                                    {!user.is_active && (
                                                        <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-600 border border-gray-200">
                                                            Inactive
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
                                                    <div className="flex items-center gap-1">
                                                        <Mail className="w-3 h-3" />
                                                        {user.email}
                                                    </div>
                                                    <div className="flex items-center gap-1">
                                                        <Shield className="w-3 h-3" />
                                                        {user.auth_id.substring(0, 20)}...
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => openEditModal(user)}
                                                className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
                                                title="Edit user"
                                            >
                                                <Edit className="w-4 h-4 text-[var(--text-secondary)]" />
                                            </button>
                                            <button
                                                onClick={() => handleDeleteUser(user.id)}
                                                className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                                                title="Delete user"
                                            >
                                                <Trash2 className="w-4 h-4 text-red-600" />
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Profile View */}
                                {expandedUser === user.id && (
                                    <div className="border-t border-[var(--border-subtle)] p-4 bg-[var(--bg-secondary)]">
                                        {loadingProfiles[user.id] ? (
                                            <div className="text-center py-8 text-[var(--text-secondary)]">Loading profiles...</div>
                                        ) : (
                                            <div className="space-y-6">
                                                {/* Basic Profile */}
                                                <div>
                                                    <h4 className="font-semibold text-[var(--text-primary)] mb-2">Basic Profile</h4>
                                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                                        <div><span className="text-[var(--text-secondary)]">Preferred Name:</span> {String(userProfiles[user.id]?.basic?.preferred_name || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Phone:</span> {String(userProfiles[user.id]?.basic?.phone || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Mobile:</span> {String(userProfiles[user.id]?.basic?.mobile || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Timezone:</span> {String(userProfiles[user.id]?.basic?.timezone || "—")}</div>
                                                    </div>
                                                </div>

                                                {/* Professional Profile */}
                                                <div>
                                                    <h4 className="font-semibold text-[var(--text-primary)] mb-2">Professional Profile</h4>
                                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                                        <div><span className="text-[var(--text-secondary)]">Job Title:</span> {String(userProfiles[user.id]?.professional?.job_title || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Department:</span> {String(userProfiles[user.id]?.professional?.department || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Organization:</span> {String(userProfiles[user.id]?.professional?.organization || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Team:</span> {String(userProfiles[user.id]?.professional?.team_name || "—")}</div>
                                                    </div>
                                                </div>

                                                {/* Communication Profile */}
                                                <div>
                                                    <h4 className="font-semibold text-[var(--text-primary)] mb-2">Communication Profile</h4>
                                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                                        <div><span className="text-[var(--text-secondary)]">Style:</span> {String(userProfiles[user.id]?.communication?.communication_style || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Tone:</span> {String(userProfiles[user.id]?.communication?.tone_preference || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Format:</span> {String(userProfiles[user.id]?.communication?.response_format_preference || "—")}</div>
                                                    </div>
                                                </div>

                                                {/* AI Preference Profile */}
                                                <div>
                                                    <h4 className="font-semibold text-[var(--text-primary)] mb-2">AI Preferences</h4>
                                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                                        <div><span className="text-[var(--text-secondary)]">Preferred Strategy:</span> {String(userProfiles[user.id]?.ai_preference?.preferred_strategy || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Autonomy Level:</span> {String(userProfiles[user.id]?.ai_preference?.autonomy_level || "—")}</div>
                                                        <div><span className="text-[var(--text-secondary)]">Confidence Threshold:</span> {
                                                            typeof userProfiles[user.id]?.ai_preference?.confidence_threshold === "number" 
                                                                ? userProfiles[user.id].ai_preference.confidence_threshold 
                                                                : "—"
                                                        }</div>
                                                    </div>
                                                </div>

                                                {/* Use Case Profile */}
                                                {userProfiles[user.id]?.use_case?.primary_workflows && 
                                                 Array.isArray(userProfiles[user.id].use_case.primary_workflows) &&
                                                 userProfiles[user.id].use_case.primary_workflows.length > 0 && (
                                                    <div>
                                                        <h4 className="font-semibold text-[var(--text-primary)] mb-2">Primary Workflows</h4>
                                                        <div className="space-y-1 text-sm">
                                                            {userProfiles[user.id].use_case.primary_workflows.slice(0, 5).map((wf: any, idx: number) => (
                                                                <div key={idx} className="flex justify-between">
                                                                    <span>{wf.name || "Unknown"}</span>
                                                                    <span className="text-[var(--text-secondary)]">({wf.count || 0} uses)</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Query History Stats */}
                                                {userProfiles[user.id]?.query_history?.interaction_stats && (
                                                    <div>
                                                        <h4 className="font-semibold text-[var(--text-primary)] mb-2">Query Statistics</h4>
                                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                                            <div>
                                                                <span className="text-[var(--text-secondary)]">Total Queries:</span>{" "}
                                                                {(() => {
                                                                    try {
                                                                        const stats = userProfiles[user.id].query_history.interaction_stats;
                                                                        const parsed = typeof stats === "string" ? JSON.parse(stats || "{}") : (stats || {});
                                                                        const total = parsed?.total_queries;
                                                                        return typeof total === "number" ? total : 0;
                                                                    } catch (e) {
                                                                        return 0;
                                                                    }
                                                                })()}
                                                            </div>
                                                            <div>
                                                                <span className="text-[var(--text-secondary)]">Avg Query Length:</span>{" "}
                                                                {(() => {
                                                                    try {
                                                                        const stats = userProfiles[user.id].query_history.interaction_stats;
                                                                        const parsed = typeof stats === "string" ? JSON.parse(stats || "{}") : (stats || {});
                                                                        const avg = parsed?.avg_query_length;
                                                                        return typeof avg === "number" ? Math.round(avg) : 0;
                                                                    } catch (e) {
                                                                        return 0;
                                                                    }
                                                                })()}
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Session Links */}
                                                {sessionLinks[user.id] && sessionLinks[user.id].length > 0 && (
                                                    <div>
                                                        <h4 className="font-semibold text-[var(--text-primary)] mb-2">Recent Session Links ({sessionLinks[user.id].length})</h4>
                                                        <div className="space-y-2 max-h-48 overflow-y-auto">
                                                            {sessionLinks[user.id].slice(0, 5).map((link) => (
                                                                <div key={link.id} className="text-sm p-2 bg-[var(--bg-primary)] rounded border border-[var(--border-subtle)]">
                                                                    <div className="flex justify-between items-start mb-1">
                                                                        <span className="font-medium text-[var(--text-primary)]">
                                                                            Session #{link.session_id}
                                                                        </span>
                                                                        <span className="text-xs text-[var(--text-secondary)]">
                                                                            {link.strategy || link.consultant_strategy || "—"}
                                                                        </span>
                                                                    </div>
                                                                    <div className="text-[var(--text-secondary)] text-xs truncate">
                                                                        {link.query_text || "—"}
                                                                    </div>
                                                                    {link.workflow_name && (
                                                                        <div className="text-xs text-[var(--text-tertiary)] mt-1">
                                                                            Workflow: {link.workflow_name}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Create/Edit Modal */}
            {(showCreateModal || editingUser) && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-[var(--bg-primary)] rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto border border-[var(--border-subtle)]">
                        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">
                            {editingUser ? "Edit User" : "Create User"}
                        </h2>
                        
                        {editingUser && (
                            <div className="flex gap-2 mb-4 border-b border-[var(--border-subtle)]">
                                <button
                                    type="button"
                                    onClick={() => setEditTab("basic")}
                                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                                        editTab === "basic"
                                            ? "border-[var(--primary-blue)] text-[var(--primary-blue)]"
                                            : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                                    }`}
                                >
                                    Basic Info
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setEditTab("profiles")}
                                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                                        editTab === "profiles"
                                            ? "border-[var(--primary-blue)] text-[var(--primary-blue)]"
                                            : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                                    }`}
                                >
                                    Profiles
                                </button>
                            </div>
                        )}

                        {editTab === "basic" && (
                            <form onSubmit={editingUser ? handleUpdateUser : handleCreateUser}>
                            {!editingUser && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                                        Auth ID
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.auth_id}
                                        onChange={(e) => setFormData({ ...formData, auth_id: e.target.value })}
                                        required
                                        className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                        placeholder="Google Auth Subject ID"
                                    />
                                </div>
                            )}
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                    className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                                    Name
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                                    Role
                                </label>
                                <select
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                    required
                                    className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                >
                                    <option value="user">User</option>
                                    <option value="admin">Admin</option>
                                    <option value="viewer">Viewer</option>
                                </select>
                            </div>
                            {editingUser && (
                                <div className="mb-4">
                                    <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={formData.is_active}
                                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                            className="rounded"
                                        />
                                        <span className="text-sm text-[var(--text-secondary)]">Active</span>
                                    </label>
                                </div>
                            )}
                            <div className="flex gap-2 justify-end">
                                <button
                                    type="button"
                                    onClick={closeModals}
                                    className="px-4 py-2 border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors"
                                >
                                    {editingUser ? "Update" : "Create"}
                                </button>
                            </div>
                        </form>
                        )}

                        {editTab === "profiles" && editingUser && (
                            <div className="space-y-6">
                                {/* Basic Profile */}
                                <div>
                                    <h3 className="font-semibold text-[var(--text-primary)] mb-3">Basic Profile</h3>
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Preferred Name</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.basic?.preferred_name || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    basic: { ...profileFormData.basic, preferred_name: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Phone</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.basic?.phone || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    basic: { ...profileFormData.basic, phone: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Mobile</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.basic?.mobile || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    basic: { ...profileFormData.basic, mobile: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Timezone</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.basic?.timezone || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    basic: { ...profileFormData.basic, timezone: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                                placeholder="America/New_York"
                                            />
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handleUpdateProfile("basic", profileFormData.basic || {})}
                                        className="px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors text-sm"
                                    >
                                        Update Basic Profile
                                    </button>
                                </div>

                                {/* Professional Profile */}
                                <div className="border-t border-[var(--border-subtle)] pt-4">
                                    <h3 className="font-semibold text-[var(--text-primary)] mb-3">Professional Profile</h3>
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Job Title</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.professional?.job_title || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    professional: { ...profileFormData.professional, job_title: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Department</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.professional?.department || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    professional: { ...profileFormData.professional, department: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Organization</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.professional?.organization || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    professional: { ...profileFormData.professional, organization: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Team Name</label>
                                            <input
                                                type="text"
                                                defaultValue={profileFormData.professional?.team_name || ""}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    professional: { ...profileFormData.professional, team_name: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            />
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handleUpdateProfile("professional", profileFormData.professional || {})}
                                        className="px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors text-sm"
                                    >
                                        Update Professional Profile
                                    </button>
                                </div>

                                {/* Communication Profile */}
                                <div className="border-t border-[var(--border-subtle)] pt-4">
                                    <h3 className="font-semibold text-[var(--text-primary)] mb-3">Communication Profile</h3>
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Communication Style</label>
                                            <select
                                                defaultValue={profileFormData.communication?.communication_style || "professional"}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    communication: { ...profileFormData.communication, communication_style: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            >
                                                <option value="professional">Professional</option>
                                                <option value="casual">Casual</option>
                                                <option value="formal">Formal</option>
                                                <option value="friendly">Friendly</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Tone Preference</label>
                                            <select
                                                defaultValue={profileFormData.communication?.tone_preference || "balanced"}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    communication: { ...profileFormData.communication, tone_preference: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            >
                                                <option value="balanced">Balanced</option>
                                                <option value="concise">Concise</option>
                                                <option value="detailed">Detailed</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Response Format</label>
                                            <select
                                                defaultValue={profileFormData.communication?.response_format_preference || "structured"}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    communication: { ...profileFormData.communication, response_format_preference: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            >
                                                <option value="structured">Structured</option>
                                                <option value="bullet_points">Bullet Points</option>
                                                <option value="conversational">Conversational</option>
                                            </select>
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handleUpdateProfile("communication", profileFormData.communication || {})}
                                        className="px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors text-sm"
                                    >
                                        Update Communication Profile
                                    </button>
                                </div>

                                {/* AI Preference Profile */}
                                <div className="border-t border-[var(--border-subtle)] pt-4">
                                    <h3 className="font-semibold text-[var(--text-primary)] mb-3">AI Preferences</h3>
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div>
                                            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">Autonomy Level</label>
                                            <select
                                                defaultValue={profileFormData.ai_preference?.autonomy_level || "balanced"}
                                                onChange={(e) => setProfileFormData({
                                                    ...profileFormData,
                                                    ai_preference: { ...profileFormData.ai_preference, autonomy_level: e.target.value }
                                                })}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)]"
                                            >
                                                <option value="balanced">Balanced</option>
                                                <option value="autonomous">Autonomous</option>
                                                <option value="consultative">Consultative</option>
                                            </select>
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handleUpdateProfile("ai-preference", profileFormData.ai_preference || {})}
                                        className="px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors text-sm"
                                    >
                                        Update AI Preferences
                                    </button>
                                </div>

                                {/* Most Common Use Cases */}
                                <div className="border-t border-[var(--border-subtle)] pt-4">
                                    <h3 className="font-semibold text-[var(--text-primary)] mb-3">Most Common Use Cases</h3>
                                    {profileFormData.use_case?.primary_workflows && 
                                     Array.isArray(profileFormData.use_case.primary_workflows) &&
                                     profileFormData.use_case.primary_workflows.length > 0 ? (
                                        <div className="space-y-2 mb-4">
                                            {profileFormData.use_case.primary_workflows.map((workflow: any, idx: number) => (
                                                <div key={idx} className="flex items-center justify-between p-3 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)]">
                                                    <div>
                                                        <div className="font-medium text-[var(--text-primary)]">
                                                            {workflow.name || "Unknown Workflow"}
                                                        </div>
                                                        {workflow.description && (
                                                            <div className="text-sm text-[var(--text-secondary)] mt-1">
                                                                {workflow.description}
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="text-sm text-[var(--text-secondary)]">
                                                        {workflow.count || 0} uses
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-sm text-[var(--text-secondary)] mb-4 p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)]">
                                            No use cases tracked yet. Use cases will appear here as the user interacts with workflows.
                                        </div>
                                    )}
                                </div>

                                <div className="flex gap-2 justify-end pt-4 border-t border-[var(--border-subtle)]">
                                    <button
                                        type="button"
                                        onClick={closeModals}
                                        className="px-4 py-2 border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                                    >
                                        Close
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
