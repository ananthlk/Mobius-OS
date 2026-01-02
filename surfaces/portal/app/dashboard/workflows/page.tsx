"use client";

import { useState, useEffect } from "react";
import ToolPalette from "@/components/workflows/ToolPalette";
import StepEditor from "@/components/workflows/StepEditor";
import ProblemEntry from "@/components/workflows/ProblemEntry";
import SolutionRail from "@/components/workflows/SolutionRail";
import ShapingChat from "@/components/workflows/ShapingChat";
import ProgressHeader, { ProgressState } from "@/components/ProgressHeader";
import { normalizeProgressState, fetchJourneyState } from "@/utils/progressHelpers";
import ProcessCards from "@/components/workflows/ProcessCards";

interface Step {
    id: string;
    tool_name: string;
    description: string;
    args_mapping: Record<string, string>;
}

// Mock Solutions Data
const MOCK_SOLUTIONS = [
    {
        id: "sol_1",
        name: "Medicaid ID Recovery v2.1",
        description: "Automated scan of state databases to recover missing Medicaid IDs for intake processing.",
        matchScore: 92,
        completionRate: 85,
        origin: "standard" as const,
        steps: [
            { id: "s1", tool_name: "schedule_scanner", description: "Find appointment", args_mapping: {} },
            { id: "s2", tool_name: "risk_calculator", description: "Assess gaps", args_mapping: { "patient_id": "step_1" } }
        ]
    },
    {
        id: "sol_2",
        name: "Intake Gap Analysis",
        description: "AI-synthesized workflow to identify missing documentation before patient arrival.",
        matchScore: 78,
        completionRate: 60,
        origin: "ai" as const,
        steps: [
            { id: "s1", tool_name: "schedule_scanner", description: "Scan schedule", args_mapping: {} }
        ]
    }
];

export default function WorkflowBuilder() {
    type ViewMode = "ENTRY" | "SELECTION" | "EDITOR";

    const [viewMode, setViewMode] = useState<ViewMode>("ENTRY");
    const [diagnosticResults, setDiagnosticResults] = useState<any[]>([]);

    // Editor State
    const [name, setName] = useState("");
    const [goal, setGoal] = useState("");
    const [steps, setSteps] = useState<Step[]>([]);
    const [selectedSchemaMap, setSelectedSchemaMap] = useState<Record<string, any>>({});
    const [searchQuery, setSearchQuery] = useState("");
    const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
    const [isToolPaletteCollapsed, setIsToolPaletteCollapsed] = useState(false);
    const [isInitializing, setIsInitializing] = useState(false); // Track if we're waiting for initial API response

    // Selection State
    const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(null);


    // Draft State
    const [draftPlan, setDraftPlan] = useState<any | null>(null);

    // Progress State
    const [progressState, setProgressState] = useState<ProgressState>({});

    // Planning Phase State (simplified - just for highlighting)
    const [highlightedSteps, setHighlightedSteps] = useState<any[]>([]);
    
    // Poll for journey state updates when session is active
    useEffect(() => {
        if (!currentSessionId) return;
        
        const interval = setInterval(async () => {
            try {
                const journeyState = await fetchJourneyState(currentSessionId);
                if (journeyState) {
                    setProgressState(journeyState);
                }
            } catch (error) {
                // Silently fail - journey state might not exist yet
                console.debug("Journey state not available yet");
            }
        }, 2000); // Poll every 2 seconds
        
        return () => clearInterval(interval);
    }, [currentSessionId]);

    // Handlers
    const handleDiagnose = async (results: any[], query: string, sessionId?: number) => {
        setDiagnosticResults(results);
        setSearchQuery(query);
        if (sessionId) {
            setCurrentSessionId(sessionId);
            setIsInitializing(false); // We have a session, initialization complete
            
            // Fetch initial session state to populate progress
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}`);
                const sessionData = await res.json();
                await handleSessionUpdate(sessionData);
            } catch (e) {
                console.error("Failed to fetch initial session state", e);
            }
        } else {
            setIsInitializing(results.length === 0); // Still initializing if no results and no session
        }
        setViewMode("SELECTION"); // Navigate immediately - don't wait for API response
    };

    const handleShapingUpdate = async (newQuery: string) => {
        // 1. If we have a session, fetch the latest draft plan and journey state
        if (currentSessionId) {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const [sessionRes, journeyRes] = await Promise.all([
                    fetch(`${apiUrl}/api/workflows/shaping/${currentSessionId}`),
                    fetch(`${apiUrl}/api/workflows/shaping/${currentSessionId}/journey-state`).catch(() => null)
                ]);
                
                const sessionData = await sessionRes.json();

                // Check if draft_plan exists and has meaningful content (gates, phases, or steps)
                if (sessionData.draft_plan) {
                    const hasGates = sessionData.draft_plan.gates && sessionData.draft_plan.gates.length > 0;
                    const hasPhases = sessionData.draft_plan.phases && sessionData.draft_plan.phases.length > 0;
                    const hasSteps = sessionData.draft_plan.steps && sessionData.draft_plan.steps.length > 0;
                    const hasOtherKeys = Object.keys(sessionData.draft_plan).length > 0;
                    if (hasGates || hasPhases || hasSteps || hasOtherKeys) {
                        setDraftPlan(sessionData.draft_plan);
                    }
                }
                
                // Update journey state if available
                if (journeyRes && journeyRes.ok) {
                    const journeyData = await journeyRes.json();
                    setProgressState({
                        domain: journeyData.domain,
                        strategy: journeyData.strategy,
                        currentStep: journeyData.current_step,
                        percentComplete: journeyData.percent_complete ?? 0,
                        status: journeyData.status
                    });
                } else {
                    // Fallback to session data
                    const progress = normalizeProgressState(sessionData, searchQuery);
                    setProgressState(progress);
                }
            } catch (e) {
                console.error("Failed to fetch draft", e);
            }
        }

        // 2. Keep the existing match logic for the "Searching" phase
        const shuffled = [...diagnosticResults].map(r => ({
            ...r,
            match_score: Math.random() * 0.5 + 0.4
        })).sort((a, b) => b.match_score - a.match_score);
        setDiagnosticResults(shuffled);
    };

    const handleSelectSolution = (sol: any) => {
        setSelectedSolutionId(sol.recipe_name);
    };

    const updateDraftPlan = async (updates: any) => {
        if (!currentSessionId) return;
        
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/workflows/shaping/${currentSessionId}/draft-plan`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(updates),
            });

            if (!response.ok) {
                throw new Error("Failed to update draft plan");
            }

            const updatedPlan = await response.json();
            setDraftPlan(updatedPlan);
        } catch (error) {
            console.error("Failed to update draft plan:", error);
            alert("Failed to update draft plan. Please try again.");
        }
    };

    const handleStepUpdate = async (stepId: string, updatedStep: any) => {
        if (!draftPlan || !draftPlan.steps) return;

        const updatedSteps = draftPlan.steps.map((s: any) => 
            s.id === stepId ? updatedStep : s
        );

        await updateDraftPlan({ steps: updatedSteps });
    };

    const handleStepDelete = async (stepId: string) => {
        if (!draftPlan || !draftPlan.steps) return;

        const updatedSteps = draftPlan.steps.filter((s: any) => s.id !== stepId);
        await updateDraftPlan({ steps: updatedSteps });
    };

    const handleStepReorder = async (newOrder: any[]) => {
        await updateDraftPlan({ steps: newOrder });
    };

    const handleStepCreate = async (newStep: any) => {
        if (!draftPlan) return;

        const updatedSteps = [...(draftPlan.steps || []), newStep];
        await updateDraftPlan({ steps: updatedSteps });
    };

    const handleAdopt = async () => {
        const sol = diagnosticResults.find(s => s.recipe_name === selectedSolutionId);
        if (!sol) return;

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            
            // Fetch full recipe details and tool schemas in parallel
            const [recipeRes, toolsRes] = await Promise.all([
                fetch(`${apiUrl}/api/workflows/${sol.recipe_name}`),
                fetch(`${apiUrl}/api/workflows/tools`)
            ]);
            
            const recipe = await recipeRes.json();
            const tools = await toolsRes.json();
            
            // Create a map of tool schemas for quick lookup
            const toolsMap: Record<string, any> = {};
            tools.forEach((tool: any) => {
                toolsMap[tool.name] = tool;
            });

            if (recipe && recipe.steps) {
                // Convert recipe steps to editor format
                const stepsArray: Step[] = [];
                const schemaMap: Record<string, any> = {};

                // Build steps in order (follow transition chain)
                const visited = new Set<string>();
                let currentStepId = recipe.start_step_id || Object.keys(recipe.steps)[0];
                
                while (currentStepId && !visited.has(currentStepId)) {
                    visited.add(currentStepId);
                    const step = recipe.steps[currentStepId];
                    if (step) {
                        stepsArray.push({
                            id: step.step_id || currentStepId,
                            tool_name: step.tool_name,
                            description: step.description || "",
                            args_mapping: step.args_mapping || {}
                        });
                        // Use actual tool schema if available, otherwise create placeholder
                        schemaMap[step.tool_name] = toolsMap[step.tool_name] || {
                            name: step.tool_name,
                            description: step.description || "",
                            parameters: {}
                        };
                        currentStepId = step.transition_success || null;
                    } else {
                        break;
                    }
                }

                // If transition chain approach didn't work, fallback to all steps
                if (stepsArray.length === 0 && recipe.steps) {
                    Object.entries(recipe.steps).forEach(([stepId, step]: [string, any]) => {
                        stepsArray.push({
                            id: step.step_id || stepId,
                            tool_name: step.tool_name,
                            description: step.description || "",
                            args_mapping: step.args_mapping || {}
                        });
                        schemaMap[step.tool_name] = toolsMap[step.tool_name] || {
                            name: step.tool_name,
                            description: step.description || "",
                            parameters: {}
                        };
                    });
                }

                setName(recipe.name || sol.recipe_name);
                setGoal(recipe.goal || sol.goal);
                setSteps(stepsArray);
                setSelectedSchemaMap(schemaMap);
                setViewMode("EDITOR");
            } else {
                // Fallback if recipe structure is different
                setName(sol.recipe_name);
                setGoal(sol.goal);
                setSteps([]);
                setViewMode("EDITOR");
            }
        } catch (error) {
            console.error("Failed to load recipe", error);
            alert("Failed to load workflow details. Please try again.");
        }
    };

    // --- EDITOR HANDLERS (Reused) ---
    const handleAddStep = (tool: any) => {
        const newStepId = `step_${steps.length + 1}`;
        const newStep: Step = {
            id: newStepId,
            tool_name: tool.name,
            description: "",
            args_mapping: {}
        };
        setSteps([...steps, newStep]);
        setSelectedSchemaMap({ ...selectedSchemaMap, [tool.name]: tool });
    };

    const handleUpdateStep = (index: number, updated: Step) => {
        const newSteps = [...steps];
        newSteps[index] = updated;
        setSteps(newSteps);
    };

    const handleDeleteStep = (index: number) => {
        const newSteps = [...steps];
        newSteps.splice(index, 1);
        setSteps(newSteps);
    };

    const handleSave = async () => {
        if (!name || steps.length === 0) {
            alert("Please provide a name and at least one step.");
            return;
        }
        
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            
            // Convert steps array to the format expected by the backend
            const stepsDict: Record<string, any> = {};
            steps.forEach((step, idx) => {
                stepsDict[step.id] = {
                    tool_name: step.tool_name,
                    description: step.description,
                    args_mapping: step.args_mapping
                };
            });
            
            const response = await fetch(`${apiUrl}/api/workflows/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    goal: goal || name,
                    steps: stepsDict,
                    start_step_id: steps.length > 0 ? steps[0].id : ""
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Failed to save workflow");
            }
            
            const result = await response.json();
            alert(`Workflow "${name}" saved successfully!`);
            
            // Optionally reset form or navigate
            // setViewMode("ENTRY");
        } catch (error: any) {
            console.error("Save failed", error);
            alert(`Failed to save workflow: ${error.message}`);
        }
    };


    const handleSessionUpdate = async (data: any) => {
        // Check if draft_plan exists and has meaningful content (gates, phases, or steps)
        if (data.draft_plan) {
            const hasGates = data.draft_plan.gates && data.draft_plan.gates.length > 0;
            const hasPhases = data.draft_plan.phases && data.draft_plan.phases.length > 0;
            const hasSteps = data.draft_plan.steps && data.draft_plan.steps.length > 0;
            const hasOtherKeys = Object.keys(data.draft_plan).length > 0;
            if (hasGates || hasPhases || hasSteps || hasOtherKeys) {
                console.log("[WORKFLOW_BUILDER] Setting draft plan:", { 
                    hasGates,
                    hasPhases, 
                    hasSteps, 
                    gatesCount: data.draft_plan.gates?.length || 0,
                    phasesCount: data.draft_plan.phases?.length || 0,
                    stepsCount: data.draft_plan.steps?.length || 0,
                    keys: Object.keys(data.draft_plan)
                });
                setDraftPlan(data.draft_plan);
            } else {
                console.log("[WORKFLOW_BUILDER] Draft plan exists but is empty:", data.draft_plan);
            }
        } else {
            console.log("[WORKFLOW_BUILDER] No draft_plan in session data");
        }
        
        // Try to fetch journey state directly (more efficient)
        if (currentSessionId) {
            const journeyState = await fetchJourneyState(currentSessionId);
            if (journeyState) {
                setProgressState(journeyState);
                return; // Use journey state if available
            }
        }
        
        // Fallback: Extract and normalize progress state from session data
        const progress = normalizeProgressState(data, searchQuery);
        setProgressState(progress);
    };


    // Convert draft plan to phases format for ProcessCards
    // Handles both "gates" (new structure) and "phases" (legacy structure)
    const getPhasesFromDraft = () => {
        if (!draftPlan) {
            console.log("[WORKFLOW_BUILDER] getPhasesFromDraft: No draftPlan");
            return [];
        }
        
        console.log("[WORKFLOW_BUILDER] getPhasesFromDraft: draftPlan structure:", {
            hasGates: !!draftPlan.gates,
            gatesLength: draftPlan.gates?.length || 0,
            hasPhases: !!draftPlan.phases,
            phasesLength: draftPlan.phases?.length || 0,
            hasSteps: !!draftPlan.steps,
            stepsLength: draftPlan.steps?.length || 0,
            keys: Object.keys(draftPlan)
        });
        
        // NEW STRUCTURE: Convert gates to phases format
        // Gates are essentially phases with additional metadata (gate_key, gate_question, gate_value, etc.)
        const gates = draftPlan.gates || [];
        if (gates.length > 0) {
            console.log("[WORKFLOW_BUILDER] Converting gates to phases format:", gates.length);
            // Convert each gate to a phase structure
            return gates.map((gate: any) => ({
                id: gate.id || `gate_${gate.gate_key}`,
                name: gate.name || gate.gate_question || "Gate",
                description: gate.description || gate.gate_question || "",
                steps: gate.steps || [],
                // Preserve gate-specific metadata for potential future use
                gate_key: gate.gate_key,
                gate_question: gate.gate_question,
                gate_value: gate.gate_value,
                gate_data: gate.gate_data
            }));
        }
        
        // LEGACY STRUCTURE: Use phases directly
        const phases = draftPlan.phases || [];
        if (phases.length > 0) {
            console.log("[WORKFLOW_BUILDER] Returning phases:", phases.length);
            return phases;
        }
        
        // FALLBACK: convert flat steps to phase structure
        const steps = draftPlan.steps || [];
        if (steps.length > 0) {
            console.log("[WORKFLOW_BUILDER] Converting steps to phase structure:", steps.length);
            return [{
                id: "phase_1",
                name: "Workflow Steps",
                description: "",
                steps: steps
            }];
        }
        
        console.log("[WORKFLOW_BUILDER] No gates, phases, or steps found, returning empty array");
        return [];
    };

    // --- RENDER ---
    return (
        <div className="flex h-screen bg-[#F9FAFB] text-[#1A1A1A] overflow-hidden font-sans selection:bg-blue-100">
            {/* VIEW: ENTRY */}
            {viewMode === "ENTRY" && (
                <div className="w-full h-full relative z-10">
                    <ProblemEntry onDiagnose={handleDiagnose} />
                </div>
            )}



            {/* VIEW: SELECTION (2 COLUMN LAYOUT) */}
            {viewMode === "SELECTION" && (
                <div className="w-full h-full flex flex-col relative z-10 bg-[#F9FAFB]">
                    {/* Progress Header */}
                    <ProgressHeader progress={progressState} />
                    
                    <div className="flex-1 flex p-6 gap-6 min-h-0">
                        {/* Loading overlay - only show if we're waiting for initial API response */}
                        {isInitializing && diagnosticResults.length === 0 && (
                            <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm z-50 rounded-2xl">
                                <div className="text-center">
                                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                                    <p className="text-sm text-gray-600 font-medium">Initializing workflow builder...</p>
                                    <p className="text-xs text-gray-400 mt-1">Analyzing your request</p>
                                </div>
                            </div>
                        )}
                        
                        {/* Left Rail: Process Cards */}
                        <div className="w-1/3 border-r border-gray-300 bg-white rounded-2xl shadow-md overflow-hidden">
                            <ProcessCards
                                phases={getPhasesFromDraft()}
                                highlightedSteps={highlightedSteps}
                                onStepClick={(stepId, phaseId) => {
                                    // Handle step click if needed
                                }}
                            />
                        </div>

                        {/* Right Side: Chat Window */}
                        <div className="flex-1 h-full min-w-0">
                            <ShapingChat
                                initialQuery={searchQuery || "I have a problem..."}
                                onUpdate={handleShapingUpdate}
                                onSessionUpdate={handleSessionUpdate}
                                sessionId={currentSessionId}
                                progressState={progressState}
                            />
                        </div>
                    </div>
                </div>
            )}


            {/* VIEW: EDITOR */}
            {viewMode === "EDITOR" && (
                <div className="w-full h-full flex flex-col relative z-10">
                    {/* Progress Header */}
                    <ProgressHeader progress={progressState} />
                    
                    <div className="flex-1 flex min-h-0">
                        <ToolPalette 
                            onSelectTool={handleAddStep}
                            collapsed={isToolPaletteCollapsed}
                            onToggleCollapse={() => setIsToolPaletteCollapsed(!isToolPaletteCollapsed)}
                        />

                        <div className="flex-1 flex flex-col h-full relative z-10 bg-[#F9FAFB]">
                            {/* Header */}
                            <div className="h-20 border-b border-[#E5E7EB] flex items-center justify-between px-8 bg-white/80 backdrop-blur-xl z-20 sticky top-0">
                            <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-3">
                                    <input
                                        type="text"
                                        placeholder="Untitled Workflow"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        className="bg-transparent text-xl font-semibold focus:outline-none placeholder-gray-300 w-80 text-[#1A1A1A] tracking-tight"
                                    />
                                    <div className="px-2 py-0.5 rounded-full bg-blue-50 border border-blue-100 text-[10px] text-blue-600 uppercase tracking-widest font-bold">
                                        Draft
                                    </div>
                                </div>
                                <input
                                    type="text"
                                    placeholder="Describe the goal..."
                                    value={goal}
                                    onChange={(e) => setGoal(e.target.value)}
                                    className="bg-transparent text-sm focus:outline-none placeholder-gray-300 w-96 text-[#6B7280] font-normal"
                                />
                            </div>

                            <button
                                onClick={handleSave}
                                className="bg-[#1A1A1A] text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-black transition-colors shadow-md shadow-black/5"
                            >
                                Publish Workflow
                            </button>
                        </div>

                        {/* Editor Canvas */}
                        <div className="flex-1 overflow-y-auto p-12 custom-scrollbar bg-[#F9FAFB]">
                            {/* Dotted Grid */}
                            <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.4] pointer-events-none mix-blend-multiply"></div>

                            <div className="max-w-4xl mx-auto pb-20 relative z-10">
                                <div className="relative">
                                    {/* Connector Line */}
                                    <div className="absolute left-8 top-8 bottom-8 w-0.5 bg-[#E5E7EB] -z-10"></div>
                                    <div className="space-y-6">
                                        {steps.map((step, idx) => (
                                            <div key={step.id} className="relative pl-4 animate-in slide-in-from-bottom-4 fade-in">
                                                {/* Connector Elbow */}
                                                {idx > 0 && <div className="absolute left-[33px] -top-6 bottom-1/2 w-0.5 bg-[#E5E7EB] -z-10"></div>}
                                                <StepEditor
                                                    step={step}
                                                    index={idx}
                                                    allSteps={steps}
                                                    toolSchema={selectedSchemaMap[step.tool_name] || { name: step.tool_name, description: "Loaded step", parameters: {} }}
                                                    onChange={(updated) => handleUpdateStep(idx, updated)}
                                                    onDelete={() => handleDeleteStep(idx)}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
