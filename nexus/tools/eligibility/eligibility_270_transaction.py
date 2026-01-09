"""
Eligibility 270 Transaction Tool

Simulates a 270 eligibility transaction to retrieve coverage status.
"""
import logging
from typing import Dict, Any, List
from datetime import date, datetime, timedelta
from nexus.core.base_tool import NexusTool, ToolSchema

logger = logging.getLogger("nexus.tools.eligibility.270_transaction")


class Eligibility270TransactionTool(NexusTool):
    """Tool for querying 270 eligibility transactions"""
    
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="eligibility_270_transaction",
            description="Query 270 eligibility transaction to retrieve coverage status",
            parameters={
                "insurance_id": "str",
                "insurance_name": "str"
            }
        )
    
    def run(self, insurance_id: str, insurance_name: str) -> Dict[str, Any]:
        """Synchronous run method"""
        import asyncio
        return asyncio.run(self.execute(insurance_id, insurance_name))
    
    async def execute(self, insurance_id: str, insurance_name: str) -> Dict[str, Any]:
        """Execute 270 eligibility transaction"""
        logger.debug(f"[Eligibility270TransactionTool.execute] ENTRY | insurance_id={insurance_id}, insurance_name={insurance_name}")
        
        # Generate eligibility windows
        windows = self._generate_eligibility_windows(insurance_id)
        
        logger.debug(f"[Eligibility270TransactionTool.execute] EXIT | windows_count={len(windows)}")
        
        return {
            "insurance_id": insurance_id,
            "insurance_name": insurance_name,
            "eligibility_windows": windows,
            "queried_at": datetime.now().isoformat()
        }
    
    def _generate_eligibility_windows(self, insurance_id: str) -> List[Dict[str, Any]]:
        """
        Generate mock eligibility windows.
        
        This method is deterministic: the same insurance_id will always return the same windows.
        Test scenarios can override default behavior for specific MRNs.
        """
        logger.debug(f"[Eligibility270TransactionTool._generate_eligibility_windows] ENTRY | insurance_id={insurance_id}")
        
        # Check for test scenario
        # Try direct lookup first, then try to extract MRN from member_id
        from nexus.tools.eligibility.test_scenarios import get_test_scenario
        test_scenario = get_test_scenario(insurance_id)
        
        # If not found, try to extract MRN from member_id (format: {mrn_number}123456789)
        if not test_scenario and insurance_id.endswith("123456789"):
            mrn_number = insurance_id[:-9]  # Remove "123456789" suffix
            if mrn_number.isdigit():
                test_scenario = get_test_scenario(f"MRN{mrn_number}")
        
        today = date.today()
        windows = []
        
        if test_scenario:
            scenario_type = test_scenario.get("eligibility_result", "ACTIVE")
            
            if scenario_type == "NO_ACTIVE_WINDOW":
                # Only inactive windows, no active
                prev_start = today - timedelta(days=500)
                prev_end = today - timedelta(days=200)
                windows.append({
                    "effective_date": prev_start.isoformat(),
                    "end_date": prev_end.isoformat(),
                    "status": "inactive",
                    "coverage_type": "medical",
                    "plan_name": f"{insurance_id} Old Plan",
                    "member_id": insurance_id
                })
                logger.debug(f"Test scenario: {insurance_id} - NO_ACTIVE_WINDOW (no active coverage)")
                return windows
            
            elif scenario_type == "EXPIRED":
                # Active window that expired in the past
                active_start = today - timedelta(days=400)
                active_end = today - timedelta(days=10)  # Expired 10 days ago
                windows.append({
                    "effective_date": active_start.isoformat(),
                    "end_date": active_end.isoformat(),
                    "status": "inactive",  # Expired, so inactive
                    "coverage_type": "medical",
                    "plan_name": f"{insurance_id} Expired Plan",
                    "member_id": insurance_id
                })
                logger.debug(f"Test scenario: {insurance_id} - EXPIRED (coverage expired)")
                return windows
            
            elif scenario_type == "FUTURE":
                # Coverage that starts in the future
                active_start = today + timedelta(days=30)  # Starts in 30 days
                active_end = today + timedelta(days=400)
                windows.append({
                    "effective_date": active_start.isoformat(),
                    "end_date": active_end.isoformat(),
                    "status": "inactive",  # Not yet active
                    "coverage_type": "medical",
                    "plan_name": f"{insurance_id} Future Plan",
                    "member_id": insurance_id
                })
                logger.debug(f"Test scenario: {insurance_id} - FUTURE (coverage not yet active)")
                return windows
        
        # Default: Active window (current coverage)
        # This is deterministic based on insurance_id hash
        active_start = today - timedelta(days=150)
        active_end = today + timedelta(days=200)
        windows.append({
            "effective_date": active_start.isoformat(),
            "end_date": active_end.isoformat(),
            "status": "active",
            "coverage_type": "medical",
            "plan_name": f"{insurance_id} Standard Plan",
            "member_id": insurance_id
        })
        
        # Previous window (inactive)
        prev_start = active_start - timedelta(days=365)
        prev_end = active_start - timedelta(days=1)
        windows.append({
            "effective_date": prev_start.isoformat(),
            "end_date": prev_end.isoformat(),
            "status": "inactive",
            "coverage_type": "medical",
            "plan_name": f"{insurance_id} Standard Plan",
            "member_id": insurance_id
        })
        
        logger.debug(f"[Eligibility270TransactionTool._generate_eligibility_windows] EXIT | windows_generated={len(windows)}")
        return windows
