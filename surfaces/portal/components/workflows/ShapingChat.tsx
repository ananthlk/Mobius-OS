"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, User } from "lucide-react";
import { useSession } from "next-auth/react";
import MobiusIcon from "@/components/MobiusIcon";
import ThinkingContainer from "@/components/ThinkingContainer";
import Tooltip from "@/components/Tooltip";
import ActionButtons from "./ActionButtons";
import FeedbackCapture from "@/components/FeedbackCapture";
import StructuredForm from "./StructuredForm";

interface Message {
    id: string;
    role: "system" | "user" | "thinking";
    content?: string; // Only for system/user messages
    thinkingMessages?: string[]; // Only for thinking role
    collapsed?: boolean; // For thinking containers (default: false while streaming, true when system responds)
    timestamp: number;
    memoryEventId?: number; // For feedback linking
    feedback?: {
        rating: "thumbs_up" | "thumbs_down";
        comment?: string | null;
    } | null;
}

interface ShapingChatProps {
    initialQuery: string;
    onUpdate: (query: string) => void;
    onSessionUpdate?: (data: any) => void; // New callback for full state sync
    sessionId?: number | null;
    progressState?: { status?: string }; // Add progress state to detect planning phase
}

export default function ShapingChat({ initialQuery, onUpdate, onSessionUpdate, sessionId, progressState }: ShapingChatProps) {
    const { data: session } = useSession();
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [currentThinkingId, setCurrentThinkingId] = useState<string | null>(null); // Track active thinking container ID
    const [expandedThinkingIds, setExpandedThinkingIds] = useState<Set<string>>(new Set()); // Track which thinking blocks are expanded
    const [explicitlyCollapsedIds, setExplicitlyCollapsedIds] = useState<Set<string>>(new Set()); // Track which thinking blocks are explicitly collapsed by user
    const [userOverriddenIds, setUserOverriddenIds] = useState<Set<string>>(new Set()); // Track containers user explicitly expanded after system collapse
    const [actionButtons, setActionButtons] = useState<any>(null);
    const [activeForm, setActiveForm] = useState<any>(null); // Structured form data
    const [feedbackUIs, setFeedbackUIs] = useState<Map<number, number>>(new Map()); // memory_event_id -> message index
    const [latestSystemMessageId, setLatestSystemMessageId] = useState<string | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const isUserScrollingRef = useRef(false);
    const lastMessageCountRef = useRef(0);
    const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    
    // Memoize action complete handler to prevent unnecessary re-renders
    const handleActionComplete = useCallback((buttonId: string, result: any) => {
        console.log(`Action button ${buttonId} completed:`, result);
        
        // Clear buttons after successful action
        if (result && result.status === 'success') {
            setActionButtons(null);
            
            // If there's a next_step, trigger it
            if (result.next_step === 'compute_plan' && sessionId) {
                // Trigger compute plan step
                const triggerNextStep = async () => {
                    try {
                        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                        const response = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}/planning-phase/compute`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                        });
                        const computeResult = await response.json();
                        console.log('Compute plan result:', computeResult);
                    } catch (error) {
                        console.error('Failed to trigger compute plan:', error);
                    }
                };
                // Small delay to ensure decision is saved
                setTimeout(triggerNextStep, 500);
            }
        }
    }, [sessionId]);

    // Check if user is near bottom of scroll (within 100px)
    const isNearBottom = (element: HTMLDivElement): boolean => {
        const { scrollTop, scrollHeight, clientHeight } = element;
        return scrollHeight - scrollTop - clientHeight < 100;
    };

    // Auto-scroll only if user is near bottom (hasn't manually scrolled up)
    useEffect(() => {
        if (scrollRef.current) {
            const element = scrollRef.current;
            
            // Only auto-scroll if:
            // 1. User is near the bottom (hasn't manually scrolled up), OR
            // 2. New messages were added (not just thinking updates)
            const newMessageCount = messages.filter(m => m.role !== "thinking").length;
            const hasNewMessages = newMessageCount > lastMessageCountRef.current;
            const shouldAutoScroll = isNearBottom(element) || hasNewMessages;
            
            if (shouldAutoScroll && !isUserScrollingRef.current) {
                // Use requestAnimationFrame to ensure smooth scrolling
                requestAnimationFrame(() => {
                    if (scrollRef.current) {
                        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                    }
                });
            }
            
            lastMessageCountRef.current = newMessageCount;
        }
    }, [messages]);

    // Track user scroll behavior
    useEffect(() => {
        const element = scrollRef.current;
        if (!element) return;

        const handleScroll = () => {
            // Mark that user is scrolling
            isUserScrollingRef.current = true;
            
            // Clear any existing timeout
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
            
            // Reset the flag after user stops scrolling for 1 second
            scrollTimeoutRef.current = setTimeout(() => {
                isUserScrollingRef.current = false;
            }, 1000);
        };

        element.addEventListener('scroll', handleScroll, { passive: true });
        return () => {
            element.removeEventListener('scroll', handleScroll);
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
        };
    }, []);

    // Auto-collapse thinking containers when they first become collapsed (only once, not on every update)
    // But respect user's explicit override if they've expanded it after system collapse
    useEffect(() => {
        const collapsedIds = messages
            .filter(msg => msg.role === "thinking" && msg.collapsed)
            .map(msg => msg.id);
        
        if (collapsedIds.length > 0) {
            setExpandedThinkingIds(prev => {
                const newSet = new Set(prev);
                let changed = false;
                collapsedIds.forEach(id => {
                    // Only auto-collapse if user hasn't explicitly overridden it
                    if (newSet.has(id) && !userOverriddenIds.has(id)) {
                        newSet.delete(id);
                        changed = true;
                    }
                });
                return changed ? newSet : prev;
            });
        }
    }, [messages, userOverriddenIds]);

    // Initial Load
    useEffect(() => {
        if (initialQuery && messages.length === 0) {
            // If we have a sessionId, we *should* fetch history. For now, we assume just started.
            const userMsg: Message = { id: "1", role: "user", content: initialQuery, timestamp: Date.now() };
            setMessages([userMsg]);
            // Note: Initial thinking container will be created by polling when backend responds
        }
    }, [initialQuery, sessionId]);

    // Polling Effect (The "Stream Listener")
    useEffect(() => {
        let interval: NodeJS.Timeout;
        const lastGateKeyRef = { value: null as string | null }; // Use ref object to persist across closures
        if (sessionId) {
            interval = setInterval(async () => {
                try {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                    const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}`);
                    const data = await res.json();

                    // Extract current gate key from gate_state
                    const currentGateKey = data.gate_state?.current_gate_key || null;
                    
                    // Skip button update if gate key hasn't changed (prevents showing stale state during processing)
                    // Only skip if we've seen a gate key before (not on initial load) and gates are not complete
                    const shouldSkipButtonUpdate = lastGateKeyRef.value !== null && 
                                                   currentGateKey === lastGateKeyRef.value && 
                                                   data.gates_complete === false;
                    
                    // Always update transcript and pass to parent
                    if (data.transcript && Array.isArray(data.transcript)) {
                        // Pass full state up to parent (for Left Rail sync)
                        if (onSessionUpdate) onSessionUpdate(data);
                    }
                    
                    // Skip button update if gate key unchanged (still processing)
                    if (shouldSkipButtonUpdate) {
                        return; // Skip button update to avoid showing stale buttons
                    }
                    
                    // Gate key changed or first load - update everything including buttons
                    lastGateKeyRef.value = currentGateKey;

                    if (data.transcript && Array.isArray(data.transcript)) {
                        // Check for ACTION_BUTTONS artifacts - only update if changed
                        // Backend should filter out buttons if decision is made, but we also check here
                        const currentButtonArtifact = data.latest_action_buttons || 
                            (data.artifacts && Array.isArray(data.artifacts) 
                                ? data.artifacts.find((a: any) => a.type === 'ACTION_BUTTONS')
                                : null);
                        
                        // #region agent log
                        if (currentButtonArtifact) {
                            fetch('http://127.0.0.1:7243/ingest/2d690d57-f7bb-4ea6-989d-27d335039802', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    location: 'ShapingChat.tsx:194',
                                    message: 'Received action buttons from backend',
                                    data: {
                                        context: currentButtonArtifact.context,
                                        button_count: currentButtonArtifact.buttons?.length || 0,
                                        button_ids: currentButtonArtifact.buttons?.map((b: any) => b.id) || [],
                                        button_labels: currentButtonArtifact.buttons?.map((b: any) => b.label) || [],
                                        has_other_button: currentButtonArtifact.buttons?.some((b: any) => b.label === 'Other' || b.id?.includes('_other')) || false
                                    },
                                    timestamp: Date.now(),
                                    sessionId: 'debug-session',
                                    runId: 'run1',
                                    hypothesisId: 'C'
                                })
                            }).catch(() => {});
                        }
                        // #endregion
                        
                        if (currentButtonArtifact) {
                            setActionButtons((prev: any) => {
                                // Compare by stringifying to avoid unnecessary updates
                                const prevStr = JSON.stringify(prev);
                                const newStr = JSON.stringify(currentButtonArtifact);
                                if (prevStr !== newStr) {
                                    // #region agent log
                                    fetch('http://127.0.0.1:7243/ingest/2d690d57-f7bb-4ea6-989d-27d335039802', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                            location: 'ShapingChat.tsx:210',
                                            message: 'Updating action buttons state',
                                            data: {
                                                prev_button_count: prev?.buttons?.length || 0,
                                                new_button_count: currentButtonArtifact.buttons?.length || 0,
                                                prev_button_ids: prev?.buttons?.map((b: any) => b.id) || [],
                                                new_button_ids: currentButtonArtifact.buttons?.map((b: any) => b.id) || []
                                            },
                                            timestamp: Date.now(),
                                            sessionId: 'debug-session',
                                            runId: 'run1',
                                            hypothesisId: 'C'
                                        })
                                    }).catch(() => {});
                                    // #endregion
                                    return currentButtonArtifact;
                                }
                                return prev;
                            });
                        } else {
                            // No action buttons in response - clear them (decision might have been made)
                            setActionButtons(null);
                        }
                        
                        // Check for FEEDBACK_UI artifacts and track them
                        const feedbackUIArtifacts = data.artifacts && Array.isArray(data.artifacts)
                            ? data.artifacts.filter((a: any) => a.type === 'FEEDBACK_UI')
                            : [];
                        
                        // Check for STRUCTURED_FORM artifacts
                        const structuredFormArtifact = data.artifacts && Array.isArray(data.artifacts)
                            ? data.artifacts.find((a: any) => a.type === 'STRUCTURED_FORM')
                            : null;
                        
                        if (structuredFormArtifact) {
                            console.log('[ShapingChat] Found STRUCTURED_FORM artifact:', structuredFormArtifact);
                            setActiveForm({
                                form_type: structuredFormArtifact.form_type || 'unknown',
                                message: structuredFormArtifact.message || '',
                                form_fields: structuredFormArtifact.form_fields || [],
                                submit_button: structuredFormArtifact.submit_button || null,
                                metadata: structuredFormArtifact.metadata || {}
                            });
                        } else {
                            // Only clear form if we're sure there's no form artifact (not just on first load)
                            // This prevents clearing the form during polling when it's still valid
                            if (activeForm && data.artifacts && Array.isArray(data.artifacts)) {
                                // Check if artifacts array exists but doesn't contain STRUCTURED_FORM
                                const hasFormArtifact = data.artifacts.some((a: any) => a.type === 'STRUCTURED_FORM');
                                if (!hasFormArtifact) {
                                    console.log('[ShapingChat] No STRUCTURED_FORM artifact found, clearing active form');
                                    setActiveForm(null);
                                }
                            }
                        }
                        
                        // Load feedback for ALL system messages with memory_event_id (async, non-blocking)
                        if (data.transcript && Array.isArray(data.transcript)) {
                            const systemMessages = data.transcript.filter((t: any) => t.role === "system" && t.memory_event_id);
                            if (systemMessages.length > 0) {
                                console.log(`[ShapingChat] Loading feedback for ${systemMessages.length} system messages with memory_event_id`);
                                // Load feedback asynchronously but don't block transcript update
                                Promise.all(systemMessages.map(async (msg: any) => {
                                    try {
                                        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                                        const user_id = session?.user?.id || "anonymous";
                                        const feedbackRes = await fetch(`${apiUrl}/api/feedback/${msg.memory_event_id}?user_id=${user_id}`);
                                        if (feedbackRes.ok) {
                                            const feedback = await feedbackRes.json();
                                            console.log(`[ShapingChat] Loaded feedback for memory_event_id=${msg.memory_event_id}:`, feedback);
                                            return { memoryEventId: msg.memory_event_id, feedback };
                                        } else if (feedbackRes.status === 404) {
                                            // No feedback yet - that's OK
                                            return { memoryEventId: msg.memory_event_id, feedback: null };
                                        }
                                    } catch (e) {
                                        console.error(`[ShapingChat] Error loading feedback for memory_event_id=${msg.memory_event_id}:`, e);
                                    }
                                    return { memoryEventId: msg.memory_event_id, feedback: null };
                                })).then(feedbackResults => {
                                    console.log(`[ShapingChat] Feedback loading complete, updating ${feedbackResults.length} messages`);
                                    // Update messages with feedback after loading
                                    setMessages(prev => prev.map(msg => {
                                        const feedbackResult = feedbackResults.find(fr => fr.memoryEventId === msg.memoryEventId);
                                        if (feedbackResult) {
                                            return { 
                                                ...msg, 
                                                feedback: feedbackResult.feedback ? {
                                                    rating: feedbackResult.feedback.rating,
                                                    comment: feedbackResult.feedback.comment
                                                } : null
                                            };
                                        }
                                        return msg;
                                    }));
                                });
                            } else {
                                console.log(`[ShapingChat] No system messages with memory_event_id found in transcript`);
                            }
                        }

                        // Update thinking container with thinking messages (if active and not collapsed)
                        if (data.latest_thought && currentThinkingId) {
                            setMessages(prev => prev.map(msg => {
                                if (msg.id === currentThinkingId && msg.role === "thinking" && !msg.collapsed) {
                                    // Use messages array if available (new format), otherwise fall back to single message
                                    const newMessages = data.latest_thought.messages || 
                                                      (data.latest_thought.message ? [data.latest_thought.message] : []);
                                    
                                    // Merge with existing, avoiding duplicates while preserving order
                                    const existing = msg.thinkingMessages || [];
                                    const existingSet = new Set(existing);
                                    const uniqueNew = newMessages.filter((m: string) => !existingSet.has(m));
                                    
                                    if (uniqueNew.length > 0) {
                                        return {
                                            ...msg,
                                            thinkingMessages: [...existing, ...uniqueNew]
                                        };
                                    }
                                }
                                return msg;
                            }));
                        }
                        
                        // If we have thinking messages but no container, and last message is user, create one
                        if (data.latest_thought && !currentThinkingId) {
                            // Use messages array if available, otherwise fall back to single message
                            const initialMessages = data.latest_thought.messages || 
                                                  (data.latest_thought.message ? [data.latest_thought.message] : []);
                            
                            if (initialMessages.length > 0) {
                                setMessages(prev => {
                                    const lastMsg = prev[prev.length - 1];
                                    // If last message is user and no thinking container exists, create one
                                    if (lastMsg && lastMsg.role === "user") {
                                        const thinkingId = `thinking_${Date.now()}`;
                                        setCurrentThinkingId(thinkingId);
                                        return [...prev, {
                                            id: thinkingId,
                                            role: "thinking" as const,
                                            thinkingMessages: initialMessages,
                                            collapsed: false,
                                            timestamp: Date.now()
                                        }];
                                    }
                                    return prev;
                                });
                            }
                        }

                        // Update transcript messages and manage thinking containers
                        setMessages(prev => {
                            // Extract only user and system messages from transcript
                            const transcriptMsgs = data.transcript.map((t: any, idx: number) => ({
                                id: `poll_${idx}`,
                                role: t.role as "system" | "user",
                                content: t.content,
                                timestamp: t.timestamp === "now" ? Date.now() : t.timestamp,
                                memoryEventId: t.memory_event_id, // Include memory_event_id if available
                                feedback: null // Will be loaded separately
                            }));

                            // Separate thinking containers from regular messages
                            const thinkingContainers = prev.filter(m => m.role === "thinking");
                            const regularMsgs = prev.filter(m => m.role !== "thinking");

                            // Check if a new system message arrived
                            const lastTranscriptMsg = transcriptMsgs[transcriptMsgs.length - 1];
                            const lastRegularMsg = regularMsgs[regularMsgs.length - 1];
                            
                            const hasNewSystemMsg = lastTranscriptMsg?.role === "system" && (
                                transcriptMsgs.length > regularMsgs.length ||
                                !lastRegularMsg ||
                                (lastRegularMsg.content !== lastTranscriptMsg.content)
                            );
                            
                            // Update latest system message ID - track the last system message from transcript
                            if (lastTranscriptMsg?.role === "system") {
                                // Use the transcript message's ID (it will be matched/merged with local message below)
                                // We'll update this after messages are merged
                            }

                            // If new system message arrived, collapse the active thinking container
                            if (hasNewSystemMsg && currentThinkingId) {
                                console.log('System message arrived, collapsing thinking container:', currentThinkingId);
                                const updatedContainers = thinkingContainers.map(msg => {
                                    if (msg.id === currentThinkingId) {
                                        console.log('Setting collapsed: true for container:', msg.id);
                                        return { ...msg, collapsed: true };
                                    }
                                    return msg;
                                });
                                // Clear active thinking immediately - this will stop streaming
                                setCurrentThinkingId(null);
                                
                                // Build result: interleave transcript messages with thinking containers
                                const result: Message[] = [];
                                let containerIdx = 0;
                                
                                for (const transcriptMsg of transcriptMsgs) {
                                    result.push(transcriptMsg);
                                    // If this is a user message, check if there's a thinking container after it
                                    if (transcriptMsg.role === "user" && containerIdx < updatedContainers.length) {
                                        // Find thinking container that should follow this user message
                                        // For now, match by position - each user message gets its thinking container
                                        const thinkingContainer = updatedContainers[containerIdx];
                                        if (thinkingContainer && !result.find(m => m.id === thinkingContainer.id)) {
                                            result.push(thinkingContainer);
                                            containerIdx++;
                                        }
                                    }
                                }
                                
                                // Add any remaining thinking containers
                                for (let i = containerIdx; i < updatedContainers.length; i++) {
                                    if (!result.find(m => m.id === updatedContainers[i].id)) {
                                        result.push(updatedContainers[i]);
                                    }
                                }
                                
                                // Update latest system message ID after merging
                                const lastSystemMsg = result.filter(m => m.role === "system").pop();
                                if (lastSystemMsg) {
                                    setLatestSystemMessageId(lastSystemMsg.id);
                                }
                                
                                return result;
                            }

                            // Update existing messages while preserving thinking containers
                            // Also check if any thinking containers should be collapsed (if system message exists but wasn't detected above)
                            const lastMsgInTranscript = transcriptMsgs[transcriptMsgs.length - 1];
                            const shouldCollapseActive = lastMsgInTranscript?.role === "system" && currentThinkingId;
                            
                            const finalThinkingContainers = shouldCollapseActive 
                                ? thinkingContainers.map(msg => {
                                    if (msg.id === currentThinkingId) {
                                        console.log('Collapsing thinking container in else branch:', msg.id);
                                        return { ...msg, collapsed: true };
                                    }
                                    return msg;
                                })
                                : thinkingContainers;
                            
                            if (shouldCollapseActive) {
                                setCurrentThinkingId(null);
                            }
                            
                            // Match transcript messages with local messages by content
                            // Preserve local messages that haven't been confirmed in transcript yet
                            const result: Message[] = [];
                            const matchedLocalIndices = new Set<number>();
                            let containerIdx = 0;
                            
                            // Process transcript messages and match with local messages
                            for (const transcriptMsg of transcriptMsgs) {
                                // Try to find matching local message by content and role
                                const matchingLocalIdx = regularMsgs.findIndex((localMsg, idx) => 
                                    !matchedLocalIndices.has(idx) &&
                                    localMsg.content === transcriptMsg.content &&
                                    localMsg.role === transcriptMsg.role
                                );
                                
                                if (matchingLocalIdx >= 0) {
                                    // Found a match - use transcript message (more authoritative) but preserve local ID and feedback
                                    matchedLocalIndices.add(matchingLocalIdx);
                                    const localMsg = regularMsgs[matchingLocalIdx];
                                    result.push({
                                        ...transcriptMsg,
                                        id: localMsg.id, // Preserve local ID
                                        feedback: localMsg.feedback, // Preserve feedback if loaded
                                        memoryEventId: transcriptMsg.memoryEventId || localMsg.memoryEventId // Use transcript's memory_event_id if available
                                    });
                                } else {
                                    // No match found - this is a new message from backend
                                    result.push(transcriptMsg);
                                }
                                
                                // If this is a user message and we have a thinking container, add it
                                if (transcriptMsg.role === "user" && containerIdx < finalThinkingContainers.length) {
                                    const thinkingContainer = finalThinkingContainers[containerIdx];
                                    if (thinkingContainer && !result.find(m => m.id === thinkingContainer.id)) {
                                        result.push(thinkingContainer);
                                        containerIdx++;
                                    }
                                }
                            }
                            
                            // Add any local messages that weren't matched (pending backend confirmation)
                            for (let i = 0; i < regularMsgs.length; i++) {
                                if (!matchedLocalIndices.has(i)) {
                                    const localMsg = regularMsgs[i];
                                    // Only preserve if it's a user message (system messages should come from backend)
                                    // and it's relatively recent (within last 10 seconds)
                                    const isRecent = Date.now() - localMsg.timestamp < 10000;
                                    if (localMsg.role === "user" && isRecent && !result.find(m => m.content === localMsg.content && m.role === localMsg.role)) {
                                        // Insert before any thinking containers that might follow
                                        const insertIndex = result.length;
                                        result.splice(insertIndex, 0, localMsg);
                                        
                                        // Check if there's a thinking container for this user message
                                        if (containerIdx < finalThinkingContainers.length) {
                                            const thinkingContainer = finalThinkingContainers[containerIdx];
                                            if (thinkingContainer && !result.find(m => m.id === thinkingContainer.id)) {
                                                result.push(thinkingContainer);
                                                containerIdx++;
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Add any remaining thinking containers that weren't inserted
                            for (let i = containerIdx; i < finalThinkingContainers.length; i++) {
                                if (!result.find(m => m.id === finalThinkingContainers[i].id)) {
                                    result.push(finalThinkingContainers[i]);
                                }
                            }
                            
                            // Update latest system message ID after merging
                            const lastSystemMsg = result.filter(m => m.role === "system").pop();
                            if (lastSystemMsg) {
                                setLatestSystemMessageId(lastSystemMsg.id);
                            }
                            
                            return result;
                        });
                    }
                } catch (e) {
                    console.error("Polling failed", e);
                }
            }, 1000); // Increased to 1000ms to reduce race conditions with gate state updates
        }
        return () => {
            if (interval) clearInterval(interval);
        };
    }, [currentThinkingId, sessionId, onSessionUpdate]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: Message = { 
            id: Date.now().toString(), 
            role: "user", 
            content: input, 
            timestamp: Date.now() 
        };
        
        // Clear previous thinking container when new user message is sent
        // Backend will filter thinking messages to only show those after this user message
        setCurrentThinkingId(null);
        setExpandedThinkingIds(new Set());
        setUserOverriddenIds(new Set());
        
        // Create thinking container immediately after user message
        const thinkingId = `thinking_${Date.now()}`;
        const thinkingMsg: Message = {
            id: thinkingId,
            role: "thinking",
            thinkingMessages: ["Consultant is thinking..."],
            collapsed: false, // Start expanded while streaming
            timestamp: Date.now()
        };

        setMessages(prev => [...prev, userMsg, thinkingMsg]);
        setCurrentThinkingId(thinkingId); // Set as active thinking container
        setInput("");

        // Notify parent (for sidebar re-rank)
        onUpdate(input);

        // PERSISTENCE: Call Backend
        if (sessionId) {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const user_id = session?.user?.id || "anonymous";
                const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: input, user_id }),
                });

                await res.json();
                // Polling will continue and update the thinking container
            } catch (e) {
                console.error("Chat failed", e);
                // On error, collapse thinking and clear it
                setMessages(prev => prev.filter(m => m.id !== thinkingId));
                setCurrentThinkingId(null);
            }
        } else {
            // No session ID - this shouldn't happen if backend is working
            console.warn("ShapingChat: sessionId is null, cannot send message");
            setTimeout(() => {
                const sysMsg: Message = {
                    id: (Date.now() + 1).toString(),
                    role: "system",
                    content: "Session ID missing. Please refresh and try again.",
                    timestamp: Date.now()
                };
                setMessages(prev => {
                    // Remove thinking container and add system message
                    const withoutThinking = prev.filter(m => m.id !== thinkingId);
                    return [...withoutThinking, sysMsg];
                });
                setCurrentThinkingId(null);
            }, 1000);
        }
    };

    return (
        <div className="flex flex-col h-full bg-[var(--bg-primary)] rounded-2xl shadow-[var(--shadow-md)] border-2 border-[var(--border-medium)] overflow-hidden relative">
            {/* Header */}
            <div className="p-4 border-b-2 border-[var(--border-medium)] bg-gradient-to-b from-[var(--bg-secondary)] to-[var(--bg-primary)] flex items-center gap-2 shadow-sm">
                <Tooltip content={progressState?.status === "PLANNING" ? "Planning Phase Agent - Review and refine your workflow plan" : "AI agent that helps define and shape your workflow problem through conversation"}>
                    <div className="cursor-help">
                        <MobiusIcon size={20} animated={false} />
                    </div>
                </Tooltip>
                <span className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">
                    {progressState?.status === "PLANNING" ? "Planning Phase" : "Problem Shaping Agent"}
                </span>
            </div>

            {/* Chat Area - Match chat page padding */}
            <div className="flex-1 overflow-y-auto p-4 md:p-10 space-y-8" ref={scrollRef}>
                {messages.map((msg) => {
                    // Render thinking containers separately
                    if (msg.role === "thinking") {
                        // Only streaming if not collapsed AND it's the current active thinking container
                        // Explicitly check collapsed first - if collapsed is true, never streaming
                        // Also check if currentThinkingId is null (system message arrived)
                        // If currentThinkingId is null, it means system message arrived, so stop streaming
                        const isStreaming = msg.collapsed !== true && msg.id === currentThinkingId && currentThinkingId !== null;
                        
                        // Debug log to see what's happening
                        if (msg.id === currentThinkingId) {
                            console.log('Thinking container streaming check:', {
                                id: msg.id,
                                collapsed: msg.collapsed,
                                currentThinkingId,
                                isStreaming
                            });
                        }
                        // Three states: true (explicitly expanded), false (explicitly collapsed), undefined (never toggled)
                        // Once user explicitly expands after system collapse, they take full control
                        // Priority: user's explicit state > system collapsed state
                        const isExpanded: boolean | undefined = expandedThinkingIds.has(msg.id) ? true : (
                            explicitlyCollapsedIds.has(msg.id) ? false : 
                            (msg.collapsed && !userOverriddenIds.has(msg.id) ? false : undefined)
                        );
                        
                        return (
                            <ThinkingContainer
                                key={msg.id}
                                message={{
                                    id: msg.id,
                                    thinkingMessages: msg.thinkingMessages || [],
                                    collapsed: msg.collapsed
                                }}
                                isExpanded={isExpanded}
                                onToggle={() => {
                                    // Allow toggle even if system collapsed it - user can expand to see thinking
                                    if (expandedThinkingIds.has(msg.id)) {
                                        // Currently expanded, so collapse it
                                        setExpandedThinkingIds(prev => {
                                            const newSet = new Set(prev);
                                            newSet.delete(msg.id);
                                            return newSet;
                                        });
                                        setExplicitlyCollapsedIds(prev => new Set(prev).add(msg.id));
                                        // Remove from override set since user is now collapsing it
                                        setUserOverriddenIds(prev => {
                                            const newSet = new Set(prev);
                                            newSet.delete(msg.id);
                                            return newSet;
                                        });
                                    } else {
                                        // Currently collapsed or never toggled, so expand it
                                        setExpandedThinkingIds(prev => new Set(prev).add(msg.id));
                                        setExplicitlyCollapsedIds(prev => {
                                            const newSet = new Set(prev);
                                            newSet.delete(msg.id);
                                            return newSet;
                                        });
                                        // If system collapsed it, mark as user-overridden so system can't force collapse again
                                        if (msg.collapsed) {
                                            setUserOverriddenIds(prev => new Set(prev).add(msg.id));
                                        }
                                    }
                                }}
                                isStreaming={isStreaming}
                            />
                        );
                    }

                    // Render user/system messages - Match chat page styling
                    const isLatestSystemMessage = msg.role === "system" && 
                        latestSystemMessageId !== null && 
                        msg.id === latestSystemMessageId;
                    
                    return (
                    <div key={msg.id} className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[80%] md:max-w-[70%] rounded-[20px] px-6 py-4 text-[15px] leading-relaxed shadow-sm break-words overflow-wrap-anywhere ${msg.role === "user"
                            ? 'bg-[#E8F0FE] text-[#1f1f1f] rounded-tr-none' // User: Light Blue (Google User style)
                            : 'bg-[var(--bg-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-tl-none'
                            }`}>
                            {/* Render Markdown-lite (bolding) */}
                            {msg.content && (
                                <div className="break-words overflow-wrap-anywhere" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>') }} />
                            )}
                            
                            {/* Render feedback capture for ALL system messages with memoryEventId */}
                            {msg.role === "system" && msg.memoryEventId && (
                                <FeedbackCapture
                                    memoryEventId={msg.memoryEventId}
                                    userId={session?.user?.id || "anonymous"}
                                    isLatestMessage={isLatestSystemMessage}
                                    existingFeedback={msg.feedback}
                                    onFeedbackSubmitted={() => {
                                        // Reload feedback for this specific message after submission
                                        (async () => {
                                            try {
                                                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                                                const user_id = session?.user?.id || "anonymous";
                                                const feedbackRes = await fetch(`${apiUrl}/api/feedback/${msg.memoryEventId}?user_id=${user_id}`);
                                                if (feedbackRes.ok) {
                                                    const feedback = await feedbackRes.json();
                                                    // Update the message with new feedback
                                                    setMessages(prev => prev.map(m => 
                                                        m.memoryEventId === msg.memoryEventId 
                                                            ? { ...m, feedback: feedback ? {
                                                                rating: feedback.rating,
                                                                comment: feedback.comment
                                                            } : null }
                                                            : m
                                                    ));
                                                }
                                            } catch (e) {
                                                console.error(`[ShapingChat] Error reloading feedback:`, e);
                                            }
                                        })();
                                    }}
                                />
                            )}
                        </div>
                    </div>
                    );
                        })}
                        
                        {/* Render action buttons after messages */}
                        {actionButtons && actionButtons.buttons && (
                            <ActionButtons
                                buttons={actionButtons.buttons}
                                context={actionButtons.context}
                                message={actionButtons.message}
                                sessionId={sessionId}
                                onActionComplete={handleActionComplete}
                            />
                        )}
                        
                        {/* Render structured form if present */}
                        {activeForm && activeForm.form_fields && activeForm.form_fields.length > 0 && (
                            <div className="w-full flex justify-start">
                                <StructuredForm
                                    formType={activeForm.form_type}
                                    message={activeForm.message}
                                    formFields={activeForm.form_fields}
                                    submitButton={activeForm.submit_button}
                                    sessionId={sessionId}
                                    onSuccess={(result) => {
                                        console.log('[ShapingChat] Form submitted successfully:', result);
                                        // Clear the form after successful submission
                                        setActiveForm(null);
                                        // Optionally add a user message showing what was submitted
                                        if (result.message) {
                                            // The backend will handle adding the response to the transcript
                                            // We just need to trigger a refresh
                                        }
                                    }}
                                    onError={(error) => {
                                        console.error('[ShapingChat] Form submission error:', error);
                                        // Keep form visible on error so user can retry
                                    }}
                                />
                            </div>
                        )}
                    </div>

            {/* Input Area - Match chat page styling */}
            <div className="p-4 md:p-6 border-t border-[var(--border-subtle)] bg-[var(--bg-primary)]">
                <div className="bg-[#F0F4F8] rounded-full flex items-center px-2 py-2 focus-within:bg-white focus-within:shadow-md focus-within:ring-1 focus-within:ring-gray-200 transition-all">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="Clarify the problem..."
                        rows={1}
                        className="flex-1 bg-transparent border-none outline-none px-4 py-2 text-[#1f1f1f] placeholder-[#5F6368] resize-none overflow-hidden break-words pr-12"
                        style={{ minHeight: '40px', maxHeight: '120px' }}
                        onInput={(e) => {
                            const target = e.target as HTMLTextAreaElement;
                            target.style.height = 'auto';
                            target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className="w-10 h-10 flex items-center justify-center rounded-full text-[#1a73e8] hover:bg-blue-50 disabled:opacity-50 transition-colors"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
}
