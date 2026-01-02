import { ProgressState } from "@/components/ProgressHeader";

export function calculateProgressFromDraft(draftPlan: any, status?: string): number {
    if (!draftPlan?.steps || draftPlan.steps.length === 0) {
        const statusProgress: Record<string, number> = {
            'GATHERING': 10,
            'PLANNING': 30,
            'APPROVED': 60,
            'EXECUTING': 80,
            'COMPLETED': 100
        };
        return statusProgress[status || ''] || 0;
    }
    
    const completedSteps = draftPlan.steps.filter((step: any) => step.completed).length;
    const totalSteps = draftPlan.steps.length;
    return Math.round((completedSteps / totalSteps) * 100);
}

export function getCurrentStepFromDraft(draftPlan: any): string | undefined {
    if (!draftPlan?.steps || draftPlan.steps.length === 0) return undefined;
    
    const incompleteStep = draftPlan.steps.find((step: any) => !step.completed);
    if (incompleteStep) {
        return incompleteStep.description || incompleteStep.tool_hint || `Step ${incompleteStep.id}`;
    }
    
    return draftPlan.steps[draftPlan.steps.length - 1]?.description;
}

export function extractDomainFromQuery(query: string): string {
    const queryLower = query.toLowerCase();
    if (queryLower.includes('medicaid')) return 'Medicaid';
    if (queryLower.includes('intake')) return 'Intake';
    if (queryLower.includes('billing')) return 'Billing';
    if (queryLower.includes('eligibility')) return 'Eligibility';
    if (queryLower.includes('appointment')) return 'Appointments';
    if (queryLower.includes('patient')) return 'Patient Management';
    return 'General';
}

export function normalizeProgressState(sessionData: any, query?: string): ProgressState {
    // Priority: journey_state table > session fields > fallback
    const journeyState = sessionData.journey_state;
    
    return {
        domain: journeyState?.domain || sessionData.domain || (query ? extractDomainFromQuery(query) : undefined),
        strategy: journeyState?.strategy || sessionData.consultant_strategy,
        currentStep: journeyState?.current_step || sessionData.current_step || getCurrentStepFromDraft(sessionData.draft_plan),
        percentComplete: journeyState?.percent_complete ?? sessionData.percent_complete ?? calculateProgressFromDraft(sessionData.draft_plan, sessionData.status),
        status: journeyState?.status || sessionData.status
    };
}

// New function: Fetch journey state directly from dedicated endpoint
export async function fetchJourneyState(sessionId: number): Promise<ProgressState | null> {
    try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}/journey-state`);
        
        if (!res.ok) {
            if (res.status === 404) {
                return null; // No journey state yet
            }
            throw new Error(`Failed to fetch journey state: ${res.statusText}`);
        }
        
        const data = await res.json();
        
        return {
            domain: data.domain,
            strategy: data.strategy,
            currentStep: data.current_step,
            percentComplete: data.percent_complete ?? 0,
            status: data.status
        };
    } catch (error) {
        console.error("Error fetching journey state:", error);
        return null;
    }
}

