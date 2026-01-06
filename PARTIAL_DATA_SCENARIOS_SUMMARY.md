# Partial Data Availability - Summary

## Answer: Yes, the module handles realistic partial data scenarios

The `UserProfileManager` module **does a good job** of creating patients with partial data availability across different systems. It supports 9 predefined scenarios that simulate real-world healthcare data fragmentation.

## Supported Scenarios

### 1. **Standard** - All Views Available
- **Views:** EMR, System, Health Plan
- **Real-World:** Complete patient record, all systems synced
- **Example:** John Doe (TEST001)

### 2. **No Insurance** - EMR + System, No Insurance
- **Views:** EMR, System
- **Real-World:** Patient has been treated (EMR records) but is uninsured or insurance enrollment failed
- **Example:** Emily Davis (TEST006)
- **Use Case:** Testing eligibility workflows when patient has clinical history but no insurance

### 3. **EMR Only** - Not Integrated
- **Views:** EMR only
- **Real-World:** Patient exists only in legacy EMR system, not integrated with other systems
- **Example:** David Miller (TEST007)
- **Use Case:** Testing with legacy system data, hospital-only records

### 4. **Insurance Only** - New Patient
- **Views:** Health Plan only
- **Real-World:** Patient just enrolled in insurance but hasn't had medical visits yet
- **Example:** Jessica Garcia (TEST008)
- **Use Case:** Pre-visit eligibility verification, new enrollment

### 5. **Missing System** - EMR + Insurance, System Not Synced
- **Views:** EMR, Health Plan
- **Real-World:** EMR and insurance are synced, but system/demographics data not updated
- **Example:** William Taylor (TEST009)
- **Use Case:** System integration lag, data sync issues

### 6. **Missing EMR** - System + Insurance, No Clinical Records
- **Views:** System, Health Plan
- **Real-World:** Patient is registered and has insurance, but never visited (no EMR records)
- **Example:** Amanda Martinez (TEST010)
- **Use Case:** New patient registration, pre-visit eligibility check

### 7. **System Only** - Demographics Only
- **Views:** System only
- **Real-World:** Patient registered in system but no clinical or insurance data
- **Example:** Christopher Lee (TEST011)
- **Use Case:** Registration only, no visits, no insurance on file

### 8. **EMR and Insurance** - System Missing
- **Views:** EMR, Health Plan
- **Real-World:** Has EMR and insurance, but system integration missing
- **Example:** Jennifer White (TEST012)
- **Use Case:** Clinical and insurance systems connected, demographics system not integrated

## How It Works

### Generation with Scenarios

```python
# Patient with EMR but no insurance (realistic scenario)
profile = await user_profile_manager.generate_synthetic_patient(
    patient_id="UNINSURED001",
    name="Uninsured Patient",
    seed_data={"scenario": "no_insurance"}  # Only generates EMR + System
)
```

### What Gets Generated

- **Available views:** Full data generated (e.g., EMR gets diagnoses, medications, visits, labs, procedures)
- **Unavailable views:** Empty dict `{}` stored, availability flag set to `False`
- **API behavior:** Unavailable views return 404 when accessed individually

### Example: Patient in EMR but Not in Insurance

```bash
# Generate patient with no insurance
curl -X POST http://localhost:8000/api/user-profiles/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Emily Davis",
    "seed_data": {"scenario": "no_insurance"}
  }'

# EMR view available
curl http://localhost:8000/api/user-profiles/TEST006/emr
→ 200 OK with full EMR data (diagnoses, medications, visits, etc.)

# System view available
curl http://localhost:8000/api/user-profiles/TEST006/system
→ 200 OK with demographics, preferences, local_ids

# Health plan view unavailable
curl http://localhost:8000/api/user-profiles/TEST006/health-plan
→ 404 Not Found (patient not enrolled in insurance)
```

## Bounded Plan Handling

The bounded plan flow handles partial data gracefully:

1. **Searches for patient** → Finds patient (even if some views unavailable)
2. **Fetches all views** → Some return 200, some return 404
3. **Merges available data** → Only includes data from available views
4. **Populates known_fields** → Uses whatever data is available
5. **Continues workflow** → Works with partial data, may ask for missing info if needed

**Example Logs for "no_insurance" scenario:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id=TEST006
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys=['diagnoses', 'medications', 'allergies', 'visits', 'labs', 'procedures']
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | keys=['demographics', 'preferences', 'local_ids', 'registration']
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_UNAVAILABLE | status=404
[BoundedPlanBrain._fetch_patient_profile] DATA_MERGED | views=['emr', 'system'], extracted_fields=['patient_id', 'patient_name', 'date_of_birth', ...]
[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added=8, total_fields=9
```

## Test Patients with Partial Data

After running `python nexus/scripts/seed_test_patients.py`, you get:

| Patient | Scenario | Available Views | Missing Views |
|---------|----------|----------------|---------------|
| TEST006 | no_insurance | EMR, System | Health Plan |
| TEST007 | emr_only | EMR | System, Health Plan |
| TEST008 | insurance_only | Health Plan | EMR, System |
| TEST009 | missing_system | EMR, Health Plan | System |
| TEST010 | missing_emr | System, Health Plan | EMR |
| TEST011 | system_only | System | EMR, Health Plan |
| TEST012 | emr_and_insurance | EMR, Health Plan | System |

## Benefits

✅ **Realistic Testing:** Simulates real-world data fragmentation  
✅ **Graceful Degradation:** System handles partial data without errors  
✅ **Flexible Scenarios:** Easy to create custom scenarios  
✅ **Deterministic:** Same scenario + name = same data every time  
✅ **Comprehensive Coverage:** Tests all combinations of view availability  
✅ **Real-World Mapping:** Each scenario maps to actual healthcare data situations

## Summary

**Yes, the module does an excellent job** of creating patients with partial data availability. It supports:

- ✅ Patients in EMR but not in insurance (`no_insurance`)
- ✅ Patients only in EMR system (`emr_only`)
- ✅ Patients with insurance but no EMR (`insurance_only`)
- ✅ Patients with EMR and insurance but missing system data (`missing_system`)
- ✅ And 4 more realistic scenarios

All scenarios are handled gracefully by the bounded plan flow, which merges available data and continues with whatever information is available.




