-- Migration: 032_message_feedback
-- Purpose: Store user feedback (thumbs up/down) tied to memory events
-- Architecture: Feedback capture module for chat interactions

CREATE TABLE IF NOT EXISTS message_feedback (
    id SERIAL PRIMARY KEY,
    memory_event_id INTEGER NOT NULL REFERENCES memory_events(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('thumbs_up', 'thumbs_down')),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one feedback per user per memory event
    UNIQUE(memory_event_id, user_id)
);

-- Index for fast lookups by memory_event_id
CREATE INDEX IF NOT EXISTS idx_message_feedback_memory_event ON message_feedback(memory_event_id);

-- Index for user feedback history
CREATE INDEX IF NOT EXISTS idx_message_feedback_user_id ON message_feedback(user_id, created_at DESC);



