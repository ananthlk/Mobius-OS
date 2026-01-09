# Partial Data Availability Scenarios

## Overview

The user profile manager supports **realistic partial data scenarios** where patients exist in some systems but not others. This simulates real-world healthcare data fragmentation.

## Supported Scenarios

### 1. Standard (All Views Available)
- **Scenario:** `standard`
- **Views:** EMR, System, Health Plan
- **Use Case:** Complete patient record - all systems synced
- **Example:** John Doe (TEST001)

### 2. No Insurance (EMR + System, No Insurance)
- **Scenario:** `no_insurance`
- **Views:** EMR, System
- **Use Case:** Patient has been treated (EMR records) but is uninsured or insurance enrollment failed
- **Example:** Emily Davis (TEST006)
- **Real-World:** Common for uninsured patients, Medicaid pending, or insurance termination

### 3. EMR Only (Not Integrated)
- **Scenario:** `emr_only`
- **Views:** EMR only
- **Use Case:** Patient exists only in legacy EMR system, not integrated with other systems
- **Example:** David Miller (TEST007)
- **Real-World:** Legacy systems, hospital-only records, not in central registry

### 4. Insurance Only (New Patient)
- **Scenario:** `insurance_only`
- **Views:** Health Plan only
- **Use Case:** Patient just enrolled in insurance but hasn't had medical visits yet
- **Example:** Jessica Garcia (TEST008)
- **Real-World:** New enrollment, pre-visit eligibility check

### 5. Missing System (EMR + Insurance, System Not Synced)
- **Scenario:** `missing_system`
- **Views:** EMR, Health Plan
- **Use Case:** EMR and insurance are synced, but system/demographics data not updated
- **Example:** William Taylor (TEST009)
- **Real-World:** System integration lag, data sync issues

### 6. Missing EMR (System + Insurance, No Clinical Records)
- **Scenario:** `missing_emr`
- **Views:** System, Health Plan
- **Use Case:** Patient is registered and has insurance, but never visited (no EMR records)
- **Example:** Amanda Martinez (TEST010)
- **Real-World:** New patient registration, pre-visit eligibility verification

### 7. System Only (Demographics Only)
- **Scenario:** `system_only`
- **Views:** System only
- **Use Case:** Patient registered in system but no clinical or insurance data
- **Example:** Christopher Lee (TEST011)
- **Real-World:** Registration only, no visits, no insurance on file

### 8. EMR and Insurance (System Missing)
- **Scenario:** `emr_and_insurance`
- **Views:** EMR, Health Plan
- **Use Case:** Has EMR and insurance, but system integration missing
- **Example:** Jennifer White (TEST012)
- **Real-World:** Clinical and insurance systems connected, but demographics system not integrated

## How It Works

### Generation with Scenarios

When generating a patient, you can specify a scenario:

```python
# Patient with EMR but no insurance
profile = await user_profile_manager.generate_synthetic_patient(
    patient_id="PAT001",
    name="John Doe",
    seed_data={"scenario": "no_insurance"}
)
```

### What Gets Generated

- **Available views:** Full data generated (e.g., EMR gets diagnoses, medications, visits, etc.)
- **Unavailable views:** Empty dict `{}` stored, availability flag set to `False`
- **System view:** Always has at least demographics (for search), but may be minimal if scenario is `system_only`

### API Behavior

When fetching views:

```bash
# EMR available
GET /api/user-profiles/TEST006/emr
→ 200 OK with full EMR data

# Health plan unavailable
GET /api/user-profiles/TEST006/health-plan
→ 404 Not Found (unavailable)

# System available
GET /api/user-profiles/TEST006/system
→ 200 OK with system data
```

### Bounded Plan Handling

The bounded plan flow handles partial data gracefully:

1. **Searches for patient** → Finds patient (even if some views unavailable)
2. **Fetches all views** → Some return 200, some return 404
3. **Merges available data** → Only includes data from available views
4. **Populates known_fields** → Uses whatever data is available
5. **Continues workflow** → Works with partial data, may ask for missing info if needed

**Example Logs:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id=TEST006
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys=[...]
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | keys=[...]
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_UNAVAILABLE | status=404
[BoundedPlanBrain._fetch_patient_profile] DATA_MERGED | views=['emr', 'system'], extracted_fields=[...]
```

## Testing Scenarios

### Test: Patient with EMR but No Insurance

```bash
# 1. Generate patient
curl -X POST http://localhost:8000/api/user-profiles/generate \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "UNINSURED001",
    "name": "Uninsured Patient",
    "seed_data": {"scenario": "no_insurance"}
  }'

# 2. Verify views
curl http://localhost:8000/api/user-profiles/UNINSURED001
# Response shows: emr_data and system_data populated, health_plan_data empty

# 3. Test individual views
curl http://localhost:8000/api/user-profiles/UNINSURED001/emr
# → 200 OK (has data)

curl http://localhost:8000/api/user-profiles/UNINSURED001/health-plan
# → 404 Not Found (unavailable)
```

### Test: EMR Only Patient

```bash
curl -X POST http://localhost:8000/api/user-profiles/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Legacy Patient",
    "seed_data": {"scenario": "emr_only"}
  }'

# Only EMR view will be available
# System and Health Plan will return 404
```

## Custom Scenarios

You can also specify exact views to generate:

```python
profile = await user_profile_manager.generate_synthetic_patient(
    name="Custom Patient",
    seed_data={
        "available_views": ["emr", "system"]  # Only generate these
    }
)
```

## Real-World Mapping

| Scenario | Real-World Example |
|----------|-------------------|
| `no_insurance` | Uninsured patient, Medicaid pending, insurance terminated |
| `emr_only` | Legacy hospital system, not in central registry |
| `insurance_only` | New enrollment, pre-visit eligibility check |
| `missing_system` | EMR/insurance synced, demographics system lag |
| `missing_emr` | Registered patient, never visited |
| `system_only` | Registration only, no clinical or insurance data |
| `emr_and_insurance` | Clinical and insurance connected, demographics missing |

## Benefits

1. **Realistic Testing:** Simulates real-world data fragmentation
2. **Graceful Degradation:** System handles partial data without errors
3. **Flexible Scenarios:** Easy to create custom scenarios for testing
4. **Deterministic:** Same scenario + name = same data every time
5. **Comprehensive Coverage:** Tests all combinations of view availability






