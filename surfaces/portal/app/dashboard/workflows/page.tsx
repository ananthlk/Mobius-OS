"use client";

import { useState } from "react";
import ToolPalette from "@/components/workflows/ToolPalette";
import StepEditor from "@/components/workflows/StepEditor";
import ProblemEntry from "@/components/workflows/ProblemEntry";
import SolutionRail from "@/components/workflows/SolutionRail";

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
    const [searchQuery, setSearchQuery] = useState(""); // Add this back

    // Selection State
    const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(null);


    // Handlers
    const handleDiagnose = (results: any[], query: string) => { // Accept query
        setDiagnosticResults(results);
        setSearchQuery(query);
        setViewMode("SELECTION");
    };

    const handleSelectSolution = (sol: any) => {
        setSelectedSolutionId(sol.recipe_name);
    };

    const handleAdopt = () => {
        const sol = diagnosticResults.find(s => s.recipe_name === selectedSolutionId);
        if (!sol) return;

        setName(sol.name);
        setGoal(sol.description);
        setSteps(sol.steps.map(s => ({ ...s, args_mapping: s.args_mapping || {} })));
        setViewMode("EDITOR");
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
        alert("Workflow Saved! (Mock)");
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

            import ShapingChat from "@/components/workflows/ShapingChat";

// ... inside component ...

    // Handlers
    const handleDiagnose = (results: any[]) => {
                setDiagnosticResults(results);
            setViewMode("SELECTION"); // We reuse SELECTION mode name but it's now "SHAPING" view
    };

    const handleShapingUpdate = (newQuery: string) => {
        // Mock: Reshuffle or adjust scores based on "new insight"
        // In real backend, this would call /api/diagnose/refine
        const shuffled = [...diagnosticResults].map(r => ({
                ...r,
                match_score: Math.random() * 0.5 + 0.4 // Randomize score to show "Thinking"
        })).sort((a, b) => b.match_score - a.match_score);

            setDiagnosticResults(shuffled);
    };

            // ... render ...

            {/* VIEW: SELECTION (SHAPING SPLIT VIEW) */}
            {viewMode === "SELECTION" && (
                <div className="w-full h-full flex relative z-10 bg-[#F9FAFB] p-6 gap-6">
                    {/* Left Rail: Dynamic Solutions */}
                    <div className="w-[340px] flex-shrink-0 flex flex-col h-full bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                        <SolutionRail
                            solutions={diagnosticResults}
                            selectedId={selectedSolutionId}
                            onSelect={handleSelectSolution}
                        />
                        {/* Adopt Button at bottom of rail */}
                        <div className="p-4 border-t border-gray-100 bg-gray-50/50">
                            <button
                                onClick={handleAdopt}
                                disabled={!selectedSolutionId}
                                className="w-full bg-[#1A1A1A] text-white py-3 rounded-xl font-semibold hover:bg-black transition-colors shadow-lg shadow-black/5 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                            >
                                Adopt Selected Workflow
                            </button>
                        </div>
                    </div>

                    {/* Main Area: Shaping Chat */}
                    <div className="flex-1 h-full min-w-0">
                        {/* Using the original query as seed */}
                        <ShapingChat
                            initialQuery={searchQuery || "I have a problem..."}
                            onUpdate={handleShapingUpdate}
                        />
                    </div>
                </div>
            )}


            {/* VIEW: EDITOR */}
            {viewMode === "EDITOR" && (
                <div className="w-full h-full flex relative z-10">
                    <ToolPalette onSelectTool={handleAddStep} />

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
            )}
        </div>
    );
}
