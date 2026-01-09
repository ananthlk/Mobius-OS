# TimeFunction Unit Test Results

## Test Summary
**Status**: ✅ All 6 test suites passed (18 individual assertions)

## Test Cases

### 1. Retrospective Denial Linear Decrease (Primary Test)
Tests the linear decrease behavior for `retrospective_denial` risk over 60 days.

**Base Risk**: 15%

| Days Since DOS | Expected Formula | Expected Value | Actual Value | Status |
|----------------|-------------------|----------------|--------------|--------|
| 0 | `0.15 × (1 - 0/60) = 0.15` | 15.0% | 15.0% | ✅ |
| 15 | `0.15 × (1 - 15/60) = 0.15 × 0.75` | 11.2% | 11.2% | ✅ |
| 30 | `0.15 × (1 - 30/60) = 0.15 × 0.5` | 7.5% | 7.5% | ✅ |
| 45 | `0.15 × (1 - 45/60) = 0.15 × 0.25` | 3.8% | 3.8% | ✅ |
| 60 | `0.15 × (1 - 60/60) = 0.15 × 0` | 0.0% | 0.0% | ✅ |
| 90 | `0.0` (after 60 days) | 0.0% | 0.0% | ✅ |
| 120 | `0.0` (after 60 days) | 0.0% | 0.0% | ✅ |

**Result**: ✅ PASSED - Linear decrease works correctly, reaches 0 at day 60, stays 0 after.

---

### 2. Retrospective Denial Edge Cases
Tests edge cases near boundaries.

**Base Risk**: 20%

| Days Since DOS | Expected Formula | Expected Value | Actual Value | Status |
|----------------|-------------------|----------------|--------------|--------|
| 1 | `0.20 × (1 - 1/60) = 0.20 × 59/60` | 19.67% | 19.67% | ✅ |
| 59 | `0.20 × (1 - 59/60) = 0.20 × 1/60` | 0.33% | 0.33% | ✅ |
| 61 | `0.0` (after 60 days) | 0.0% | 0.0% | ✅ |

**Result**: ✅ PASSED - Edge cases handled correctly.

---

### 3. Coverage Loss Future Amplification
Tests exponential amplification for future events.

**Base Risk**: 10%

| Days Until DOS | Formula | Expected Value | Actual Value | Status |
|----------------|---------|----------------|--------------|--------|
| 0 | `0.10 × exp(0)` | 10.0% | 10.0% | ✅ |
| 30 | `0.10 × exp(0.001 × 30) ≈ 0.10 × 1.0305` | ~10.3% | 10.3% | ✅ |
| 60 | `0.10 × exp(0.001 × 60) ≈ 0.10 × 1.0618` | ~10.6% | 10.6% | ✅ |

**Result**: ✅ PASSED - Exponential amplification works correctly.

---

### 4. Payer Error Past Deterioration
Tests exponential deterioration for past events (non-retrospective risks).

**Base Risk**: 5%

| Days Since Visit | Formula | Expected Value | Actual Value | Status |
|------------------|---------|----------------|--------------|--------|
| 0 | `0.05 × exp(0)` | 5.0% | 5.0% | ✅ |
| 30 | `0.05 × exp(-0.001 × 30) ≈ 0.05 × 0.9704` | ~4.9% | 4.9% | ✅ |

**Result**: ✅ PASSED - Exponential deterioration works correctly.

---

### 5. Multiple Risks Mixed
Tests multiple risks with different behaviors simultaneously.

**Base Risks**:
- `retrospective_denial`: 15% (linear decrease)
- `payer_error`: 5% (exponential decrease)
- `provider_error`: 3% (exponential decrease)

**At Day 30 (Past Event)**:

| Risk Type | Expected Behavior | Expected Value | Actual Value | Status |
|-----------|-------------------|----------------|--------------|--------|
| retrospective_denial | Linear: `0.15 × (1 - 30/60)` | 7.5% | 7.5% | ✅ |
| payer_error | Exponential: `0.05 × exp(-0.001 × 30)` | ~4.9% | 4.9% | ✅ |
| provider_error | Exponential: `0.03 × exp(-0.001 × 30)` | ~2.9% | 2.9% | ✅ |

**Result**: ✅ PASSED - Multiple risks with different behaviors work correctly together.

---

### 6. Unknown Event Tense
Tests that UNKNOWN event tense doesn't adjust risks.

**Base Risk**: 10%

| Event Tense | Days | Expected | Actual | Status |
|-------------|------|----------|--------|--------|
| UNKNOWN | 30 | 10.0% (unchanged) | 10.0% | ✅ |

**Result**: ✅ PASSED - UNKNOWN event tense correctly leaves risks unchanged.

---

## Key Validations

1. ✅ **Linear Decrease**: Retrospective denial risk decreases linearly from base to 0 over 60 days
2. ✅ **Zero After 60 Days**: Risk becomes 0 at exactly day 60 and stays 0 after
3. ✅ **Edge Cases**: Day 1, 59, and 61 all handled correctly
4. ✅ **Future Amplification**: Coverage loss risk amplifies exponentially for future events
5. ✅ **Past Deterioration**: Other risks (payer/provider errors) deteriorate exponentially for past events
6. ✅ **Mixed Behaviors**: Multiple risks with different behaviors work correctly together
7. ✅ **Unknown Handling**: UNKNOWN event tense doesn't modify risks

## Formula Verification

### Retrospective Denial (Linear)
```
For t ≤ 60: P_adjusted = P_base × (1 - t/60)
For t > 60: P_adjusted = 0.0
```

### Coverage Loss (Exponential Amplification)
```
P_adjusted = P_base × exp(α × t) where α = 0.001
```

### Payer/Provider Error (Exponential Deterioration)
```
P_adjusted = P_base × exp(-α × t) where α = 0.001
```

## Conclusion

All test cases passed successfully. The time function correctly implements:
- Linear decrease for retrospective denial risk over 60 days
- Exponential amplification for future risks
- Exponential deterioration for past risks (except retrospective denial)
- Proper handling of edge cases and multiple risks
