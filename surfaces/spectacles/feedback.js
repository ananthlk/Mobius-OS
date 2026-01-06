/**
 * Möbius Spectacles - Feedback Capture Module
 * Reusable feedback capture for chat messages
 */

class FeedbackCapture {
    constructor(container, memoryEventId, userId, isLatestMessage, existingFeedback = null) {
        this.container = container;
        this.memoryEventId = memoryEventId;
        this.userId = userId;
        this.isLatestMessage = isLatestMessage;
        this.existingFeedback = existingFeedback;
        this.rating = existingFeedback?.rating || null;
        this.comment = existingFeedback?.comment || "";
        this.showCommentInput = existingFeedback?.rating === "thumbs_down" && !existingFeedback?.comment;
        this.isSubmitting = false;
        this.isSubmitted = !!existingFeedback;
        
        // Hide if not latest and no existing feedback
        if (!isLatestMessage && !existingFeedback) {
            return;
        }
        
        this.render();
    }
    
    render() {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-capture';
        feedbackDiv.style.cssText = 'margin-top: 12px; display: flex; flex-direction: column; gap: 8px;';
        
        // Thumbs buttons
        const buttonsDiv = document.createElement('div');
        buttonsDiv.style.cssText = 'display: flex; align-items: center; gap: 8px;';
        
        // Thumbs Up
        const thumbsUpBtn = document.createElement('button');
        thumbsUpBtn.innerHTML = '👍';
        thumbsUpBtn.className = 'feedback-btn thumbs-up';
        thumbsUpBtn.style.cssText = `
            padding: 6px;
            border-radius: 6px;
            border: none;
            background: ${this.rating === "thumbs_up" ? "#d1fae5" : "#f3f4f6"};
            color: ${this.rating === "thumbs_up" ? "#065f46" : "#6b7280"};
            cursor: ${this.isSubmitting || (!this.isLatestMessage && !this.existingFeedback) ? "not-allowed" : "pointer"};
            opacity: ${this.isSubmitting || (!this.isLatestMessage && !this.existingFeedback) ? "0.5" : "1"};
            transition: all 0.2s;
        `;
        thumbsUpBtn.title = "Helpful";
        thumbsUpBtn.onclick = () => this.handleRatingClick("thumbs_up");
        if (this.isSubmitting || (!this.isLatestMessage && !this.existingFeedback)) {
            thumbsUpBtn.disabled = true;
        }
        
        // Thumbs Down
        const thumbsDownBtn = document.createElement('button');
        thumbsDownBtn.innerHTML = '👎';
        thumbsDownBtn.className = 'feedback-btn thumbs-down';
        thumbsDownBtn.style.cssText = `
            padding: 6px;
            border-radius: 6px;
            border: none;
            background: ${this.rating === "thumbs_down" ? "#fee2e2" : "#f3f4f6"};
            color: ${this.rating === "thumbs_down" ? "#991b1b" : "#6b7280"};
            cursor: ${this.isSubmitting || (!this.isLatestMessage && !this.existingFeedback) ? "not-allowed" : "pointer"};
            opacity: ${this.isSubmitting || (!this.isLatestMessage && !this.existingFeedback) ? "0.5" : "1"};
            transition: all 0.2s;
        `;
        thumbsDownBtn.title = "Not helpful";
        thumbsDownBtn.onclick = () => this.handleRatingClick("thumbs_down");
        if (this.isSubmitting || (!this.isLatestMessage && !this.existingFeedback)) {
            thumbsDownBtn.disabled = true;
        }
        
        buttonsDiv.appendChild(thumbsUpBtn);
        buttonsDiv.appendChild(thumbsDownBtn);
        feedbackDiv.appendChild(buttonsDiv);
        
        // Comment input (only for thumbs down, only on latest message)
        if (this.showCommentInput && this.isLatestMessage) {
            const commentDiv = document.createElement('div');
            commentDiv.style.cssText = 'display: flex; flex-direction: column; gap: 8px;';
            
            const textarea = document.createElement('textarea');
            textarea.value = this.comment;
            textarea.placeholder = "Why was this not helpful? (optional)";
            textarea.style.cssText = `
                width: 100%;
                padding: 8px;
                font-size: 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                resize: none;
                font-family: inherit;
            `;
            textarea.rows = 2;
            textarea.disabled = this.isSubmitting || this.isSubmitted;
            textarea.oninput = (e) => {
                this.comment = e.target.value;
            };
            
            if (!this.isSubmitted) {
                const submitBtn = document.createElement('button');
                submitBtn.textContent = this.isSubmitting ? "Submitting..." : "Submit Feedback";
                submitBtn.style.cssText = `
                    align-self: flex-start;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 500;
                    color: white;
                    background: #2563eb;
                    border: none;
                    border-radius: 6px;
                    cursor: ${this.isSubmitting || !this.comment.trim() ? "not-allowed" : "pointer"};
                    opacity: ${this.isSubmitting || !this.comment.trim() ? "0.5" : "1"};
                `;
                submitBtn.disabled = this.isSubmitting || !this.comment.trim();
                submitBtn.onclick = () => this.handleCommentSubmit();
                
                commentDiv.appendChild(textarea);
                commentDiv.appendChild(submitBtn);
            } else {
                commentDiv.appendChild(textarea);
                textarea.disabled = true;
            }
            
            feedbackDiv.appendChild(commentDiv);
        }
        
        // Show existing comment if feedback was already submitted
        if (this.isSubmitted && this.existingFeedback?.comment) {
            const commentDisplay = document.createElement('div');
            commentDisplay.textContent = `Your feedback: "${this.existingFeedback.comment}"`;
            commentDisplay.style.cssText = 'font-size: 11px; color: #6b7280; font-style: italic; margin-top: 4px;';
            feedbackDiv.appendChild(commentDisplay);
        }
        
        this.container.appendChild(feedbackDiv);
        this.feedbackDiv = feedbackDiv;
    }
    
    async handleRatingClick(newRating) {
        // If already submitted and clicking same rating, do nothing
        if (this.isSubmitted && this.rating === newRating) {
            return;
        }
        
        this.rating = newRating;
        
        // Show comment input for thumbs down
        if (newRating === "thumbs_down") {
            this.showCommentInput = true;
            this.render(); // Re-render to show comment input
        } else {
            this.showCommentInput = false;
        }
        
        // Auto-submit for thumbs up, or if thumbs down with existing comment
        if (newRating === "thumbs_up" || (newRating === "thumbs_down" && this.comment.trim())) {
            await this.submitFeedback(newRating, this.comment);
        }
    }
    
    async handleCommentSubmit() {
        if (this.rating && this.comment.trim()) {
            await this.submitFeedback(this.rating, this.comment);
        }
    }
    
    async submitFeedback(feedbackRating, feedbackComment) {
        this.isSubmitting = true;
        this.render(); // Re-render to show loading state
        
        try {
            const apiUrl = "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/feedback/submit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    memory_event_id: this.memoryEventId,
                    user_id: this.userId,
                    rating: feedbackRating,
                    comment: feedbackComment.trim() || null
                })
            });
            
            if (!response.ok) {
                throw new Error("Failed to submit feedback");
            }
            
            this.isSubmitted = true;
            this.existingFeedback = {
                rating: feedbackRating,
                comment: feedbackComment.trim() || null
            };
            this.render(); // Re-render to show submitted state
        } catch (error) {
            console.error("Error submitting feedback:", error);
            // Reset rating on error
            this.rating = this.existingFeedback?.rating || null;
            this.render();
        } finally {
            this.isSubmitting = false;
        }
    }
    
    destroy() {
        if (this.feedbackDiv && this.feedbackDiv.parentNode) {
            this.feedbackDiv.parentNode.removeChild(this.feedbackDiv);
        }
    }
}

// Export for use in sidepanel.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FeedbackCapture;
}




