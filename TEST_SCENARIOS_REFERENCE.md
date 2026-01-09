# Test Scenarios Reference

This document lists all available test scenarios for the Eligibility Agent V2. These scenarios are **deterministic** - the same MRN will always return the same data regardless of whether accessed from Spectacles, Portal, or any other interface.

## How It Works

Test scenarios are configured in `nexus/tools/eligibility/test_scenarios.py`. The `PatientSimulator` and `Eligibility270TransactionTool` check for test scenarios and override default behavior accordingly.

## Available Test Scenarios

### Eligibility Failure Scenarios

| MRN | Scenario | Description |
|-----|----------|-------------|
| **MRN200** | NO_ACTIVE_WINDOW | No active coverage window, but has demographics, insurance, and visits |
| **MRN201** | NO_ACTIVE_WINDOW + no visits | No active coverage window, no visits |
| **MRN202** | EXPIRED | Coverage expired (past end date) |
| **MRN203** | FUTURE | Coverage starts in future (not yet effective) |

### Missing Data Scenarios

| MRN | Scenario | Description |
|-----|----------|-------------|
| **MRN204** | Missing demographics | No demographics data |
| **MRN205** | Partial demographics | Missing DOB |
| **MRN206** | Partial demographics | Missing first/last name |
| **MRN207** | Missing insurance | No insurance data |
| **MRN208** | Partial insurance | Missing plan_name |
| **MRN209** | Partial insurance | Missing payer_name |
| **MRN210** | No visits | No visit/appointment data |

### Combined Failure Scenarios

| MRN | Scenario | Description |
|-----|----------|-------------|
| **MRN211** | Multiple failures | NO_ACTIVE_WINDOW + partial demographics + partial insurance + no visits |
| **MRN212** | NO + missing demographics | NO_ACTIVE_WINDOW + no demographics |
| **MRN213** | NO + missing insurance | NO_ACTIVE_WINDOW + no insurance |
| **MRN214** | Expired + no visits | EXPIRED + no visits |
| **MRN215** | Future + partial data | FUTURE + partial demographics + partial insurance |

## Usage

Simply use the MRN in any eligibility check:

```
Check eligibility for MRN200
Check eligibility for MRN204
Check eligibility for MRN207
```

## Deterministic Behavior

All test scenarios are **deterministic**:
- Same MRN = Same data every time
- Works from Spectacles, Portal, or any interface
- Test scenarios override default synthetic data generation

## Adding New Test Scenarios

To add a new test scenario, edit `nexus/tools/eligibility/test_scenarios.py`:

```python
"MRN999": {
    "eligibility_result": "NO_ACTIVE_WINDOW",  # or "ACTIVE", "EXPIRED", "FUTURE"
    "demographics": "FULL",  # or "NONE", "PARTIAL", "PARTIAL_NAME"
    "insurance": "FULL",  # or "NONE", "PARTIAL", "PARTIAL_PAYER"
    "visits": "FULL"  # or "NONE"
}
```

## Testing

Run the test script to verify all scenarios:

```bash
python test_all_failure_scenarios.py
```

This will:
1. Test all scenarios
2. Verify expected results
3. Test determinism (same MRN = same data across multiple calls)
