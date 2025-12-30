from typing import Any, Dict, List
from nexus.core.base_tool import NexusTool, ToolSchema
import random

class RiskCalculatorTool(NexusTool):
    def define_schema(self) -> ToolSchema:
        return ToolSchema(
            name="risk_calculator",
            description="Analyzes a list of appointments and calculates risk scores.",
            parameters={
                "appointments": "List[Dict] (The appointments to analyze)"
            }
        )

    def run(self, appointments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates No-Show and Denial risks for each appointment.
        """
        analyzed_appointments = []
        total_risk_score = 0
        
        for appt in appointments:
            # Simulation Logic
            no_show_risk = 0.1
            denial_risk = 0.1
            flags = []
            actions = []

            # CRM Rule: New Patients have higher no-show risk
            if appt["type"] == "New Patient":
                no_show_risk += 0.2
                flags.append("High No-Show Risk (New Patient)")
                actions.append("Send SMS Confirmation")

            # Revenue Rule: Pending Auth has high denial risk
            if appt["insurance_status"] == "Pending Auth":
                denial_risk += 0.6
                flags.append("High Denial Risk (Auth Missing)")
                actions.append("Request Visualization")
            elif appt["insurance_status"] == "Unknown":
                denial_risk += 0.4
                flags.append("Eligibility Unchecked")
                actions.append("Run Eligibility Check")

            analyzed_appointments.append({
                **appt,
                "risk_scores": {
                    "no_show": round(no_show_risk, 2),
                    "denial": round(denial_risk, 2)
                },
                "flags": flags,
                "suggested_actions": actions
            })
            
            total_risk_score += (no_show_risk + denial_risk)

        return {
            "appointments": analyzed_appointments,
            "summary": {
                "total_appointments": len(appointments),
                "high_risk_count": len([a for a in analyzed_appointments if a["flags"]]),
                "overall_health_score": round(100 - (total_risk_score * 10), 0)
            }
        }
