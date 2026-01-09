"""
Propensity Repository

Queries propensity data and computes volatility metrics.
Implements waterfall/backoff strategy.
"""
import logging
from typing import Optional, Dict, Any, List
from nexus.modules.database import database

logger = logging.getLogger("nexus.eligibility_v2.propensity_repository")


class PropensityRepository:
    """Repository for propensity data queries"""
    
    async def get_propensity_with_volatility(
        self,
        product_type: Optional[str] = None,
        contract_status: Optional[str] = None,
        event_tense: Optional[str] = None,
        payer_id: Optional[str] = None,
        sex: Optional[str] = None,
        age_bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get propensity with volatility using waterfall/backoff strategy"""
        # Use waterfall strategy
        result = await self.get_best_propensity_with_backoff(
            product_type=product_type,
            contract_status=contract_status,
            event_tense=event_tense,
            payer_id=payer_id,
            sex=sex,
            age_bucket=age_bucket
        )
        
        return {
            "probability": result.get("probability", 0.5),
            "combined_confidence": result.get("combined_confidence", 0.5),
            "sample_size": result.get("sample_size", 0),
            "backoff_level": result.get("backoff_level"),
            "backoff_dims": result.get("backoff_dims", []),
            "backoff_path": result.get("backoff_path", []),
            "probability_interval": result.get("probability_interval"),
            "volatility": result.get("volatility"),
            "sample_confidence": result.get("sample_confidence")
        }
    
    async def get_best_propensity_with_backoff(
        self,
        product_type: Optional[str] = None,
        contract_status: Optional[str] = None,
        event_tense: Optional[str] = None,
        payer_id: Optional[str] = None,
        sex: Optional[str] = None,
        age_bucket: Optional[str] = None,
        min_n: int = 20
    ) -> Dict[str, Any]:
        """Get best propensity using waterfall/backoff strategy"""
        # Build list of known dimensions
        known_dims = {}
        if payer_id:
            known_dims["payer_id"] = payer_id
        if product_type:
            known_dims["product_type"] = product_type
        if contract_status:
            known_dims["contract_status"] = contract_status
        if event_tense:
            known_dims["event_tense"] = event_tense
        if sex:
            known_dims["sex"] = sex
        if age_bucket:
            known_dims["age_bucket"] = age_bucket
        
        logger.info(f"🌊 PROPENSITY WATERFALL: Starting with {len(known_dims)} known dimensions: {list(known_dims.keys())}")
        
        # Try different levels of specificity
        candidates = []
        
        # Level 0: Global average
        global_result = await self._query_transactions_propensity({})
        if global_result:
            candidates.append({
                "level": 0,
                "dims": [],
                **global_result
            })
        
        # Try combinations (simplified for now - full implementation would try all combinations)
        if known_dims:
            # Try with all known dims
            result = await self._query_transactions_propensity(known_dims)
            if result:
                candidates.append({
                    "level": len(known_dims),
                    "dims": list(known_dims.keys()),
                    **result
                })
        
        # Select best candidate
        if candidates:
            # Prefer higher level (more specific) if confidence is reasonable
            best = max(candidates, key=lambda x: (
                x.get("combined_confidence", 0) if x.get("combined_confidence", 0) > 0.2 else 0,
                x.get("level", 0),
                x.get("sample_size", 0)
            ))
            return best
        
        # Fallback
        return {
            "probability": 0.5,
            "combined_confidence": 0.5,
            "sample_size": 0,
            "backoff_level": 0,
            "backoff_dims": [],
            "backoff_path": []
        }
    
    async def _query_transactions_propensity(self, dims: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Query transactions for propensity with given dimensions"""
        # Build WHERE clause
        conditions = []
        values = {}
        
        for key, value in dims.items():
            if value:
                conditions.append(f"{key} = :{key}")
                values[key] = value
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT 
                COUNT(*) as n,
                AVG(CASE WHEN eligibility_status = 'YES' THEN 1.0 ELSE 0.0 END) as probability
            FROM eligibility_transactions
            WHERE {where_clause}
        """
        
        try:
            row = await database.fetch_one(query=query, values=values)
            if row and row.get("n", 0) > 0:
                n = row["n"]
                prob = float(row["probability"] or 0.5)
                
                # Compute CI (simplified)
                ci_width = 0.1  # Simplified
                combined_confidence = min(0.95, n / 100.0)  # Simplified
                
                return {
                    "probability": prob,
                    "sample_size": n,
                    "ci_width": ci_width,
                    "combined_confidence": combined_confidence
                }
        except Exception as e:
            logger.warning(f"Failed to query transactions: {e}")
        
        return None
