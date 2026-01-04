# Test Patients Reference

## Overview

The patient profile system uses **dynamic generation** - patients are created on-demand when you provide a name or ID. However, for consistent testing, you can seed a set of pre-defined test patients.

## How Patient Generation Works

### Dynamic Generation (Default Behavior)

When you provide a patient name or ID that doesn't exist:
1. The system automatically generates a synthetic patient profile
2. Generation is **deterministic** - same name/ID always produces same data
3. Patient is stored in the `user_profiles` table for future use

**Example:**
```bash
# First time: "John Doe" doesn't exist, so it's generated
# Subsequent times: "John Doe" is retrieved from database
```

### Pre-Seeded Test Patients

For consistent testing, you can seed a set of known test patients:

```bash
python nexus/scripts/seed_test_patients.py
```

This creates 8 test patients with known IDs and names.

---

## Pre-Seeded Test Patients

After running the seed script, these patients will be available with **realistic partial data scenarios**:

| Patient ID | Name | Scenario | Views Available | Real-World Use Case |
|------------|------|----------|-----------------|---------------------|
| **TEST001** | John Doe | standard | EMR, System, Health Plan | Complete patient record - all systems synced |
| **TEST002** | Jane Smith | standard | EMR, System, Health Plan | Complete patient record - all systems synced |
| **TEST003** | Michael Johnson | standard | EMR, System, Health Plan | Complete patient record - all systems synced |
| **TEST004** | Sarah Williams | standard | EMR, System, Health Plan | Complete patient record - all systems synced |
| **TEST005** | Robert Brown | standard | EMR, System, Health Plan | Complete patient record - all systems synced |
| **TEST006** | Emily Davis | no_insurance | EMR, System | **Patient exists in EMR but not enrolled in insurance** |
| **TEST007** | David Miller | emr_only | EMR only | **Patient only in EMR system (not integrated with other systems)** |
| **TEST008** | Jessica Garcia | insurance_only | Health Plan only | **New patient - just enrolled, no EMR records yet** |
| **TEST009** | William Taylor | missing_system | EMR, Health Plan | **EMR and insurance synced, but system data not updated** |
| **TEST010** | Amanda Martinez | missing_emr | System, Health Plan | **Registered patient but never visited (no EMR)** |
| **TEST011** | Christopher Lee | system_only | System only | **Demographics only - no clinical or insurance data** |
| **TEST012** | Jennifer White | emr_and_insurance | EMR, Health Plan | **Has EMR and insurance, but system integration missing** |

---

## Testing Scenarios

### Scenario 1: Standard Patient (All Views Available)

**Test Patient:** John Doe (TEST001)

**What to do:**
1. Start eligibility check workflow
2. When asked for patient name, type: **"John Doe"**
3. System will:
   - Search for "John Doe"
   - Find TEST001
   - Fetch all 3 views (EMR, System, Health Plan)
   - Populate `known_fields` with all data
   - Continue with enriched data

**Expected Logs:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id=TEST001
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys=[...]
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | keys=[...]
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_RETRIEVED | keys=[...]
[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added=11, total_fields=12
```

---

### Scenario 2: Patient Exists in EMR but Not in Insurance (Realistic)

**Test Patient:** Emily Davis (TEST006) - `no_insurance` scenario

**What to do:**
1. Start eligibility check workflow
2. When asked for patient name, type: **"Emily Davis"**
3. System will:
   - Search for "Emily Davis"
   - Find TEST006
   - Fetch EMR view successfully (patient has clinical records)
   - Fetch System view successfully (demographics available)
   - Try to fetch Health Plan view → **404 (unavailable - not enrolled)**
   - Populate `known_fields` with available data (EMR + System)
   - Continue (gracefully handles missing insurance data)

**Expected Logs:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id=TEST006
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys=['diagnoses', 'medications', 'allergies', 'visits', 'labs', 'procedures']
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_RETRIEVED | keys=['demographics', 'preferences', 'local_ids', 'registration']
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_UNAVAILABLE | status=404
[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added=8, total_fields=9
```

**Real-World Scenario:** Patient has been treated (EMR records exist) but is uninsured or insurance enrollment failed.

---

### Scenario 3: Patient Only in EMR System (Not Integrated)

**Test Patient:** David Miller (TEST007) - `emr_only` scenario

**What to do:**
1. Start eligibility check workflow
2. When asked for patient name, type: **"David Miller"**
3. System will:
   - Search for "David Miller"
   - Find TEST007
   - Fetch EMR view successfully
   - Try to fetch System view → **404 (unavailable)**
   - Try to fetch Health Plan view → **404 (unavailable)**
   - Populate `known_fields` with EMR data only
   - Continue (system handles partial data gracefully)

**Expected Logs:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_FOUND | patient_id=TEST007
[BoundedPlanBrain._fetch_patient_profile] EMR_VIEW_RETRIEVED | keys=[...]
[BoundedPlanBrain._fetch_patient_profile] SYSTEM_VIEW_UNAVAILABLE | status=404
[BoundedPlanBrain._fetch_patient_profile] HEALTH_PLAN_VIEW_UNAVAILABLE | status=404
[BoundedPlanBrain.handle_user_message] PATIENT_PROFILE_LOADED | fields_added=6, total_fields=7
```

**Real-World Scenario:** Legacy EMR system not integrated with modern systems. Patient exists only in clinical records.

---

### Scenario 4: New Patient - Insurance Only (No EMR Yet)

**Test Patient:** Jessica Garcia (TEST008) - `insurance_only` scenario

**What to do:**
1. Start eligibility check workflow
2. When asked for patient name, type: **"Jessica Garcia"**
3. System will:
   - Search for "Jessica Garcia"
   - Find TEST008
   - Try to fetch EMR view → **404 (unavailable - never visited)**
   - Try to fetch System view → **404 (unavailable)**
   - Fetch Health Plan view successfully (just enrolled)
   - Populate `known_fields` with insurance data only

**Real-World Scenario:** Patient just enrolled in insurance but hasn't had any medical visits yet.

---

### Scenario 3: New Patient (Dynamic Generation)

**Test Patient:** Any name not in the database (e.g., "Alice Johnson")

**What to do:**
1. Start eligibility check workflow
2. When asked for patient name, type: **"Alice Johnson"**
3. System will:
   - Search for "Alice Johnson"
   - Not find in database
   - **Automatically generate** a new patient profile
   - Store in database with deterministic ID
   - Fetch all views (all available for new patients)
   - Populate `known_fields` with generated data

**Expected Logs:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_NOT_FOUND | no_results
# OR if you generate first:
[UserProfileManager.generate_synthetic_patient] ENTRY | name=Alice Johnson
[UserProfileManager.generate_synthetic_patient] PATIENT_ID_DETERMINED | patient_id=<hash>
[UserProfileManager.generate_synthetic_patient] PROFILE_STORED | patient_id=<hash>
```

---

## API Testing

### Search for Patient

```bash
# Search by name
curl "http://localhost:8000/api/user-profiles/search?name=John%20Doe"

# Response:
{
  "patients": [
    {
      "patient_id": "TEST001",
      "name": "John Doe",
      "dob": "1980-01-15",
      "demographics": {...}
    }
  ],
  "count": 1
}
```

### Get Full Profile

```bash
curl http://localhost:8000/api/user-profiles/TEST001

# Response includes all views:
{
  "patient_id": "TEST001",
  "emr_data": {...},
  "system_data": {...},
  "health_plan_data": {...},
  "availability_flags": {
    "emr": true,
    "system": true,
    "health_plan": true
  }
}
```

### Get Specific Views

```bash
# EMR view only
curl http://localhost:8000/api/user-profiles/TEST001/emr

# System view only
curl http://localhost:8000/api/user-profiles/TEST001/system

# Health plan view only
curl http://localhost:8000/api/user-profiles/TEST001/health-plan
```

### Generate New Patient

```bash
curl -X POST http://localhost:8000/api/user-profiles/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Patient Name",
    "patient_id": "CUSTOM001"
  }'
```

### Mark View as Unavailable (for testing)

```bash
curl -X POST http://localhost:8000/api/user-profiles/TEST001/unavailable \
  -H "Content-Type: application/json" \
  -d '{
    "view_type": "emr"
  }'
```

---

## Deterministic Generation Details

### How It Works

1. **By Name:** If you provide a name, the system:
   - Creates a deterministic patient_id from name hash: `hashlib.md5(name.lower()).hexdigest()[:12]`
   - Uses name hash as random seed for consistent data generation
   - Same name = same patient data every time

2. **By Patient ID:** If you provide a patient_id:
   - Uses that ID directly
   - Generates data deterministically based on ID

3. **Seed Data:** Optional seed_data parameter can customize generation:
   ```python
   await user_profile_manager.generate_synthetic_patient(
       patient_id="CUSTOM001",
       name="Custom Patient",
       seed_data={"scenario": "diabetic", "age": 65}
   )
   ```

### Example: Same Name = Same Data

```python
# First call
profile1 = await user_profile_manager.generate_synthetic_patient(name="John Doe")

# Second call (even if database is cleared)
profile2 = await user_profile_manager.generate_synthetic_patient(name="John Doe")

# profile1["patient_id"] == profile2["patient_id"]  # True (deterministic)
# profile1["system_data"]["demographics"]["dob"] == profile2["system_data"]["demographics"]["dob"]  # True
```

---

## Quick Test Checklist

- [ ] Run seed script: `python nexus/scripts/seed_test_patients.py`
- [ ] Test with "John Doe" (standard patient)
- [ ] Test with "Emily Davis" (missing EMR view)
- [ ] Test with new name "Alice Johnson" (dynamic generation)
- [ ] Verify logs show patient profile fetching
- [ ] Verify `known_fields` are populated in bounded_plan_state
- [ ] Verify plan becomes READY_FOR_COMPILATION after patient data loaded

---

## Troubleshooting

### Patient Not Found

**Error:**
```
[BoundedPlanBrain._fetch_patient_profile] PATIENT_NOT_FOUND | no_results
```

**Solution:**
1. Run seed script: `python nexus/scripts/seed_test_patients.py`
2. Or generate on-demand by providing a name (will auto-generate)

### View Unavailable

**Error:**
```
[user_profile_endpoints.get_patient_emr] EMR_UNAVAILABLE | patient_id=TEST006
```

**This is expected** for test patients TEST006, TEST007, TEST008. The system handles this gracefully and continues with available data.

### Database Not Ready

**Error:**
```
[UserProfileManager._store_patient_profile] ERROR | table 'user_profiles' does not exist
```

**Solution:**
Run migration 026:
```bash
curl http://localhost:8000/api/system/migrate
```

---

## Summary

- **Dynamic Generation:** Patients are created on-demand when you provide a name/ID
- **Deterministic:** Same name/ID always produces same patient data
- **Pre-Seeded:** Run `seed_test_patients.py` for consistent test patients
- **Test Patients:** 8 pre-defined patients (TEST001-TEST008) with various scenarios
- **API Available:** All CRUD operations via REST API endpoints

