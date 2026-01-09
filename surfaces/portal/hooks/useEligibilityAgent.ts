import { useState, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface EligibilityCaseView {
    case_id: string;
    case_pk?: number;
    session_id?: number;
    status: string;
    case_state: any;
    score_state?: any;
    next_questions?: any[];
    improvement_plan?: any[];
    presentation_summary?: string;
}

export function useEligibilityAgent(caseId: string) {
    const [caseView, setCaseView] = useState<EligibilityCaseView | null>(null);
    const [loading, setLoading] = useState(false);

    const getCaseView = useCallback(async (sessionId?: number) => {
        try {
            const headers: HeadersInit = { "Content-Type": "application/json" };
            if (sessionId) {
                headers["X-Session-ID"] = sessionId.toString();
            }

            const response = await fetch(`${API_URL}/api/eligibility-v2/cases/${caseId}/view`, {
                method: "GET",
                headers,
            });

            if (response.ok) {
                const data = await response.json();
                setCaseView(data);
                return data;
            }
        } catch (error) {
            console.error("Failed to get case view:", error);
        }
        return null;
    }, [caseId]);

    const submitMessage = useCallback(async (message: string, sessionId?: number) => {
        setLoading(true);
        try {
            const headers: HeadersInit = { "Content-Type": "application/json" };
            if (sessionId) {
                headers["X-Session-ID"] = sessionId.toString();
            }

            const response = await fetch(`${API_URL}/api/eligibility-v2/cases/${caseId}/turn`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    event_type: "user_message",
                    data: { message },
                    timestamp: new Date().toISOString(),
                }),
            });

            if (response.ok) {
                const data = await response.json();
                await getCaseView(sessionId);
                return data;
            } else {
                throw new Error(`API error: ${response.status}`);
            }
        } catch (error) {
            console.error("Failed to submit message:", error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [caseId, getCaseView]);

    const submitForm = useCallback(async (formData: Record<string, any>, sessionId?: number) => {
        setLoading(true);
        try {
            const headers: HeadersInit = { "Content-Type": "application/json" };
            if (sessionId) {
                headers["X-Session-ID"] = sessionId.toString();
            }

            const response = await fetch(`${API_URL}/api/eligibility-v2/cases/${caseId}/turn`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    event_type: "form_submit",
                    data: formData,
                    timestamp: new Date().toISOString(),
                }),
            });

            if (response.ok) {
                const data = await response.json();
                await getCaseView(sessionId);
                return data;
            } else {
                throw new Error(`API error: ${response.status}`);
            }
        } catch (error) {
            console.error("Failed to submit form:", error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [caseId, getCaseView]);

    return {
        caseView,
        loading,
        getCaseView,
        submitMessage,
        submitForm,
    };
}
