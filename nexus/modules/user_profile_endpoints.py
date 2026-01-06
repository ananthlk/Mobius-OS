"""
User Profile API Endpoints

REST API endpoints for querying synthetic patient profile data.
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from nexus.modules.user_profile_manager import user_profile_manager

logger = logging.getLogger("nexus.user_profile_endpoints")
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/api/user-profiles", tags=["user-profiles"])


# Request/Response Models

class GeneratePatientRequest(BaseModel):
    patient_id: Optional[str] = None
    name: Optional[str] = None
    seed_data: Optional[Dict[str, Any]] = None


class MarkUnavailableRequest(BaseModel):
    view_type: Optional[str] = None  # 'emr', 'system', 'health_plan', or None for all


# Endpoints

@router.get("/{patient_id}")
async def get_patient_profile(patient_id: str):
    """Get aggregated patient profile (all views merged)."""
    logger.debug(f"[user_profile_endpoints.get_patient_profile] ENTRY | patient_id={patient_id}")
    
    try:
        profile = await user_profile_manager.get_patient_profile(patient_id)
        
        if not profile:
            logger.debug(f"[user_profile_endpoints.get_patient_profile] PATIENT_NOT_FOUND | patient_id={patient_id}")
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        
        logger.debug(f"[user_profile_endpoints.get_patient_profile] EXIT | profile_retrieved, views={list(profile.keys())}")
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_profile_endpoints.get_patient_profile] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_patients(
    name: Optional[str] = Query(None, description="Patient name (partial match)"),
    dob: Optional[str] = Query(None, description="Date of birth (YYYY-MM-DD)"),
    patient_id: Optional[str] = Query(None, description="Exact patient ID")
):
    """Search patients by name, DOB, or patient_id."""
    logger.debug(f"[user_profile_endpoints.search_patients] ENTRY | name={name}, dob={dob}, patient_id={patient_id}")
    
    try:
        results = await user_profile_manager.search_patients(
            name=name,
            dob=dob,
            patient_id=patient_id
        )
        
        logger.debug(f"[user_profile_endpoints.search_patients] EXIT | results_count={len(results)}")
        return {"patients": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"[user_profile_endpoints.search_patients] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}/emr")
async def get_patient_emr(patient_id: str):
    """Get EMR view only (clinical data)."""
    logger.debug(f"[user_profile_endpoints.get_patient_emr] ENTRY | patient_id={patient_id}")
    
    try:
        emr_data = await user_profile_manager.get_patient_emr_view(patient_id)
        
        if not emr_data:
            logger.debug(f"[user_profile_endpoints.get_patient_emr] EMR_UNAVAILABLE | patient_id={patient_id}")
            raise HTTPException(status_code=404, detail=f"EMR data not available for patient '{patient_id}'")
        
        logger.debug(f"[user_profile_endpoints.get_patient_emr] EXIT | emr_data_keys={list(emr_data.keys())}")
        return emr_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_profile_endpoints.get_patient_emr] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}/system")
async def get_patient_system(patient_id: str):
    """Get system view only (demographics, local records)."""
    logger.debug(f"[user_profile_endpoints.get_patient_system] ENTRY | patient_id={patient_id}")
    
    try:
        system_data = await user_profile_manager.get_patient_system_view(patient_id)
        
        if not system_data:
            logger.debug(f"[user_profile_endpoints.get_patient_system] SYSTEM_UNAVAILABLE | patient_id={patient_id}")
            raise HTTPException(status_code=404, detail=f"System data not available for patient '{patient_id}'")
        
        logger.debug(f"[user_profile_endpoints.get_patient_system] EXIT | system_data_keys={list(system_data.keys())}")
        return system_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_profile_endpoints.get_patient_system] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}/health-plan")
async def get_patient_health_plan(patient_id: str):
    """Get health plan view only (insurance, coverage)."""
    logger.debug(f"[user_profile_endpoints.get_patient_health_plan] ENTRY | patient_id={patient_id}")
    
    try:
        health_plan_data = await user_profile_manager.get_patient_health_plan_view(patient_id)
        
        if not health_plan_data:
            logger.debug(f"[user_profile_endpoints.get_patient_health_plan] HEALTH_PLAN_UNAVAILABLE | patient_id={patient_id}")
            raise HTTPException(status_code=404, detail=f"Health plan data not available for patient '{patient_id}'")
        
        logger.debug(f"[user_profile_endpoints.get_patient_health_plan] EXIT | health_plan_data_keys={list(health_plan_data.keys())}")
        return health_plan_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[user_profile_endpoints.get_patient_health_plan] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", status_code=201)
async def generate_patient(request: GeneratePatientRequest):
    """Generate new synthetic patient record."""
    logger.debug(f"[user_profile_endpoints.generate_patient] ENTRY | patient_id={request.patient_id}, name={request.name}")
    
    try:
        profile = await user_profile_manager.generate_synthetic_patient(
            patient_id=request.patient_id,
            name=request.name,
            seed_data=request.seed_data
        )
        
        logger.debug(f"[user_profile_endpoints.generate_patient] EXIT | patient_id={profile.get('patient_id')}")
        return profile
        
    except Exception as e:
        logger.error(f"[user_profile_endpoints.generate_patient] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{patient_id}/unavailable")
async def mark_patient_unavailable(patient_id: str, request: MarkUnavailableRequest):
    """Mark views as unavailable (for testing)."""
    logger.debug(f"[user_profile_endpoints.mark_patient_unavailable] ENTRY | patient_id={patient_id}, view_type={request.view_type}")
    
    try:
        await user_profile_manager.mark_patient_unavailable(
            patient_id=patient_id,
            view_type=request.view_type
        )
        
        logger.debug(f"[user_profile_endpoints.mark_patient_unavailable] EXIT | marked_unavailable")
        return {"success": True, "patient_id": patient_id, "view_type": request.view_type}
        
    except Exception as e:
        logger.error(f"[user_profile_endpoints.mark_patient_unavailable] ERROR | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))




