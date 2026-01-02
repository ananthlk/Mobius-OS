"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Bot, User } from "lucide-react";
import ThinkingContainer from "@/components/ThinkingContainer";
import Tooltip from "@/components/Tooltip";
import ActionButtons from "./ActionButtons";

interface Message {
    id: string;
    role: "system" | "user" | "thinking";
    content?: string; // Only for system/user messages
    thinkingMessages?: string[]; // Only for thinking role
    collapsed?: boolean; // For thinking containers (default: false while streaming, true when system responds)
    timestamp: number;
}

interface ShapingChatProps {
    initialQuery: string;
    onUpdate: (query: string) => void;
    onSessionUpdate?: (data: any) => void; // New callback for full state sync
    sessionId?: number | null;
    progressState?: { status?: string }; // Add progress state to detect planning phase
}

export default function ShapingChat({ initialQuery, onUpdate, onSessionUpdate, sessionId, progressState }: ShapingChatProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [currentThinkingId, setCurrentThinkingId] = useState<string | null>(null); // Track active thinking container ID
    const [expandedThinkingIds, setExpandedThinkingIds] = useState<Set<string>>(new Set()); // Track which thinking blocks are expanded
    const [explicitlyCollapsedIds, setExplicitlyCollapsedIds] = useState<Set<string>>(new Set()); // Track which thinking blocks are explicitly collapsed by user
    const [userOverriddenIds, setUserOverriddenIds] = useState<Set<string>>(new Set()); // Track containers user explicitly expanded after system collapse
    const [actionButtons, setActionButtons] = useState<any>(null);
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
        if (sessionId) {
            interval = setInterval(async () => {
                try {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                    const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}`);
                    const data = await res.json();

                    if (data.transcript && Array.isArray(data.transcript)) {
                        // Pass full state up to parent (for Left Rail sync)
                        if (onSessionUpdate) onSessionUpdate(data);
                        
                        // Check for ACTION_BUTTONS artifacts - only update if changed
                        // Backend should filter out buttons if decision is made, but we also check here
                        const currentButtonArtifact = data.latest_action_buttons || 
                            (data.artifacts && Array.isArray(data.artifacts) 
                                ? data.artifacts.find((a: any) => a.type === 'ACTION_BUTTONS')
                                : null);
                        
                        if (currentButtonArtifact) {
                            setActionButtons((prev: any) => {
                                // Compare by stringifying to avoid unnecessary updates
                                const prevStr = JSON.stringify(prev);
                                const newStr = JSON.stringify(currentButtonArtifact);
                                if (prevStr !== newStr) {
                                    return currentButtonArtifact;
                                }
                                return prev;
                            });
                        } else {
                            // No action buttons in response - clear them (decision might have been made)
                            setActionButtons(null);
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
                                timestamp: t.timestamp === "now" ? Date.now() : t.timestamp
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
                                    // Found a match - use transcript message (more authoritative) but preserve local ID if it's more recent
                                    matchedLocalIndices.add(matchingLocalIdx);
                                    result.push(transcriptMsg);
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
                            
                            return result;
                        });
                    }
                } catch (e) {
                    console.error("Polling failed", e);
                }
            }, 500); // 500ms Tick matches the backend "Event Emitter" pace
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
                const res = await fetch(`${apiUrl}/api/workflows/shaping/${sessionId}/chat`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: input, user_id: "user_123" }),
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
        <div className="flex flex-col h-full bg-white rounded-2xl shadow-md border-2 border-gray-300 overflow-hidden relative">
            {/* Header */}
            <div className="p-4 border-b-2 border-gray-300 bg-gradient-to-b from-gray-50 to-white flex items-center gap-2 shadow-sm">
                <Tooltip content={progressState?.status === "PLANNING" ? "Planning Phase Agent - Review and refine your workflow plan" : "AI agent that helps define and shape your workflow problem through conversation"}>
                    <Bot className="w-5 h-5 text-blue-600 cursor-help" />
                </Tooltip>
                <span className="text-sm font-bold text-gray-700 uppercase tracking-wider">
                    {progressState?.status === "PLANNING" ? "Planning Phase" : "Problem Shaping Agent"}
                </span>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
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

                    // Render user/system messages
                    return (
                    <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === "system" ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"}`}>
                            {msg.role === "system" ? <Bot size={16} /> : <User size={16} />}
                        </div>
                            <div className={`max-w-[80%] rounded-2xl overflow-hidden ${msg.role === "system" ? "bg-blue-50 rounded-tl-none" : "bg-gray-100 rounded-tr-none"}`}>
                                {/* Message content container with max height and scroll */}
                                <div className={`max-h-[400px] overflow-y-auto p-3 text-sm leading-relaxed text-[#1A1A1A] custom-scrollbar break-words ${msg.role === "system" ? "" : ""}`}>
                            {/* Render Markdown-lite (bolding) if needed, for now raw text */}
                                    {msg.content && (
                            <div className="break-words overflow-wrap-anywhere" dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>') }} />
                                    )}
                        </div>
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
                    </div>

            {/* Input Area */}
            <div className="p-4 border-t-2 border-gray-300 bg-white">
                <div className="relative">
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
                        className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all pr-12 text-gray-800 placeholder-gray-400 resize-none overflow-hidden break-words"
                        style={{ minHeight: '44px', maxHeight: '120px' }}
                        onInput={(e) => {
                            const target = e.target as HTMLTextAreaElement;
                            target.style.height = 'auto';
                            target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Send size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
}
