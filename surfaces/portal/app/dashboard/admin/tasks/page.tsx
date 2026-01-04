"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, CheckSquare, Search, Plus, Save, Trash2, X, Copy } from "lucide-react";
import TaskFormFields from "./TaskFormFields";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Task {
    task_id?: string;
    task_key: string;
    name: string;
    description?: string;
    status: string;
    version?: number;
    schema_version?: string;
    classification?: {
        domain?: string;
        category?: string;
        tags?: string[];
        priority?: string;
    };
    contract?: any;
    automation?: any;
    tool_binding_defaults?: any;
    information?: any;
    policy?: any;
    temporal?: any;
    escalation?: any;
    dependencies?: any;
    failure?: any;
    ui?: any;
    governance?: any;
    created_at_utc?: string;
    updated_at_utc?: string;
    created_by?: string;
    updated_by?: string;
}

export default function TaskCatalogPage() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [selectedTask, setSelectedTask] = useState<Task | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [schema, setSchema] = useState<any>(null);
    const [schemaLoading, setSchemaLoading] = useState(true);

    // Form state
    const [formData, setFormData] = useState<Partial<Task>>({
        name: "",
        description: "",
        status: "draft",
        classification: {},
        automation: {},
        tool_binding_defaults: {},
        information: {},
        policy: {},
        temporal: {},
        escalation: {},
        dependencies: {},
        failure: {},
        ui: {},
        governance: {},
    });

    useEffect(() => {
        fetchTasks();
        fetchSchema();
    }, [statusFilter]);

    const fetchSchema = async () => {
        setSchemaLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/task-catalog/schema`);
            if (response.ok) {
                const schemaData = await response.json();
                setSchema(schemaData);
            } else {
                console.error("Failed to fetch schema:", response.statusText);
            }
        } catch (error) {
            console.error("Error fetching schema:", error);
        } finally {
            setSchemaLoading(false);
        }
    };

    useEffect(() => {
        if (selectedTask) {
            // Merge with defaults from schema
            const merged = { ...selectedTask };
            if (schema) {
                Object.keys(schema).forEach((sectionKey) => {
                    if (sectionKey !== "schema_name" && sectionKey !== "schema_version" && sectionKey !== "audit") {
                        if (!merged[sectionKey as keyof Task]) {
                            merged[sectionKey as keyof Task] = {};
                        }
                    }
                });
            }
            setFormData(merged);
        } else {
            // Initialize with defaults from schema
            const defaults: Partial<Task> = {
                name: "",
                description: "",
                status: "draft",
            };

            if (schema) {
                Object.keys(schema).forEach((sectionKey) => {
                    if (sectionKey !== "schema_name" && sectionKey !== "schema_version" && sectionKey !== "audit") {
                        const sectionSchema = schema[sectionKey];
                        const sectionDefaults: any = {};
                        
                        const applyDefaults = (obj: any, schemaObj: any, path: string[] = []) => {
                            Object.entries(schemaObj).forEach(([key, value]: [string, any]) => {
                                if (value && typeof value === "object" && "default" in value) {
                                    sectionDefaults[key] = value.default;
                                } else if (value && typeof value === "object" && !Array.isArray(value)) {
                                    sectionDefaults[key] = {};
                                    applyDefaults(sectionDefaults[key], value, [...path, key]);
                                }
                            });
                        };

                        applyDefaults(sectionDefaults, sectionSchema);
                        (defaults as any)[sectionKey] = sectionDefaults;
                    }
                });
            } else {
                // Fallback defaults if schema not loaded
                defaults.classification = {};
                defaults.automation = {};
                defaults.tool_binding_defaults = {};
                defaults.information = {};
                defaults.policy = {};
                defaults.temporal = {};
                defaults.escalation = {};
                defaults.dependencies = {};
                defaults.failure = {};
                defaults.ui = {};
                defaults.governance = {};
            }

            setFormData(defaults);
        }
    }, [selectedTask, schema]);

    const fetchTasks = async () => {
        setLoading(true);
        try {
            const filters: any = {};
            if (statusFilter !== "all") {
                filters.status = statusFilter;
            }

            const queryParams = new URLSearchParams();
            if (filters.status) queryParams.append("status", filters.status);

            const url = `${API_URL}/api/task-catalog/tasks${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;
            const response = await fetch(url);
            
            if (response.ok) {
                const data = await response.json();
                setTasks(data.tasks || data || []);
            } else {
                console.error("Failed to fetch tasks:", response.statusText);
            }
        } catch (error) {
            console.error("Error fetching tasks:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchTask = async (task_key: string) => {
        try {
            const response = await fetch(`${API_URL}/api/task-catalog/tasks/${task_key}`);
            if (response.ok) {
                const task = await response.json();
                setSelectedTask(task);
                return task;
            }
        } catch (error) {
            console.error("Error fetching task:", error);
        }
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            fetchTasks();
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${API_URL}/api/task-catalog/tasks/search`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    query: searchQuery,
                    filters: statusFilter !== "all" ? { status: statusFilter } : {}
                }),
            });

            if (response.ok) {
                const data = await response.json();
                setTasks(data.tasks || []);
            }
        } catch (error) {
            console.error("Error searching tasks:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleTaskClick = async (task: Task) => {
        await fetchTask(task.task_key);
    };

    const handleCreateNew = () => {
        setSelectedTask(null);
        setFormData({
            name: "",
            description: "",
            status: "draft",
            classification: { domain: "", category: "", tags: [] },
        });
    };

    const handleClone = async (task: Task) => {
        // Fetch full task details if not already loaded
        const fullTask = await fetchTask(task.task_key);
        if (!fullTask) return;

        // Clone the task data but clear unique fields
        const clonedData: Partial<Task> = {
            ...fullTask,
            task_key: "", // Clear task_key - will be generated from name
            name: `${fullTask.name} (Copy)`, // Suggest a new name
            version: 1, // Reset version
            status: "draft", // Reset to draft
            // Clear timestamps and actors
            created_at_utc: undefined,
            updated_at_utc: undefined,
            created_by: undefined,
            updated_by: undefined,
            task_id: undefined, // New task will get a new UUID
        };

        setSelectedTask(null); // Clear selection so it's treated as new
        setFormData(clonedData);
    };

    const handleFieldChange = (path: string[], value: any) => {
        setFormData((prev) => {
            const newData = { ...prev };
            let current: any = newData;

            // Navigate to the parent object
            for (let i = 0; i < path.length - 1; i++) {
                if (!current[path[i]]) {
                    current[path[i]] = {};
                }
                current = current[path[i]];
            }

            // Set the value
            current[path[path.length - 1]] = value;

            return newData;
        });
    };

    const handleSave = async () => {
        if (!formData.name) {
            alert("Task name is required");
            return;
        }

        setSaving(true);
        try {
            if (selectedTask) {
                // Update existing task
                const response = await fetch(
                    `${API_URL}/api/task-catalog/tasks/${selectedTask.task_key}`,
                    {
                        method: "PATCH",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            updates: formData,
                        }),
                    }
                );

                if (response.ok) {
                    await fetchTasks();
                    await fetchTask(selectedTask.task_key);
                    alert("Task updated successfully");
                } else {
                    const error = await response.json();
                    alert(`Failed to update task: ${error.detail || response.statusText}`);
                }
            } else {
                // Create new task
                // Generate task_key from name if not provided
                const task_key = formData.task_key || formData.name.toLowerCase().replace(/[^a-z0-9]+/g, "_");
                
                const response = await fetch(`${API_URL}/api/task-catalog/tasks`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        task_data: {
                            ...formData,
                            task_key,
                        },
                    }),
                });

                if (response.ok) {
                    const newTask = await response.json();
                    await fetchTasks();
                    setSelectedTask(newTask);
                    alert("Task created successfully");
                } else {
                    const error = await response.json();
                    alert(`Failed to create task: ${error.detail || response.statusText}`);
                }
            }
        } catch (error) {
            console.error("Error saving task:", error);
            alert("Failed to save task");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!selectedTask) return;
        
        if (!confirm(`Are you sure you want to delete task "${selectedTask.name}"?`)) {
            return;
        }

        try {
            const response = await fetch(
                `${API_URL}/api/task-catalog/tasks/${selectedTask.task_key}?soft_delete=true`,
                {
                    method: "DELETE",
                }
            );

            if (response.ok) {
                await fetchTasks();
                setSelectedTask(null);
                alert("Task deleted successfully");
            } else {
                alert("Failed to delete task");
            }
        } catch (error) {
            console.error("Error deleting task:", error);
            alert("Failed to delete task");
        }
    };

    const filteredTasks = tasks.filter((task) => {
        if (statusFilter !== "all" && task.status !== statusFilter) {
            return false;
        }
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            return (
                task.name.toLowerCase().includes(query) ||
                task.description?.toLowerCase().includes(query) ||
                task.task_key.toLowerCase().includes(query)
            );
        }
        return true;
    });

    return (
        <div className="h-full flex flex-col bg-[var(--bg-primary)]">
            {/* Header */}
            <div className="border-b border-[var(--border-subtle)] px-6 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/dashboard/admin"
                            className="p-2 hover:bg-[var(--bg-secondary)] rounded-[var(--radius-md)] transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5 text-[var(--text-secondary)]" />
                        </Link>
                    <div>
                            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Task Catalog</h1>
                            <p className="text-sm text-[var(--text-secondary)] mt-1">
                                Master reference system for all workflow tasks
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content - Two Panels */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel - Task List */}
                <div className="w-1/2 border-r border-[var(--border-subtle)] flex flex-col">
                    {/* Search and Filters */}
                    <div className="px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
                        <div className="flex items-center gap-2">
                            <div className="flex-1 relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[var(--text-muted)] w-4 h-4" />
                                <input
                                    type="text"
                                    placeholder="Search tasks..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                                    className="w-full pl-9 pr-3 py-2 text-sm border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                                />
                            </div>
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="px-3 py-2 text-sm border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                            >
                                <option value="all">All</option>
                                <option value="draft">Draft</option>
                                <option value="active">Active</option>
                                <option value="deprecated">Deprecated</option>
                            </select>
                            <button
                                onClick={handleCreateNew}
                                className="px-3 py-2 text-sm bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)] transition-colors flex items-center gap-2"
                            >
                                <Plus className="w-4 h-4" />
                                New
                            </button>
                        </div>
                    </div>

                    {/* Task List */}
                    <div className="flex-1 overflow-y-auto">
                        {loading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-[var(--text-secondary)]">Loading tasks...</div>
                            </div>
                        ) : filteredTasks.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-64 text-center p-4">
                                <CheckSquare className="w-12 h-12 text-[var(--text-muted)] mb-4" />
                                <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">No tasks found</h3>
                                <p className="text-sm text-[var(--text-secondary)]">
                                    {searchQuery
                                        ? "Try adjusting your search or filters"
                                        : "Click 'New' to create a task"}
                                </p>
                            </div>
                        ) : (
                            <div className="p-4 space-y-2">
                                {filteredTasks.map((task) => (
                                    <div
                                        key={task.task_key}
                                        className={`p-4 bg-[var(--bg-primary)] border rounded-[var(--radius-md)] transition-all ${
                                            selectedTask?.task_key === task.task_key
                                                ? "border-[var(--primary-blue)] bg-[var(--primary-blue-light)] shadow-md"
                                                : "border-[var(--border-subtle)] hover:border-[var(--primary-blue)] hover:shadow-sm"
                                        }`}
                                    >
                                        <div
                                            onClick={() => handleTaskClick(task)}
                                            className="cursor-pointer"
                                        >
                                            <div className="flex items-start justify-between mb-2">
                                                <h3 className="font-semibold text-[var(--text-primary)]">{task.name}</h3>
                                                <span
                                                    className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                                                        task.status === "active"
                                                            ? "bg-green-100 text-green-700"
                                                            : task.status === "draft"
                                                            ? "bg-yellow-100 text-yellow-700"
                                                            : "bg-[var(--bg-secondary)] text-gray-700"
                                                    }`}
                                                >
                                                    {task.status}
                                                </span>
                                            </div>
                                            <p className="text-sm text-[var(--text-secondary)] mb-2 line-clamp-2">
                                                {task.description || "No description"}
                                            </p>
                                            <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)]">
                                                <span className="font-mono">{task.task_key}</span>
                                                {task.classification?.domain && (
                                                    <span>• {task.classification.domain}</span>
                                                )}
                                                {task.classification?.category && (
                                                    <span>• {task.classification.category}</span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] flex items-center justify-end">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleClone(task);
                                                }}
                                                className="px-3 py-1.5 text-xs font-medium text-[var(--primary-blue)] bg-[var(--primary-blue-light)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-light)] transition-colors flex items-center gap-1.5"
                                                title="Clone this task"
                                            >
                                                <Copy className="w-3.5 h-3.5" />
                                                Clone
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Panel - Task Form */}
                <div className="w-1/2 flex flex-col bg-[var(--bg-secondary)]">
                    {selectedTask || (!selectedTask && formData.name) ? (
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="max-w-2xl mx-auto">
                                <div className="bg-[var(--bg-primary)] rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-6 space-y-6">
                                    {/* Header */}
                                    <div className="flex items-center justify-between pb-4 border-b border-[var(--border-subtle)]">
                                        <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                                            {selectedTask ? "Edit Task" : "New Task"}
                                        </h2>
                                        <div className="flex items-center gap-2">
                                            {selectedTask && (
                                                <button
                                                    onClick={handleDelete}
                                                    className="p-2 text-red-600 hover:bg-red-50 rounded-[var(--radius-md)] transition-colors"
                                                    title="Delete task"
                                                >
                                                    <Trash2 className="w-5 h-5" />
                                                </button>
                                            )}
                                            <button
                                                onClick={() => setSelectedTask(null)}
                                                className="p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] rounded-[var(--radius-md)] transition-colors"
                                            >
                                                <X className="w-5 h-5" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Basic Fields */}
                                    <div className="space-y-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Task Name *
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.name || ""}
                                                onChange={(e) =>
                                                    setFormData({ ...formData, name: e.target.value })
                                                }
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                                                placeholder="Enter task name"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Task Key
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.task_key || ""}
                                                onChange={(e) =>
                                                    setFormData({ ...formData, task_key: e.target.value })
                                                }
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent font-mono text-sm"
                                                placeholder="Auto-generated from name"
                                                disabled={!!selectedTask}
                                            />
                                            {selectedTask && (
                                                <p className="text-xs text-[var(--text-secondary)] mt-1">Task key cannot be changed</p>
                                            )}
                                        </div>

                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Description
                                            </label>
                                            <textarea
                                                value={formData.description || ""}
                                                onChange={(e) =>
                                                    setFormData({ ...formData, description: e.target.value })
                                                }
                                                rows={4}
                                                className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                                                placeholder="Enter task description"
                                            />
                                        </div>

                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Status
                                                </label>
                                                <select
                                                    value={formData.status || "draft"}
                                                    onChange={(e) =>
                                                        setFormData({ ...formData, status: e.target.value })
                                                    }
                                                    className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                                                >
                                                    <option value="draft">Draft</option>
                                                    <option value="active">Active</option>
                                                    <option value="deprecated">Deprecated</option>
                                                </select>
                                            </div>

                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Version
                                                </label>
                                                <input
                                                    type="number"
                                                    value={formData.version || 1}
                                                    onChange={(e) =>
                                                        setFormData({
                                                            ...formData,
                                                            version: parseInt(e.target.value) || 1,
                                                        })
                                                    }
                                                    className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                                                />
                                            </div>
                                        </div>

                                        {/* Schema-based Form Sections */}
                                        {schema && !schemaLoading ? (
                                            <>
                                                {/* Classification */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group" open>
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Classification</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="classification"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Automation */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Automation</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="automation"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Tool Binding */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Tool Binding Defaults</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="tool_binding_defaults"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Information */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Information</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="information"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Policy */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Policy & Permissions</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="policy"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Temporal */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Temporal</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="temporal"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Escalation */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Escalation</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="escalation"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Dependencies */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Dependencies</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="dependencies"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Failure */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Failure Handling</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="failure"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* UI */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>UI</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="ui"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Governance */}
                                                <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                    <details className="group">
                                                        <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                            <span>Governance</span>
                                                            <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                        </summary>
                                                        <div className="mt-3">
                                                            <TaskFormFields
                                                                sectionKey="governance"
                                                                schema={schema}
                                                                formData={formData}
                                                                onChange={handleFieldChange}
                                                                tasks={tasks}
                                                            />
                                                        </div>
                                                    </details>
                                                </div>

                                                {/* Contract - Keep as JSON editor for now (not in schema) */}
                                                {formData.contract !== undefined && (
                                                    <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                        <details className="group">
                                                            <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)] mb-3 list-none flex items-center justify-between">
                                                                <span>Contract</span>
                                                                <span className="text-[var(--text-muted)] group-open:rotate-90 transition-transform">›</span>
                                                            </summary>
                                                            <div className="mt-3">
                                                                <textarea
                                                                    value={JSON.stringify(formData.contract || {}, null, 2)}
                                                                    onChange={(e) => {
                                                                        try {
                                                                            const parsed = JSON.parse(e.target.value);
                                                                            setFormData({
                                                                                ...formData,
                                                                                contract: parsed,
                                                                            });
                                                                        } catch {
                                                                            // Invalid JSON, don't update
                                                                        }
                                                                    }}
                                                                    rows={6}
                                                                    className="w-full px-3 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent font-mono text-xs"
                                                                    placeholder="{}"
                                                                />
                                                            </div>
                                                        </details>
                                                    </div>
                                                )}
                                            </>
                                        ) : schemaLoading ? (
                                            <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                <p className="text-sm text-[var(--text-secondary)]">Loading schema...</p>
                                            </div>
                                        ) : (
                                            <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                <p className="text-sm text-red-500">Schema not available. Using fallback JSON editors.</p>
                                            </div>
                                        )}

                                        {/* Metadata (if editing existing task) */}
                                        {selectedTask && (
                                            <div className="pt-4 border-t border-[var(--border-subtle)]">
                                                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                                                    Metadata
                                                </h3>
                                                <div className="space-y-2 text-sm text-[var(--text-secondary)]">
                                                    {selectedTask.task_id && (
                                                        <div>
                                                            <span className="font-medium">Task ID:</span>{" "}
                                                            <span className="font-mono text-xs">
                                                                {selectedTask.task_id}
                                                            </span>
                                                        </div>
                                                    )}
                                                    {selectedTask.created_at_utc && (
                                                        <div>
                                                            <span className="font-medium">Created:</span>{" "}
                                                            {new Date(selectedTask.created_at_utc).toLocaleString()}
                                                        </div>
                                                    )}
                                                    {selectedTask.updated_at_utc && (
                                                        <div>
                                                            <span className="font-medium">Updated:</span>{" "}
                                                            {new Date(selectedTask.updated_at_utc).toLocaleString()}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="flex items-center justify-end gap-3 pt-4 border-t border-[var(--border-subtle)]">
                                        <button
                                            onClick={() => setSelectedTask(null)}
                                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-md)] hover:bg-[var(--bg-secondary)] transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleSave}
                                            disabled={saving || !formData.name}
                                            className="px-4 py-2 text-sm font-medium text-[var(--bg-primary)] bg-[var(--primary-blue)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                        >
                                            <Save className="w-4 h-4" />
                                            {saving ? "Saving..." : "Save"}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-center">
                                <CheckSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
                                    Select a task to edit
                                </h3>
                                <p className="text-sm text-[var(--text-secondary)] mb-4">
                                    Click on a task from the list or create a new one
                                </p>
                                <button
                                    onClick={handleCreateNew}
                                    className="px-4 py-2 bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)] transition-colors flex items-center gap-2 mx-auto"
                                >
                                    <Plus className="w-4 h-4" />
                                    Create New Task
                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
