import logging
import json
from typing import List, Dict, Set
from collections import defaultdict
from nexus.modules.database import database, parse_jsonb

logger = logging.getLogger("nexus.trending_issues")

# Default fallback list if no recent searches found
DEFAULT_TRENDING_ISSUES = [
    "Compliance Audit",
    "User Onboarding",
    "Data Reconciliation",
    "Risk Assessment"
]


async def get_recent_searches(days: int = 7) -> List[str]:
    """
    Extracts user queries from shaping_sessions transcripts within the last N days.
    
    Args:
        days: Number of days to look back (default: 7)
    
    Returns:
        List of unique user query strings (normalized)
    """
    try:
        # Use string formatting for INTERVAL since PostgreSQL doesn't support parameter binding in INTERVAL literals
        query = f"""
            SELECT transcript, created_at
            FROM shaping_sessions
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            ORDER BY created_at DESC
        """
        
        rows = await database.fetch_all(query)
        
        user_queries: Set[str] = set()
        
        for row in rows:
            row_dict = dict(row)
            transcript = row_dict.get("transcript")
            
            # Parse transcript if it's a string
            if isinstance(transcript, str):
                try:
                    transcript = json.loads(transcript)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse transcript: {transcript}")
                    continue
            
            # Extract user messages from transcript
            if isinstance(transcript, list):
                for msg in transcript:
                    if not isinstance(msg, dict):
                        continue
                    
                    role = msg.get("role", "").lower()
                    content = msg.get("content", "")
                    
                    if role == "user" and content:
                        # Normalize: lowercase, strip whitespace
                        normalized = content.strip().lower()
                        if normalized and len(normalized) > 3:  # Filter out very short queries
                            user_queries.add(normalized)
        
        result = list(user_queries)
        logger.debug(f"Extracted {len(result)} unique user queries from last {days} days")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting recent searches: {e}", exc_info=True)
        return []


def calculate_semantic_similarity(query: str, candidate: str) -> float:
    """
    Calculates keyword-based semantic similarity between two queries.
    Similar to diagnosis.py._calculate_fit but for query-to-query comparison.
    
    Args:
        query: First query string
        candidate: Second query string to compare against
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not query or not candidate:
        return 0.0
    
    q_lower = query.lower().strip()
    c_lower = candidate.lower().strip()
    
    # Exact match boost
    if q_lower == c_lower:
        return 1.0
    
    # Check for exact phrase match (one contains the other)
    if q_lower in c_lower or c_lower in q_lower:
        return 0.9
    
    # Keyword-based matching
    q_keywords = set(q_lower.split())
    c_keywords = set(c_lower.split())
    
    # Remove common stop words (simple list)
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "can", "may", "might", "must"}
    q_keywords = {w for w in q_keywords if w not in stop_words and len(w) > 2}
    c_keywords = {w for w in c_keywords if w not in stop_words and len(w) > 2}
    
    if not q_keywords or not c_keywords:
        return 0.0
    
    # Calculate Jaccard similarity (intersection over union)
    intersection = len(q_keywords & c_keywords)
    union = len(q_keywords | c_keywords)
    
    if union == 0:
        return 0.0
    
    jaccard_score = intersection / union
    
    # Boost for significant keyword overlap
    if intersection >= min(len(q_keywords), len(c_keywords)) * 0.5:
        jaccard_score = min(1.0, jaccard_score * 1.2)
    
    return min(1.0, jaccard_score)


async def get_trending_issues(limit: int = 4, days: int = 7) -> List[str]:
    """
    Gets trending issues based on recent searches using semantic similarity.
    
    Algorithm:
    1. Get all recent user queries from last N days
    2. For each query, calculate similarity against all other queries
    3. Aggregate scores (sum similarities for each unique query)
    4. Sort by total score descending
    5. Return top N results
    
    Args:
        limit: Maximum number of trending issues to return (default: 4)
        days: Number of days to look back (default: 7)
    
    Returns:
        List of trending issue strings (top N by semantic similarity)
    """
    try:
        # Get recent searches
        recent_searches = await get_recent_searches(days=days)
        
        if not recent_searches:
            logger.info("No recent searches found, returning default trending issues")
            return DEFAULT_TRENDING_ISSUES[:limit]
        
        if len(recent_searches) == 1:
            # Only one search - return it (capitalized)
            return [recent_searches[0].title()][:limit]
        
        # Calculate similarity matrix and aggregate scores
        query_scores: Dict[str, float] = defaultdict(float)
        
        for i, query1 in enumerate(recent_searches):
            for j, query2 in enumerate(recent_searches):
                if i != j:  # Don't compare query to itself
                    similarity = calculate_semantic_similarity(query1, query2)
                    # Add similarity score to both queries
                    query_scores[query1] += similarity
                    query_scores[query2] += similarity
        
        # Sort by score descending
        sorted_queries = sorted(
            query_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Extract top N queries and format them
        trending = [q[0].title() for q in sorted_queries[:limit]]
        
        logger.info(f"Found {len(trending)} trending issues from {len(recent_searches)} recent searches")
        return trending
        
    except Exception as e:
        logger.error(f"Error getting trending issues: {e}", exc_info=True)
        # Fallback to default list
        return DEFAULT_TRENDING_ISSUES[:limit]

