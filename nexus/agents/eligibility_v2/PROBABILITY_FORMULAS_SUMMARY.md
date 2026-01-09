# Probability Formulas - Quick Reference

## Core Formula Structure

```
P_final(state | time, dimensions) = P_base(state | dimensions) × f_time(time, state) × f_risk(state)
```

Then normalize all 4 states to sum to 1.0.

---

## 1. Base Probability by State

### Query Structure
```sql
SELECT 
    COUNT(*) as n,
    AVG(CASE WHEN eligibility_status = :state THEN 1.0 ELSE 0.0 END) as probability
FROM eligibility_transactions
WHERE [dimension_filters: product_type, contract_status, event_tense, payer_id, sex, age_bucket]
```

### States
- **ELIGIBLE**: `eligibility_status = 'YES'`
- **NOT_ELIGIBLE**: `eligibility_status = 'NO'`
- **NO_INFO**: `eligibility_status = 'NOT_ESTABLISHED'` OR missing critical fields
- **UNESTABLISHED**: `eligibility_status = 'UNKNOWN'` OR `error_type IS NOT NULL`

### Waterfall Strategy
Try queries from most specific (6 dimensions) → least specific (0 dimensions = global average)
- Select highest level where `confidence > 0.2` AND `sample_size >= 20`

---

## 2. Time Functions

### Future Events (`event_tense = FUTURE`)
`t = days_between(today, dos_date)`

| State | Time Function | Formula |
|-------|---------------|---------|
| **ELIGIBLE** | Exponential decay (coverage loss risk) | `exp(-λ_loss × t)`<br/>λ_loss = 0.001/day (0.1% per day) |
| **NOT_ELIGIBLE** | No adjustment | `1.0` |
| **NO_INFO** | Linear increase (uncertainty grows) | `1.0 + α × t`<br/>α = 0.0001/day (0.01% per day) |
| **UNESTABLISHED** | No adjustment | `1.0` |

### Past Events (`event_tense = PAST`)
`t = days_between(visit_date, today)`

| State | Time Function | Formula |
|-------|---------------|---------|
| **ELIGIBLE** | Exponential decay + denial risk | `exp(-λ_retro × t) × (1 - denial_prob(t))`<br/>λ_retro = 0.0005/day (0.05% per day) |
| **NOT_ELIGIBLE** | Linear increase (false negative risk) | `1.0 + β × t`<br/>β = 0.0002/day (0.02% per day) |
| **NO_INFO** | Exponential decay (resolution over time) | `exp(-λ_resolution × t)`<br/>λ_resolution = 0.001/day (0.1% per day) |
| **UNESTABLISHED** | Exponential decay (error resolution) | `exp(-λ_error × t)`<br/>λ_error = 0.002/day (0.2% per day) |

---

## 3. Risk Adjustment

```
f_risk(state) = 1 - Σ risk_severity(r) for all risks r affecting state
```

**Risk Types by State**:
- **ELIGIBLE**: COVERAGE_LOSS, PAYER_ERROR, PROVIDER_ERROR
- **NOT_ELIGIBLE**: PAYER_ERROR (false negative), PROVIDER_ERROR
- **NO_INFO**: Resolution risks, data availability risks
- **UNESTABLISHED**: Error recurrence risks, system reliability risks

---

## 4. Normalization

After computing all 4 probabilities:

```
P_normalized(state) = P_final(state) / Σ P_final(all_states)
```

Ensures: `Σ P_normalized(all_states) = 1.0`

---

## 5. Example Calculation

**Scenario**: ELIGIBLE case, 30 days until DOS, with coverage loss risk (15%)

1. **Base**: `P_base(ELIGIBLE) = 0.7`
2. **Time**: `f_future(30, ELIGIBLE) = exp(-0.001 × 30) = 0.970`
3. **Risk**: `f_risk(ELIGIBLE) = 1 - 0.15 = 0.85`
4. **Final**: `P_final(ELIGIBLE) = 0.7 × 0.970 × 0.85 = 0.577`
5. **Normalize**: (assuming other states sum to 0.423) → `P_normalized(ELIGIBLE) = 0.577`

---

## 6. Key Parameters

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `λ_loss` | 0.001/day | Future coverage loss rate for ELIGIBLE |
| `λ_retro` | 0.0005/day | Retrospective denial rate for ELIGIBLE |
| `α` | 0.0001/day | Future uncertainty growth for NO_INFO |
| `β` | 0.0002/day | Past false negative risk for NOT_ELIGIBLE |
| `λ_resolution` | 0.001/day | Past resolution rate for NO_INFO |
| `λ_error` | 0.002/day | Past error resolution rate for UNESTABLISHED |
| `min_n` | 20 | Minimum sample size for waterfall strategy |
| `confidence_threshold` | 0.2 | Minimum confidence for waterfall selection |

---

## 7. Visit Aggregation

For multiple visits:

```
P_case(state) = weighted_average(P_visit(state, v_i) for all visits v_i)
```

**Default weights**: Equal (`1/n_visits`)

**Alternative**: Time-weighted (`w_i = exp(-|t_v_i| / τ)`) - closer visits weighted more
