"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, User, Mail, Shield, Save } from "lucide-react";
import { useSession } from "next-auth/react";

interface UserProfile {
    user_id: number;
    preferences: Record<string, any>;
    settings: Record<string, any>;
    metadata: Record<string, any>;
}

export default function ProfilePage() {
    const { data: session } = useSession();
    const [user, setUser] = useState<any>(null);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (session?.user?.id) {
            fetchUserData();
        }
    }, [session]);

    const fetchUserData = async () => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            // Get user by auth_id (session.user.id is the auth_id)
            const userResponse = await fetch(`${apiUrl}/api/users/auth/${session?.user?.id}`, {
                headers: {
                    "X-User-ID": session?.user?.id || ""
                }
            });

            if (userResponse.ok) {
                const userData = await userResponse.json();
                setUser(userData);

                // Get user profile
                const profileResponse = await fetch(`${apiUrl}/api/users/${userData.id}/profile`, {
                    headers: {
                        "X-User-ID": session?.user?.id || ""
                    }
                });

                if (profileResponse.ok) {
                    const profileData = await profileResponse.json();
                    setProfile(profileData);
                }
            }
        } catch (error) {
            console.error("Error fetching user data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSavePreferences = async () => {
        if (!user || !profile) return;

        try {
            setSaving(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users/${user.id}/profile`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify({
                    preferences: profile.preferences,
                    settings: profile.settings,
                    metadata: profile.metadata
                })
            });

            if (!response.ok) {
                throw new Error("Failed to save preferences");
            }

            const updated = await response.json();
            setProfile(updated);
            alert("Preferences saved successfully");
        } catch (error) {
            console.error("Error saving preferences:", error);
            alert("Failed to save preferences");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">Loading profile...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">User not found</div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="border-b border-[var(--border-subtle)] p-6">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <button className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors">
                            <ArrowLeft className="w-5 h-5 text-[var(--text-secondary)]" />
                        </button>
                    </Link>
                    <div>
                        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Profile</h1>
                        <p className="text-sm text-[var(--text-secondary)] mt-1">Manage your account settings and preferences</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-2xl space-y-6">
                    {/* User Information */}
                    <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Account Information</h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <User className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Name</div>
                                    <div className="text-[var(--text-primary)]">{user.name || "Not set"}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Mail className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Email</div>
                                    <div className="text-[var(--text-primary)]">{user.email}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Shield className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Role</div>
                                    <div className="text-[var(--text-primary)] capitalize">{user.role}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Preferences */}
                    {profile && (
                        <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Preferences</h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                        Preferences (JSON)
                                    </label>
                                    <textarea
                                        value={JSON.stringify(profile.preferences, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const prefs = JSON.parse(e.target.value);
                                                setProfile({ ...profile, preferences: prefs });
                                            } catch (err) {
                                                // Invalid JSON, ignore
                                            }
                                        }}
                                        className="w-full h-32 px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono text-sm"
                                    />
                                </div>
                                <button
                                    onClick={handleSavePreferences}
                                    disabled={saving}
                                    className="flex items-center gap-2 px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50"
                                >
                                    <Save className="w-4 h-4" />
                                    {saving ? "Saving..." : "Save Preferences"}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}


import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, User, Mail, Shield, Save } from "lucide-react";
import { useSession } from "next-auth/react";

interface UserProfile {
    user_id: number;
    preferences: Record<string, any>;
    settings: Record<string, any>;
    metadata: Record<string, any>;
}

export default function ProfilePage() {
    const { data: session } = useSession();
    const [user, setUser] = useState<any>(null);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (session?.user?.id) {
            fetchUserData();
        }
    }, [session]);

    const fetchUserData = async () => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            // Get user by auth_id (session.user.id is the auth_id)
            const userResponse = await fetch(`${apiUrl}/api/users/auth/${session?.user?.id}`, {
                headers: {
                    "X-User-ID": session?.user?.id || ""
                }
            });

            if (userResponse.ok) {
                const userData = await userResponse.json();
                setUser(userData);

                // Get user profile
                const profileResponse = await fetch(`${apiUrl}/api/users/${userData.id}/profile`, {
                    headers: {
                        "X-User-ID": session?.user?.id || ""
                    }
                });

                if (profileResponse.ok) {
                    const profileData = await profileResponse.json();
                    setProfile(profileData);
                }
            }
        } catch (error) {
            console.error("Error fetching user data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSavePreferences = async () => {
        if (!user || !profile) return;

        try {
            setSaving(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users/${user.id}/profile`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify({
                    preferences: profile.preferences,
                    settings: profile.settings,
                    metadata: profile.metadata
                })
            });

            if (!response.ok) {
                throw new Error("Failed to save preferences");
            }

            const updated = await response.json();
            setProfile(updated);
            alert("Preferences saved successfully");
        } catch (error) {
            console.error("Error saving preferences:", error);
            alert("Failed to save preferences");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">Loading profile...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">User not found</div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="border-b border-[var(--border-subtle)] p-6">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <button className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors">
                            <ArrowLeft className="w-5 h-5 text-[var(--text-secondary)]" />
                        </button>
                    </Link>
                    <div>
                        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Profile</h1>
                        <p className="text-sm text-[var(--text-secondary)] mt-1">Manage your account settings and preferences</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-2xl space-y-6">
                    {/* User Information */}
                    <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Account Information</h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <User className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Name</div>
                                    <div className="text-[var(--text-primary)]">{user.name || "Not set"}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Mail className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Email</div>
                                    <div className="text-[var(--text-primary)]">{user.email}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Shield className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Role</div>
                                    <div className="text-[var(--text-primary)] capitalize">{user.role}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Preferences */}
                    {profile && (
                        <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Preferences</h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                        Preferences (JSON)
                                    </label>
                                    <textarea
                                        value={JSON.stringify(profile.preferences, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const prefs = JSON.parse(e.target.value);
                                                setProfile({ ...profile, preferences: prefs });
                                            } catch (err) {
                                                // Invalid JSON, ignore
                                            }
                                        }}
                                        className="w-full h-32 px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono text-sm"
                                    />
                                </div>
                                <button
                                    onClick={handleSavePreferences}
                                    disabled={saving}
                                    className="flex items-center gap-2 px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50"
                                >
                                    <Save className="w-4 h-4" />
                                    {saving ? "Saving..." : "Save Preferences"}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}


import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, User, Mail, Shield, Save } from "lucide-react";
import { useSession } from "next-auth/react";

interface UserProfile {
    user_id: number;
    preferences: Record<string, any>;
    settings: Record<string, any>;
    metadata: Record<string, any>;
}

export default function ProfilePage() {
    const { data: session } = useSession();
    const [user, setUser] = useState<any>(null);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (session?.user?.id) {
            fetchUserData();
        }
    }, [session]);

    const fetchUserData = async () => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            // Get user by auth_id (session.user.id is the auth_id)
            const userResponse = await fetch(`${apiUrl}/api/users/auth/${session?.user?.id}`, {
                headers: {
                    "X-User-ID": session?.user?.id || ""
                }
            });

            if (userResponse.ok) {
                const userData = await userResponse.json();
                setUser(userData);

                // Get user profile
                const profileResponse = await fetch(`${apiUrl}/api/users/${userData.id}/profile`, {
                    headers: {
                        "X-User-ID": session?.user?.id || ""
                    }
                });

                if (profileResponse.ok) {
                    const profileData = await profileResponse.json();
                    setProfile(profileData);
                }
            }
        } catch (error) {
            console.error("Error fetching user data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSavePreferences = async () => {
        if (!user || !profile) return;

        try {
            setSaving(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users/${user.id}/profile`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify({
                    preferences: profile.preferences,
                    settings: profile.settings,
                    metadata: profile.metadata
                })
            });

            if (!response.ok) {
                throw new Error("Failed to save preferences");
            }

            const updated = await response.json();
            setProfile(updated);
            alert("Preferences saved successfully");
        } catch (error) {
            console.error("Error saving preferences:", error);
            alert("Failed to save preferences");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">Loading profile...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">User not found</div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="border-b border-[var(--border-subtle)] p-6">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <button className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors">
                            <ArrowLeft className="w-5 h-5 text-[var(--text-secondary)]" />
                        </button>
                    </Link>
                    <div>
                        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Profile</h1>
                        <p className="text-sm text-[var(--text-secondary)] mt-1">Manage your account settings and preferences</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-2xl space-y-6">
                    {/* User Information */}
                    <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Account Information</h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <User className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Name</div>
                                    <div className="text-[var(--text-primary)]">{user.name || "Not set"}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Mail className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Email</div>
                                    <div className="text-[var(--text-primary)]">{user.email}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Shield className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Role</div>
                                    <div className="text-[var(--text-primary)] capitalize">{user.role}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Preferences */}
                    {profile && (
                        <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Preferences</h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                        Preferences (JSON)
                                    </label>
                                    <textarea
                                        value={JSON.stringify(profile.preferences, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const prefs = JSON.parse(e.target.value);
                                                setProfile({ ...profile, preferences: prefs });
                                            } catch (err) {
                                                // Invalid JSON, ignore
                                            }
                                        }}
                                        className="w-full h-32 px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono text-sm"
                                    />
                                </div>
                                <button
                                    onClick={handleSavePreferences}
                                    disabled={saving}
                                    className="flex items-center gap-2 px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50"
                                >
                                    <Save className="w-4 h-4" />
                                    {saving ? "Saving..." : "Save Preferences"}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}


import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, User, Mail, Shield, Save } from "lucide-react";
import { useSession } from "next-auth/react";

interface UserProfile {
    user_id: number;
    preferences: Record<string, any>;
    settings: Record<string, any>;
    metadata: Record<string, any>;
}

export default function ProfilePage() {
    const { data: session } = useSession();
    const [user, setUser] = useState<any>(null);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (session?.user?.id) {
            fetchUserData();
        }
    }, [session]);

    const fetchUserData = async () => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            // Get user by auth_id (session.user.id is the auth_id)
            const userResponse = await fetch(`${apiUrl}/api/users/auth/${session?.user?.id}`, {
                headers: {
                    "X-User-ID": session?.user?.id || ""
                }
            });

            if (userResponse.ok) {
                const userData = await userResponse.json();
                setUser(userData);

                // Get user profile
                const profileResponse = await fetch(`${apiUrl}/api/users/${userData.id}/profile`, {
                    headers: {
                        "X-User-ID": session?.user?.id || ""
                    }
                });

                if (profileResponse.ok) {
                    const profileData = await profileResponse.json();
                    setProfile(profileData);
                }
            }
        } catch (error) {
            console.error("Error fetching user data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSavePreferences = async () => {
        if (!user || !profile) return;

        try {
            setSaving(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/users/${user.id}/profile`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": session?.user?.id || ""
                },
                body: JSON.stringify({
                    preferences: profile.preferences,
                    settings: profile.settings,
                    metadata: profile.metadata
                })
            });

            if (!response.ok) {
                throw new Error("Failed to save preferences");
            }

            const updated = await response.json();
            setProfile(updated);
            alert("Preferences saved successfully");
        } catch (error) {
            console.error("Error saving preferences:", error);
            alert("Failed to save preferences");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">Loading profile...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-[var(--text-secondary)]">User not found</div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="border-b border-[var(--border-subtle)] p-6">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <button className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors">
                            <ArrowLeft className="w-5 h-5 text-[var(--text-secondary)]" />
                        </button>
                    </Link>
                    <div>
                        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Profile</h1>
                        <p className="text-sm text-[var(--text-secondary)] mt-1">Manage your account settings and preferences</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-2xl space-y-6">
                    {/* User Information */}
                    <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Account Information</h2>
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <User className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Name</div>
                                    <div className="text-[var(--text-primary)]">{user.name || "Not set"}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Mail className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Email</div>
                                    <div className="text-[var(--text-primary)]">{user.email}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <Shield className="w-5 h-5 text-[var(--text-secondary)]" />
                                <div>
                                    <div className="text-sm text-[var(--text-secondary)]">Role</div>
                                    <div className="text-[var(--text-primary)] capitalize">{user.role}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Preferences */}
                    {profile && (
                        <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-lg p-6">
                            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Preferences</h2>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                        Preferences (JSON)
                                    </label>
                                    <textarea
                                        value={JSON.stringify(profile.preferences, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const prefs = JSON.parse(e.target.value);
                                                setProfile({ ...profile, preferences: prefs });
                                            } catch (err) {
                                                // Invalid JSON, ignore
                                            }
                                        }}
                                        className="w-full h-32 px-3 py-2 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono text-sm"
                                    />
                                </div>
                                <button
                                    onClick={handleSavePreferences}
                                    disabled={saving}
                                    className="flex items-center gap-2 px-4 py-2 bg-[var(--primary-blue)] text-white rounded-lg hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50"
                                >
                                    <Save className="w-4 h-4" />
                                    {saving ? "Saving..." : "Save Preferences"}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

