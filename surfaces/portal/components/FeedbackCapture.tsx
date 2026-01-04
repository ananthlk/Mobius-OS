"use client";

import { useState, useEffect } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";

interface FeedbackCaptureProps {
    memoryEventId: number;
    userId: string;
    isLatestMessage: boolean;
    existingFeedback?: {
        rating: "thumbs_up" | "thumbs_down";
        comment?: string | null;
    } | null;
    onFeedbackSubmitted?: () => void; // Callback to refresh feedback after submission
}

export default function FeedbackCapture({
    memoryEventId,
    userId,
    isLatestMessage,
    existingFeedback,
    onFeedbackSubmitted
}: FeedbackCaptureProps) {
    const [rating, setRating] = useState<"thumbs_up" | "thumbs_down" | null>(
        existingFeedback?.rating || null
    );
    const [comment, setComment] = useState<string>(existingFeedback?.comment || "");
    const [showCommentInput, setShowCommentInput] = useState<boolean>(
        existingFeedback?.rating === "thumbs_down" && !existingFeedback?.comment
    );
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [isSubmitted, setIsSubmitted] = useState<boolean>(!!existingFeedback);

    // Update state when existingFeedback changes
    useEffect(() => {
        if (existingFeedback) {
            setRating(existingFeedback.rating);
            setComment(existingFeedback.comment || "");
            setIsSubmitted(true);
            setShowCommentInput(existingFeedback.rating === "thumbs_down" && !existingFeedback.comment);
        } else {
            setRating(null);
            setComment("");
            setIsSubmitted(false);
            setShowCommentInput(false);
        }
    }, [existingFeedback]);

    // For non-latest messages with existing feedback, show it but make it read-only
    const isReadOnly = !isLatestMessage && !!existingFeedback;

    // Always show feedback if it exists, or if this is the latest message
    // Only hide if it's not latest AND no feedback exists
    if (!isLatestMessage && !existingFeedback) {
        return null;
    }

    const handleRatingClick = async (newRating: "thumbs_up" | "thumbs_down") => {
        // If already submitted and clicking same rating, do nothing
        if (isSubmitted && rating === newRating) {
            return;
        }

        setRating(newRating);
        
        // Show comment input for thumbs down
        if (newRating === "thumbs_down") {
            setShowCommentInput(true);
        } else {
            setShowCommentInput(false);
        }

        // Auto-submit for thumbs up, or if thumbs down with existing comment
        if (newRating === "thumbs_up" || (newRating === "thumbs_down" && comment.trim())) {
            await submitFeedback(newRating, comment);
        }
    };

    const handleCommentSubmit = async () => {
        if (rating && comment.trim()) {
            await submitFeedback(rating, comment);
        }
    };

    const submitFeedback = async (feedbackRating: "thumbs_up" | "thumbs_down", feedbackComment: string) => {
        setIsSubmitting(true);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/feedback/submit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    memory_event_id: memoryEventId,
                    user_id: userId,
                    rating: feedbackRating,
                    comment: feedbackComment.trim() || null
                })
            });

            if (!response.ok) {
                throw new Error("Failed to submit feedback");
            }

            const result = await response.json();
            
            // Update state to reflect submitted feedback
            setIsSubmitted(true);
            setShowCommentInput(false);
            
            // Update comment state with the submitted value
            setComment(feedbackComment.trim() || "");
            
            console.log("Feedback submitted successfully:", result);
            
            // Notify parent to refresh feedback
            if (onFeedbackSubmitted) {
                onFeedbackSubmitted();
            }
        } catch (error) {
            console.error("Error submitting feedback:", error);
            // Reset rating on error
            setRating(existingFeedback?.rating || null);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="mt-3 flex flex-col gap-2">
            {/* Thumbs Up/Down Buttons */}
            <div className="flex items-center gap-2">
                <button
                    onClick={() => handleRatingClick("thumbs_up")}
                    disabled={isSubmitting || isReadOnly}
                    className={`
                        p-1.5 rounded-md transition-all
                        ${rating === "thumbs_up"
                            ? "bg-green-100 text-green-700 hover:bg-green-200"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }
                        ${isSubmitting || isReadOnly ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                    `}
                    title={isReadOnly ? "Feedback already submitted" : "Helpful"}
                >
                    <ThumbsUp size={16} />
                </button>
                <button
                    onClick={() => handleRatingClick("thumbs_down")}
                    disabled={isSubmitting || isReadOnly}
                    className={`
                        p-1.5 rounded-md transition-all
                        ${rating === "thumbs_down"
                            ? "bg-red-100 text-red-700 hover:bg-red-200"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        }
                        ${isSubmitting || isReadOnly ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                    `}
                    title={isReadOnly ? "Feedback already submitted" : "Not helpful"}
                >
                    <ThumbsDown size={16} />
                </button>
            </div>

            {/* Comment Input (only for thumbs down, only on latest message, not read-only) */}
            {showCommentInput && isLatestMessage && !isReadOnly && (
                <form 
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleCommentSubmit();
                    }}
                    className="flex flex-col gap-2"
                >
                    <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        onKeyDown={(e) => {
                            // Submit on Enter (but allow Shift+Enter for new lines)
                            if (e.key === "Enter" && !e.shiftKey && comment.trim()) {
                                e.preventDefault();
                                handleCommentSubmit();
                            }
                        }}
                        placeholder="Why was this not helpful? (optional)"
                        className="
                            w-full px-3 py-2 text-sm border border-gray-300 rounded-md
                            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                            resize-none
                        "
                        rows={2}
                        disabled={isSubmitting || isSubmitted}
                    />
                    {!isSubmitted && (
                        <button
                            type="submit"
                            disabled={isSubmitting || !comment.trim()}
                            className="
                                self-start px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-md
                                hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                                transition-colors
                            "
                        >
                            {isSubmitting ? "Submitting..." : "Submit Feedback"}
                        </button>
                    )}
                </form>
            )}

            {/* Show submitted feedback confirmation */}
            {isSubmitted && (
                <div className="text-xs text-gray-600 mt-1">
                    <span className="font-medium text-green-600">✓ Feedback submitted</span>
                    {comment && (
                        <div className="italic mt-1">
                            Your comment: "{comment}"
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

