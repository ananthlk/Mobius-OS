# Eligibility Probability Formulas

## Overview

This document defines the mathematical formulas for computing eligibility probabilities across four case states:
- **ELIGIBLE** (YES): Patient is eligible for coverage
- **NOT_ELIGIBLE** (NO): Patient is not eligible for coverage
- **NO_INFO** (NOT_ESTABLISHED): Insufficient information to determine eligibility
- **UNESTABLISHED** (ERROR/UNKNOWN): System error or unknown status

## 1. Base Probability by State

### 1.1 Formula Structure

For each case state `s ∈ {ELIGIBLE, NOT_ELIGIBLE, NO_INFO, UNESTABLISHED}`, the base probability is computed using a waterfall/backoff strategy:

```
P_base(s | D) = QueryHistoricalRate(s, D)
```

Where:
- `D` = set of known dimensions (product_type, contract_status, event_tense, payer_id, sex, age_bucket)
- Query uses waterfall strategy: try most specific dimensions first, back off to less specific if sample size < min_n

### 1.2 Historical Rate Query

For each state `s`, query `eligibility_transactions`:

```sql
SELECT 
    COUNT(*) as n,
    AVG(CASE WHEN eligibility_status = :state THEN 1.0 ELSE 0.0 END) as probability
FROM eligibility_transactions
WHERE [dimension_filters]
```

**State Mapping**:
- `ELIGIBLE` → `eligibility_status = 'YES'`
- `NOT_ELIGIBLE` → `eligibility_status = 'NO'`
- `NO_INFO` → `eligibility_status = 'NOT_ESTABLISHED'` OR missing critical fields
- `UNESTABLISHED` → `eligibility_status = 'UNKNOWN'` OR `error_type IS NOT NULL`

### 1.3 Waterfall/Backoff Strategy

Try queries in order of specificity (most specific first):

1. **Level 6**: All dimensions (product_type, contract_status, event_tense, payer_id, sex, age_bucket)
2. **Level 5**: 5 dimensions (drop least important)
3. **Level 4**: 4 dimensions
4. **Level 3**: 3 dimensions
5. **Level 2**: 2 dimensions
6. **Level 1**: 1 dimension
7. **Level 0**: Global average (no filters)

**Selection Criteria**:
- Prefer higher level if `combined_confidence > 0.2` AND `sample_size >= min_n` (default: 20)
- Otherwise, use highest level with `combined_confidence > 0.2`
- Fallback to global average if no level meets criteria

### 1.4 Confidence Calculation

```
combined_confidence = min(0.95, sample_size / 100.0)
```

For small samples, use Bayesian adjustment:
```
adjusted_probability = (n * probability + prior_n * prior_probability) / (n + prior_n)
```

Where:
- `prior_n = 10` (pseudocount)
- `prior_probability = 0.25` (uniform prior for 4 states)

## 2. Time-Based Adjustments

### 2.1 Time Function Overview

Time adjustments account for:
- **Future events**: Risk of coverage loss between today and DOS
- **Past events**: Risk of retrospective eligibility issues (coverage lost after visit)

### 2.2 Future Event Time Function

For `event_tense = FUTURE`:

```
P_adjusted(s | t, D) = P_base(s | D) * f_future(t, s)
```

Where:
- `t = days_between(today, dos_date)` (time gap in days)
- `f_future(t, s)` = time adjustment factor

**For ELIGIBLE state**:
```
f_future(t, ELIGIBLE) = exp(-λ_loss * t)
```

Where:
- `λ_loss = historical_coverage_loss_rate / average_time_to_loss`
- `historical_coverage_loss_rate` = query from `eligibility_transactions`:
  ```sql
  SELECT 
      COUNT(*) FILTER (WHERE lost_coverage_before_dos = true) / COUNT(*) as loss_rate,
      AVG(days_to_loss) as avg_days_to_loss
  FROM eligibility_transactions
  WHERE eligibility_status = 'YES' 
    AND event_tense = 'FUTURE'
    AND [dimension_filters]
  ```
- `λ_loss` defaults to `0.001` (0.1% per day) if no historical data

**For NOT_ELIGIBLE state**:
```
f_future(t, NOT_ELIGIBLE) = 1.0  # No time adjustment (already determined)
```

**For NO_INFO state**:
```
f_future(t, NO_INFO) = 1.0 + α * t  # Slight increase over time (harder to resolve)
```

Where:
- `α = 0.0001` (0.01% per day increase in uncertainty)

**For UNESTABLISHED state**:
```
f_future(t, UNESTABLISHED) = 1.0  # No time adjustment (error state)
```

### 2.3 Past Event Time Function

For `event_tense = PAST`:

```
P_adjusted(s | t, D) = P_base(s | D) * f_past(t, s)
```

Where:
- `t = days_between(visit_date, today)` (days since visit)
- `f_past(t, s)` = retrospective time adjustment factor

**For ELIGIBLE state**:
```
f_past(t, ELIGIBLE) = exp(-λ_retro * t) * (1 - denial_probability(t))
```

Where:
- `λ_retro = historical_retrospective_denial_rate / average_time_to_denial`
- `denial_probability(t)` = probability of payment denial given `t` days since visit:
  ```sql
  SELECT 
      COUNT(*) FILTER (WHERE payment_status = 'DENIED') / COUNT(*) as denial_rate
  FROM eligibility_transactions
  WHERE eligibility_status = 'YES'
    AND event_tense = 'PAST'
    AND days_since_visit BETWEEN :t - 30 AND :t + 30
    AND [dimension_filters]
  ```
- `λ_retro` defaults to `0.0005` (0.05% per day) if no historical data

**For NOT_ELIGIBLE state**:
```
f_past(t, NOT_ELIGIBLE) = 1.0 + β * t  # Slight increase (more time = more likely false negative)
```

Where:
- `β = 0.0002` (0.02% per day increase in false negative risk)

**For NO_INFO state**:
```
f_past(t, NO_INFO) = exp(-λ_resolution * t)  # Decreases over time (more likely resolved)
```

Where:
- `λ_resolution = historical_resolution_rate / average_time_to_resolution`
- `λ_resolution` defaults to `0.001` (0.1% per day resolution rate)

**For UNESTABLISHED state**:
```
f_past(t, UNESTABLISHED) = exp(-λ_error_resolution * t)  # Errors more likely resolved over time
```

Where:
- `λ_error_resolution = 0.002` (0.2% per day error resolution rate)

### 2.4 Time Function Parameters Summary

| State | Future Function | Past Function | Default Parameters |
|-------|----------------|---------------|-------------------|
| ELIGIBLE | `exp(-λ_loss * t)` | `exp(-λ_retro * t) * (1 - denial_prob(t))` | `λ_loss = 0.001`, `λ_retro = 0.0005` |
| NOT_ELIGIBLE | `1.0` | `1.0 + β * t` | `β = 0.0002` |
| NO_INFO | `1.0 + α * t` | `exp(-λ_resolution * t)` | `α = 0.0001`, `λ_resolution = 0.001` |
| UNESTABLISHED | `1.0` | `exp(-λ_error_resolution * t)` | `λ_error_resolution = 0.002` |

## 3. Combined Probability Calculation

### 3.1 Final Probability Formula

For each state `s`:

```
P_final(s | t, D) = P_base(s | D) * f_time(t, s) * f_risk(s)
```

Where:
- `f_time(t, s)` = time adjustment (from Section 2)
- `f_risk(s)` = risk adjustment factor (from risk assessment, see Section 4)

### 3.2 Normalization

After computing all four probabilities, normalize to ensure they sum to 1.0:

```
P_normalized(s) = P_final(s) / Σ P_final(s_i) for all s_i
```

This ensures:
```
Σ P_normalized(s_i) = 1.0 for all states s_i
```

### 3.3 Uncertainty Quantification

Compute uncertainty as:

```
uncertainty = 1 - max(P_normalized(s_i)) for all s_i
```

High uncertainty (e.g., > 0.5) indicates:
- Low confidence in any single state
- Need for more information
- Higher risk of incorrect determination

## 4. Risk Adjustment Factors

### 4.1 Risk-Adjusted Probability

```
f_risk(s) = 1 - Σ risk_severity(r) for all risks r affecting state s
```

Where:
- `risk_severity(r) ∈ [0, 1]` (from risk assessment)
- Risks reduce probability of their target state

**Example**:
- If `COVERAGE_LOSS` risk has severity 0.3 for ELIGIBLE state:
  ```
  f_risk(ELIGIBLE) = 1 - 0.3 = 0.7
  ```
- This reduces `P_final(ELIGIBLE)` by 30%

### 4.2 Risk Types by State

| State | Risk Types | Impact on Probability |
|-------|------------|------------------------|
| ELIGIBLE | COVERAGE_LOSS, PAYER_ERROR, PROVIDER_ERROR | Reduces probability |
| NOT_ELIGIBLE | PAYER_ERROR, PROVIDER_ERROR (false negative) | Reduces probability |
| NO_INFO | Resolution risks, data availability risks | Reduces probability |
| UNESTABLISHED | Error recurrence risks, system reliability risks | Reduces probability |

## 5. Visit-Specific Probability

### 5.1 Per-Visit Calculation

For each visit `v`:

```
P_visit(s, v | t_v, D_v) = P_base(s | D_v) * f_time(t_v, s) * f_risk(s, v)
```

Where:
- `t_v = days_between(today, v.visit_date)` (for future) or `days_between(v.visit_date, today)` (for past)
- `D_v` = dimensions specific to visit `v` (may differ from case-level dimensions)
- `f_risk(s, v)` = visit-specific risk factors

### 5.2 Case-Level Aggregation

Aggregate visit probabilities to case level:

```
P_case(s) = weighted_average(P_visit(s, v_i) for all visits v_i)
```

Where weights can be:
- **Equal weights**: `w_i = 1 / n_visits`
- **Time-weighted**: `w_i = exp(-|t_v_i| / τ)` (closer visits weighted more)
- **Status-weighted**: `w_i = 1.0` for scheduled, `0.8` for completed, `0.5` for cancelled

Default: **Equal weights**

## 6. Implementation Notes

### 6.1 Query Optimization

- Cache historical rates by dimension combination
- Use materialized views for common queries
- Pre-compute time adjustment factors for common time gaps

### 6.2 Edge Cases

1. **No historical data**: Use uniform prior (0.25 for each state)
2. **Very large time gaps** (t > 365 days): Cap time adjustments to prevent extreme values
3. **Multiple visits with conflicting states**: Use weighted average with higher weight on more recent/confident visits
4. **All probabilities very low**: Indicates high uncertainty, trigger "NO_INFO" state

### 6.3 Confidence Intervals

For each probability, compute confidence interval:

```
CI_lower = P_normalized(s) - z * sqrt(P_normalized(s) * (1 - P_normalized(s)) / n)
CI_upper = P_normalized(s) + z * sqrt(P_normalized(s) * (1 - P_normalized(s)) / n)
```

Where:
- `z = 1.96` for 95% confidence interval
- `n = sample_size` from historical query

## 7. Example Calculation

### 7.1 Scenario

- **Case State**: ELIGIBLE (base probability = 0.7)
- **Event Tense**: FUTURE
- **Time Gap**: 30 days until DOS
- **Dimensions**: product_type=COMMERCIAL, contract_status=ACTIVE
- **Risks**: COVERAGE_LOSS (severity=0.15), PAYER_ERROR (severity=0.05)

### 7.2 Calculation Steps

1. **Base Probability**: `P_base(ELIGIBLE) = 0.7`

2. **Time Adjustment**:
   ```
   f_future(30, ELIGIBLE) = exp(-0.001 * 30) = exp(-0.03) ≈ 0.970
   ```

3. **Risk Adjustment**:
   ```
   f_risk(ELIGIBLE) = 1 - 0.15 - 0.05 = 0.80
   ```

4. **Final Probability**:
   ```
   P_final(ELIGIBLE) = 0.7 * 0.970 * 0.80 = 0.543
   ```

5. **Normalize** (assuming other states sum to 0.457):
   ```
   P_normalized(ELIGIBLE) = 0.543 / (0.543 + 0.457) = 0.543
   ```

### 7.3 Result

- **ELIGIBLE**: 54.3%
- **NOT_ELIGIBLE**: ~25% (estimated)
- **NO_INFO**: ~15% (estimated)
- **UNESTABLISHED**: ~5.7% (estimated)

## 8. References

- Waterfall/Backoff Strategy: See `nexus/services/eligibility_v2/propensity_repository.py`
- Risk Assessment: See `nexus/agents/eligibility_v2/risk_assessor.py` (to be implemented)
- Time Functions: Based on exponential decay models for coverage loss and retrospective eligibility
