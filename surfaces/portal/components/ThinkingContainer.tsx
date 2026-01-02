"use client";

import { Bot, ChevronDown, ChevronUp } from "lucide-react";
import Tooltip from "@/components/Tooltip";

export interface ThinkingMessage {
    id: string;
    thinkingMessages?: string[];
    collapsed?: boolean;
}

export interface ThinkingContainerProps {
    message: ThinkingMessage;
    isExpanded: boolean | undefined; // true = explicitly expanded, false = explicitly collapsed, undefined = never toggled
    onToggle: () => void;
    isStreaming?: boolean;
}

export default function ThinkingContainer({ 
    message, 
    isExpanded, 
    onToggle, 
    isStreaming = false 
}: ThinkingContainerProps) {
    // Determine if content should be shown:
    // - If explicitly expanded (true), always show
    // - If explicitly collapsed (false), never show (even if streaming)
    // - If never toggled (undefined), auto-expand if streaming
    const shouldShowContent = isExpanded === true || (isExpanded === undefined && isStreaming && !message.collapsed);
    // Never show streaming animation if message is collapsed
    const showStreaming = isStreaming && !message.collapsed;
    
    return (
        <div className="flex gap-3 relative">
            {/* Timeline line and icon */}
            <div className="flex flex-col items-center flex-shrink-0">
                <Tooltip content="AI thinking process - shows the reasoning steps the agent takes to understand and respond to your request">
                    <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center border-2 border-white shadow-sm cursor-help">
                        <Bot size={12} />
                    </div>
                </Tooltip>
                {shouldShowContent && (
                    <div className="w-0.5 h-full bg-blue-200 mt-1 min-h-[20px]"></div>
                )}
            </div>
            
            {/* Content area */}
            <div className="flex-1 min-w-0">
                <button
                    onClick={onToggle}
                    className="w-full text-left flex items-center justify-between gap-2 py-1.5 group"
                >
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-0.5 h-4 bg-blue-500 flex-shrink-0"></div>
                        <span className="text-xs text-blue-600 font-medium truncate">
                            {showStreaming ? (
                                <span className="inline-flex items-center gap-1.5">
                                    <span className="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></span>
                                    <span>Thinking...</span>
                                </span>
                            ) : (
                                `Thinking (${message.thinkingMessages?.length || 0})`
                            )}
                        </span>
                    </div>
                    <div className="flex-shrink-0">
                        {shouldShowContent ? (
                            <ChevronUp size={12} className="text-blue-400 group-hover:text-blue-600 transition-colors" />
                        ) : (
                            <ChevronDown size={12} className="text-blue-400 group-hover:text-blue-600 transition-colors" />
                        )}
                    </div>
                </button>
                
                {shouldShowContent && (
                    <div className="ml-2.5 mt-1 pb-2">
                        {/* Thinking messages container with max height and scroll */}
                        <div className="max-h-[300px] overflow-y-auto space-y-1.5 custom-scrollbar pr-1">
                            {message.thinkingMessages?.map((thought, idx) => (
                                <div key={idx} className="text-xs text-gray-600 leading-relaxed pl-2 border-l-2 border-blue-200">
                                    {thought}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
