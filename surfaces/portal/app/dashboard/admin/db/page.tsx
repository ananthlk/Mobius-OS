"use client";

import React, { useState, useEffect } from "react";
import { Database, Table as TableIcon, Search, Play, ChevronDown, ChevronRight, AlertCircle } from "lucide-react";

interface TableInfo {
    name: string;
    schema: string;
    type: string;
}

interface ColumnInfo {
    name: string;
    type: string;
    nullable: boolean;
    default: string | null;
}

interface QueryResult {
    columns: string[];
    rows: Record<string, any>[];
    row_count: number;
}

interface SessionSearchResult {
    tables: Array<{
        table_name: string;
        row_count: number;
        rows: Record<string, any>[];
    }>;
}

export default function DatabaseExplorerPage() {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Table Browser State
    const [tables, setTables] = useState<TableInfo[]>([]);
    const [selectedTable, setSelectedTable] = useState<string | null>(null);
    const [tableSchema, setTableSchema] = useState<ColumnInfo[]>([]);
    const [tableData, setTableData] = useState<QueryResult | null>(null);
    const [tablesLoading, setTablesLoading] = useState(true);
    const [schemaLoading, setSchemaLoading] = useState(false);
    const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

    // Query Editor State
    const [query, setQuery] = useState("");
    const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
    const [queryLoading, setQueryLoading] = useState(false);
    const [queryError, setQueryError] = useState<string | null>(null);

    // Session Search State
    const [sessionId, setSessionId] = useState("");
    const [sessionResults, setSessionResults] = useState<SessionSearchResult | null>(null);
    const [sessionLoading, setSessionLoading] = useState(false);
    const [sessionError, setSessionError] = useState<string | null>(null);
    const [expandedSessionTables, setExpandedSessionTables] = useState<Set<string>>(new Set());

    // Fetch all tables
    useEffect(() => {
        fetchTables();
    }, []);

    const fetchTables = async () => {
        setTablesLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/admin/db/tables`);
            if (res.ok) {
                const data = await res.json();
                setTables(data);
            } else {
                console.error("Failed to fetch tables");
            }
        } catch (e) {
            console.error("Error fetching tables", e);
        } finally {
            setTablesLoading(false);
        }
    };

    const fetchTableSchema = async (tableName: string) => {
        setSchemaLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/admin/db/tables/${tableName}/schema`);
            if (res.ok) {
                const data = await res.json();
                setTableSchema(data);
            } else {
                console.error("Failed to fetch table schema");
            }
        } catch (e) {
            console.error("Error fetching table schema", e);
        } finally {
            setSchemaLoading(false);
        }
    };

    const fetchTableData = async (tableName: string) => {
        setSchemaLoading(true);
        try {
            const query = `SELECT * FROM "${tableName}" LIMIT 100`;
            const res = await fetch(`${API_URL}/api/admin/db/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, parameters: {} }),
            });
            if (res.ok) {
                const data = await res.json();
                setTableData(data);
            } else {
                const error = await res.json();
                console.error("Failed to fetch table data", error);
            }
        } catch (e) {
            console.error("Error fetching table data", e);
        } finally {
            setSchemaLoading(false);
        }
    };

    const handleTableClick = async (tableName: string) => {
        if (expandedTables.has(tableName)) {
            const newExpanded = new Set(expandedTables);
            newExpanded.delete(tableName);
            setExpandedTables(newExpanded);
            setSelectedTable(null);
            setTableSchema([]);
            setTableData(null);
        } else {
            setSelectedTable(tableName);
            const newExpanded = new Set(expandedTables);
            newExpanded.add(tableName);
            setExpandedTables(newExpanded);
            await fetchTableSchema(tableName);
        }
    };

    const handleViewTableData = async (tableName: string) => {
        await fetchTableData(tableName);
    };

    const executeQuery = async () => {
        if (!query.trim()) {
            setQueryError("Please enter a query");
            return;
        }

        setQueryLoading(true);
        setQueryError(null);
        try {
            const res = await fetch(`${API_URL}/api/admin/db/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, parameters: {} }),
            });

            if (res.ok) {
                const data = await res.json();
                setQueryResult(data);
            } else {
                const error = await res.json();
                setQueryError(error.detail || "Query execution failed");
            }
        } catch (e) {
            setQueryError("Failed to execute query: " + (e instanceof Error ? e.message : String(e)));
        } finally {
            setQueryLoading(false);
        }
    };

    const searchSession = async () => {
        if (!sessionId.trim()) {
            setSessionError("Please enter a session ID");
            return;
        }

        const sessionIdNum = parseInt(sessionId, 10);
        if (isNaN(sessionIdNum)) {
            setSessionError("Session ID must be a number");
            return;
        }

        setSessionLoading(true);
        setSessionError(null);
        try {
            const res = await fetch(`${API_URL}/api/admin/db/session/${sessionIdNum}`);
            if (res.ok) {
                const data = await res.json();
                setSessionResults(data);
            } else {
                const error = await res.json();
                setSessionError(error.detail || "Session search failed");
            }
        } catch (e) {
            setSessionError("Failed to search session: " + (e instanceof Error ? e.message : String(e)));
        } finally {
            setSessionLoading(false);
        }
    };

    const toggleSessionTable = (tableName: string) => {
        const newExpanded = new Set(expandedSessionTables);
        if (newExpanded.has(tableName)) {
            newExpanded.delete(tableName);
        } else {
            newExpanded.add(tableName);
        }
        setExpandedSessionTables(newExpanded);
    };

    const renderTableData = (result: QueryResult) => {
        if (!result || result.rows.length === 0) {
            return <div className="text-[var(--text-secondary)] p-4">No data found</div>;
        }

        return (
            <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                    <thead>
                        <tr className="bg-[var(--bg-secondary)] border-b border-[var(--border-subtle)]">
                            {result.columns.map((col) => (
                                <th
                                    key={col}
                                    className="px-4 py-2 text-left text-sm font-semibold text-[var(--text-primary)]"
                                >
                                    {col}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {result.rows.map((row, idx) => (
                            <tr
                                key={idx}
                                className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-secondary)]"
                            >
                                {result.columns.map((col) => (
                                    <td
                                        key={col}
                                        className="px-4 py-2 text-sm text-[var(--text-secondary)]"
                                    >
                                        {row[col] === null ? (
                                            <span className="text-[var(--text-muted)] italic">null</span>
                                        ) : typeof row[col] === "object" ? (
                                            <pre className="text-xs overflow-auto max-w-xs">
                                                {JSON.stringify(row[col], null, 2)}
                                            </pre>
                                        ) : (
                                            String(row[col])
                                        )}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
                <div className="p-4 text-sm text-[var(--text-secondary)]">
                    Showing {result.row_count} row{result.row_count !== 1 ? "s" : ""}
                </div>
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col p-8 gap-6 overflow-y-auto">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <Database className="w-8 h-8 text-[var(--primary-blue)]" />
                    <h1 className="text-3xl font-bold text-[var(--text-primary)]">Database Explorer</h1>
                </div>
                <p className="text-[var(--text-secondary)]">
                    Browse tables, execute SELECT queries, and search by session ID
                </p>
            </div>

            {/* Table Browser Section */}
            <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] p-6">
                <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                    <TableIcon className="w-5 h-5" />
                    Table Browser
                </h2>
                {tablesLoading ? (
                    <div className="text-[var(--text-secondary)]">Loading tables...</div>
                ) : (
                    <div className="space-y-2">
                        {tables.map((table) => (
                            <div key={`${table.schema}.${table.name}`} className="border border-[var(--border-subtle)] rounded-[var(--radius-md)]">
                                <button
                                    onClick={() => handleTableClick(table.name)}
                                    className="w-full p-3 flex items-center justify-between hover:bg-[var(--bg-secondary)] transition-colors"
                                >
                                    <div className="flex items-center gap-2">
                                        {expandedTables.has(table.name) ? (
                                            <ChevronDown className="w-4 h-4" />
                                        ) : (
                                            <ChevronRight className="w-4 h-4" />
                                        )}
                                        <span className="font-medium text-[var(--text-primary)]">
                                            {table.schema}.{table.name}
                                        </span>
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-muted)]">
                                            {table.type}
                                        </span>
                                    </div>
                                </button>
                                {expandedTables.has(table.name) && (
                                    <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
                                        {schemaLoading ? (
                                            <div className="text-[var(--text-secondary)]">Loading schema...</div>
                                        ) : (
                                            <>
                                                <div className="mb-4">
                                                    <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">
                                                        Schema
                                                    </h3>
                                                    <div className="overflow-x-auto">
                                                        <table className="w-full text-sm">
                                                            <thead>
                                                                <tr className="border-b border-[var(--border-subtle)]">
                                                                    <th className="text-left p-2">Column</th>
                                                                    <th className="text-left p-2">Type</th>
                                                                    <th className="text-left p-2">Nullable</th>
                                                                    <th className="text-left p-2">Default</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {tableSchema.map((col) => (
                                                                    <tr key={col.name} className="border-b border-[var(--border-subtle)]">
                                                                        <td className="p-2 font-medium">{col.name}</td>
                                                                        <td className="p-2 text-[var(--text-secondary)]">{col.type}</td>
                                                                        <td className="p-2 text-[var(--text-secondary)]">
                                                                            {col.nullable ? "Yes" : "No"}
                                                                        </td>
                                                                        <td className="p-2 text-[var(--text-muted)] font-mono text-xs">
                                                                            {col.default || "—"}
                                                                        </td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleViewTableData(table.name)}
                                                    className="px-4 py-2 bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)] transition-colors text-sm"
                                                >
                                                    View Data (LIMIT 100)
                                                </button>
                                                {tableData && selectedTable === table.name && (
                                                    <div className="mt-4">
                                                        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">
                                                            Data
                                                        </h3>
                                                        {renderTableData(tableData)}
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Query Editor Section */}
            <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] p-6">
                <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                    <Play className="w-5 h-5" />
                    Query Editor
                </h2>
                <div className="space-y-4">
                    <div>
                        <textarea
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="SELECT * FROM table_name LIMIT 10;"
                            className="w-full h-32 p-4 border border-[var(--border-subtle)] rounded-[var(--radius-md)] font-mono text-sm focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent resize-none"
                        />
                        <p className="text-xs text-[var(--text-muted)] mt-2">
                            Only SELECT queries are allowed. DML/DDL keywords are not permitted.
                        </p>
                    </div>
                    <button
                        onClick={executeQuery}
                        disabled={queryLoading}
                        className="px-4 py-2 bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        <Play className="w-4 h-4" />
                        {queryLoading ? "Executing..." : "Execute Query"}
                    </button>
                    {queryError && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-[var(--radius-md)] flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                            <div>
                                <div className="font-semibold text-red-800 dark:text-red-400">Error</div>
                                <div className="text-sm text-red-700 dark:text-red-300">{queryError}</div>
                            </div>
                        </div>
                    )}
                    {queryResult && !queryError && (
                        <div>
                            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">
                                Results
                            </h3>
                            {renderTableData(queryResult)}
                        </div>
                    )}
                </div>
            </div>

            {/* Session Search Section */}
            <div className="bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] p-6">
                <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                    <Search className="w-5 h-5" />
                    Session ID Search
                </h2>
                <div className="space-y-4">
                    <div className="flex gap-4">
                        <input
                            type="number"
                            value={sessionId}
                            onChange={(e) => setSessionId(e.target.value)}
                            placeholder="Enter session ID"
                            className="flex-1 px-4 py-2 border border-[var(--border-subtle)] rounded-[var(--radius-md)] focus:ring-2 focus:ring-[var(--primary-blue)] focus:border-transparent"
                        />
                        <button
                            onClick={searchSession}
                            disabled={sessionLoading}
                            className="px-4 py-2 bg-[var(--primary-blue)] text-[var(--bg-primary)] rounded-[var(--radius-md)] hover:bg-[var(--primary-blue-dark)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            <Search className="w-4 h-4" />
                            {sessionLoading ? "Searching..." : "Search"}
                        </button>
                    </div>
                    {sessionError && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-[var(--radius-md)] flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                            <div>
                                <div className="font-semibold text-red-800 dark:text-red-400">Error</div>
                                <div className="text-sm text-red-700 dark:text-red-300">{sessionError}</div>
                            </div>
                        </div>
                    )}
                    {sessionResults && !sessionError && (
                        <div>
                            {sessionResults.tables.length === 0 ? (
                                <div className="text-[var(--text-secondary)] p-4">
                                    No entries found for session ID {sessionId}
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {sessionResults.tables.map((table) => (
                                        <div
                                            key={table.table_name}
                                            className="border border-[var(--border-subtle)] rounded-[var(--radius-md)]"
                                        >
                                            <button
                                                onClick={() => toggleSessionTable(table.table_name)}
                                                className="w-full p-3 flex items-center justify-between hover:bg-[var(--bg-secondary)] transition-colors"
                                            >
                                                <div className="flex items-center gap-2">
                                                    {expandedSessionTables.has(table.table_name) ? (
                                                        <ChevronDown className="w-4 h-4" />
                                                    ) : (
                                                        <ChevronRight className="w-4 h-4" />
                                                    )}
                                                    <span className="font-medium text-[var(--text-primary)]">
                                                        {table.table_name}
                                                    </span>
                                                    <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-muted)]">
                                                        {table.row_count} row{table.row_count !== 1 ? "s" : ""}
                                                    </span>
                                                </div>
                                            </button>
                                            {expandedSessionTables.has(table.table_name) && (
                                                <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
                                                    {renderTableData({
                                                        columns: table.rows.length > 0 ? Object.keys(table.rows[0]) : [],
                                                        rows: table.rows,
                                                        row_count: table.row_count,
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}



