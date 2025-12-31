from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from nexus.core.base_agent import AgentRecipe
from nexus.workflows.registry import registry

@dataclass
class DiagnosisConfig:
    """
    Configuration for the Diagnosis Scoring Engine.
    Allows tuning of the heuristics without changing code.
    """
    DEFAULT_SUCCESS_PROB: float = 0.5
    LIKELIHOOD_DB_LOOKUP: float = 0.8  # High confidence we can get data from DB
    LIKELIHOOD_USER_INPUT: float = 0.4 # Friction to ask user
    MISSING_INFO_PENALTY_FACTOR: float = 1.0

@dataclass
class SolutionCandidate:
    recipe_name: str
    goal: str
    match_score: float
    missing_info: List[str]
    reasoning: str
    origin: str = "standard" # standard | ai | custom

class DiagnosisBrain:
    def __init__(self, config: DiagnosisConfig = DiagnosisConfig()):
        self.config = config

    async def diagnose(self, user_query: str) -> List[SolutionCandidate]:
        """
        Analyzes the user query and returns ranked recipes.
        """
        # 1. Fetch all active recipes
        # TODO: In future, use Vector Search to filter this list first
        all_recipe_names = await registry.list_recipes()
        candidates = []

        for name in all_recipe_names:
            recipe = await registry.get_recipe(name)
            if not recipe:
                continue
            
            # 2. Analyze Fit (Mock LLM Logic for V1)
            # We will use simple keyword overlap as a proxy for "Fit Score"
            fit_score, reasoning = self._calculate_fit(user_query, recipe)
            
            if fit_score < 0.1: # Threshold to filter out irrelevant stuff
                continue

            # 3. Calculate Executability (Missing Info)
            missing_info = self._identify_missing_info(recipe, user_query)
            
            # 4. Get Success Probability (Async check)
            success_prob = await self._get_success_probability(recipe.name, recipe.metadata)

            # 5. Calculate Final Score (Expected Value)
            final_score = self._calculate_score(fit_score, missing_info, success_prob)

            candidates.append(SolutionCandidate(
                recipe_name=recipe.name,
                goal=recipe.goal,
                match_score=round(final_score, 2),
                missing_info=missing_info,
                reasoning=reasoning,
                origin="standard"
            ))

        # 5. Rank
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        return candidates

    def _calculate_fit(self, query: str, recipe: AgentRecipe) -> (float, str):
        """
        Mock LLM: Heuristic keyword matching.
        """
        q_lower = query.lower()
        r_text = (recipe.name + " " + recipe.goal).lower()
        
        keywords = q_lower.split()
        matches = sum(1 for w in keywords if w in r_text)
        
        if len(keywords) == 0:
            return 0.0, "No query provided."

        ratio = matches / len(keywords)
        
        # Boost for exact name match
        if recipe.name.lower() in q_lower:
            ratio = 1.0
            
        reasoning = f"Matches {matches}/{len(keywords)} keywords from your request."
        if ratio > 0.8:
            reasoning = "High confidence match based on problem statement."
        elif ratio < 0.3:
            reasoning = "Low relevance, but loosely related."
            
        return ratio, reasoning

    def _identify_missing_info(self, recipe: AgentRecipe, query: str) -> List[str]:
        """
        Determines what context is needed vs what we likely have.
        """
        required_vars = set()
        for step in recipe.steps.values():
            for context_key in step.args_mapping.values():
                required_vars.add(context_key)

        # Mock: We assume we DON'T have them unless user typed them (very naive)
        # In reality, we'd check the active RequestContext
        missing = []
        for var in required_vars:
            # Heuristic: If it looks like a system ID (patient_id), it's missing
            # unless mentioned in query
            if var not in query: 
                missing.append(var)
        
        return missing

    async def _get_success_probability(self, recipe_name: str, recipe_metadata: Dict[str, Any]) -> float:
        """
        Calculates success probability based on:
        1. Historical execution data (Real-world evidence)
        2. Configured metadata (Heuristic baseline)
        3. Default fallback
        """
        # 1. Try Metadata first (fastest)
        heuristic = self.config.DEFAULT_SUCCESS_PROB
        if recipe_metadata:
            heuristic = recipe_metadata.get("success_probability", heuristic)

        # 2. Try DB (Real Evidence) - TODO: Move to ExecutionManager
        # query = "SELECT AVG(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) FROM workflow_executions WHERE recipe_id = (SELECT id FROM agent_recipes WHERE name = :name)"
        # This would be an async call. For now, we simulate mixing the two.
        
        # In a real impl, we'd fetch this. 
        # For the V1 refactor, we stick to the heuristic but prepared for DB injection.
        return heuristic

    def _calculate_score(self, fit_score: float, missing_info: List[str], success_prob: float) -> float:
        """
        Formula: Score = (Success Prob * Likelihood) / (1 + Missing Info)
        """
        # Estimate Likelihood
        if len(missing_info) > 0:
            likelihood = self.config.LIKELIHOOD_USER_INPUT
        else:
            likelihood = self.config.LIKELIHOOD_DB_LOOKUP

        # The core formula
        score = (success_prob * likelihood * fit_score) / (1 + (len(missing_info) * self.config.MISSING_INFO_PENALTY_FACTOR))
        
        return min(1.0, score)

