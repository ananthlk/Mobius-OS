"""
Unit tests for TimeFunction

Tests the time-based amplification/deterioration of risk probabilities.
"""
import pytest
from nexus.agents.eligibility_v2.time_function import TimeFunction
from nexus.agents.eligibility_v2.models import EventTense


class TestTimeFunction:
    """Test suite for TimeFunction"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.time_function = TimeFunction()
    
    @pytest.mark.asyncio
    async def test_retrospective_denial_linear_decrease(self):
        """Test retrospective_denial risk with linear decrease over 60 days"""
        base_risk = 0.15  # 15% base risk
        
        # Test at day 0 (should be full base risk)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            0
        )
        assert adjusted["retrospective_denial"] == pytest.approx(base_risk, abs=0.001)
        print(f"✓ Day 0: {adjusted['retrospective_denial']:.1%} (expected: {base_risk:.1%})")
        
        # Test at day 15 (should be 75% of base risk: 1 - 15/60 = 0.75)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            15
        )
        expected_15 = base_risk * (1 - 15/60)  # 0.15 * 0.75 = 0.1125
        assert adjusted["retrospective_denial"] == pytest.approx(expected_15, abs=0.001)
        print(f"✓ Day 15: {adjusted['retrospective_denial']:.1%} (expected: {expected_15:.1%})")
        
        # Test at day 30 (should be 50% of base risk: 1 - 30/60 = 0.5)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            30
        )
        expected_30 = base_risk * (1 - 30/60)  # 0.15 * 0.5 = 0.075
        assert adjusted["retrospective_denial"] == pytest.approx(expected_30, abs=0.001)
        print(f"✓ Day 30: {adjusted['retrospective_denial']:.1%} (expected: {expected_30:.1%})")
        
        # Test at day 45 (should be 25% of base risk: 1 - 45/60 = 0.25)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            45
        )
        expected_45 = base_risk * (1 - 45/60)  # 0.15 * 0.25 = 0.0375
        assert adjusted["retrospective_denial"] == pytest.approx(expected_45, abs=0.001)
        print(f"✓ Day 45: {adjusted['retrospective_denial']:.1%} (expected: {expected_45:.1%})")
        
        # Test at day 60 (should be 0%: 1 - 60/60 = 0)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            60
        )
        assert adjusted["retrospective_denial"] == pytest.approx(0.0, abs=0.001)
        print(f"✓ Day 60: {adjusted['retrospective_denial']:.1%} (expected: 0.0%)")
        
        # Test at day 90 (should be 0% after 60 days)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            90
        )
        assert adjusted["retrospective_denial"] == pytest.approx(0.0, abs=0.001)
        print(f"✓ Day 90: {adjusted['retrospective_denial']:.1%} (expected: 0.0%)")
        
        # Test at day 120 (should be 0% after 60 days)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            120
        )
        assert adjusted["retrospective_denial"] == pytest.approx(0.0, abs=0.001)
        print(f"✓ Day 120: {adjusted['retrospective_denial']:.1%} (expected: 0.0%)")
    
    @pytest.mark.asyncio
    async def test_retrospective_denial_edge_cases(self):
        """Test edge cases for retrospective_denial"""
        base_risk = 0.20  # 20% base risk
        
        # Test at day 1 (should be very close to base risk)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            1
        )
        expected_1 = base_risk * (1 - 1/60)  # 0.20 * (59/60) ≈ 0.1967
        assert adjusted["retrospective_denial"] == pytest.approx(expected_1, abs=0.001)
        print(f"✓ Day 1: {adjusted['retrospective_denial']:.4f} (expected: {expected_1:.4f})")
        
        # Test at day 59 (should be very close to 0)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            59
        )
        expected_59 = base_risk * (1 - 59/60)  # 0.20 * (1/60) ≈ 0.0033
        assert adjusted["retrospective_denial"] == pytest.approx(expected_59, abs=0.001)
        print(f"✓ Day 59: {adjusted['retrospective_denial']:.4f} (expected: {expected_59:.4f})")
        
        # Test at day 61 (should be 0)
        adjusted = await self.time_function.apply_time_function(
            {"retrospective_denial": base_risk},
            EventTense.PAST,
            61
        )
        assert adjusted["retrospective_denial"] == pytest.approx(0.0, abs=0.001)
        print(f"✓ Day 61: {adjusted['retrospective_denial']:.1%} (expected: 0.0%)")
    
    @pytest.mark.asyncio
    async def test_coverage_loss_future_amplification(self):
        """Test coverage_loss risk amplification for future events"""
        base_risk = 0.10  # 10% base risk
        
        # Test at day 0 (should be base risk)
        adjusted = await self.time_function.apply_time_function(
            {"coverage_loss": base_risk},
            EventTense.FUTURE,
            0
        )
        assert adjusted["coverage_loss"] == pytest.approx(base_risk, abs=0.001)
        print(f"✓ Coverage Loss Day 0: {adjusted['coverage_loss']:.1%} (expected: {base_risk:.1%})")
        
        # Test at day 30 (should be amplified)
        adjusted = await self.time_function.apply_time_function(
            {"coverage_loss": base_risk},
            EventTense.FUTURE,
            30
        )
        # α = 0.001, so exp(0.001 * 30) ≈ 1.0305
        expected_30 = base_risk * 1.0305  # ≈ 0.103
        assert adjusted["coverage_loss"] > base_risk
        assert adjusted["coverage_loss"] == pytest.approx(expected_30, abs=0.002)
        print(f"✓ Coverage Loss Day 30: {adjusted['coverage_loss']:.1%} (expected: ~{expected_30:.1%})")
        
        # Test at day 60 (should be more amplified)
        adjusted = await self.time_function.apply_time_function(
            {"coverage_loss": base_risk},
            EventTense.FUTURE,
            60
        )
        # exp(0.001 * 60) ≈ 1.0618
        expected_60 = base_risk * 1.0618  # ≈ 0.106
        assert adjusted["coverage_loss"] > base_risk
        assert adjusted["coverage_loss"] == pytest.approx(expected_60, abs=0.002)
        print(f"✓ Coverage Loss Day 60: {adjusted['coverage_loss']:.1%} (expected: ~{expected_60:.1%})")
    
    @pytest.mark.asyncio
    async def test_payer_error_past_deterioration(self):
        """Test payer_error risk deterioration for past events (exponential)"""
        base_risk = 0.05  # 5% base risk
        
        # Test at day 0 (should be base risk)
        adjusted = await self.time_function.apply_time_function(
            {"payer_error": base_risk},
            EventTense.PAST,
            0
        )
        assert adjusted["payer_error"] == pytest.approx(base_risk, abs=0.001)
        print(f"✓ Payer Error Day 0: {adjusted['payer_error']:.1%} (expected: {base_risk:.1%})")
        
        # Test at day 30 (should be deteriorated exponentially)
        adjusted = await self.time_function.apply_time_function(
            {"payer_error": base_risk},
            EventTense.PAST,
            30
        )
        # α = 0.001, so exp(-0.001 * 30) ≈ 0.9704
        expected_30 = base_risk * 0.9704  # ≈ 0.0485
        assert adjusted["payer_error"] < base_risk
        assert adjusted["payer_error"] == pytest.approx(expected_30, abs=0.001)
        print(f"✓ Payer Error Day 30: {adjusted['payer_error']:.1%} (expected: ~{expected_30:.1%})")
    
    @pytest.mark.asyncio
    async def test_multiple_risks_mixed(self):
        """Test multiple risks with different behaviors"""
        risks = {
            "retrospective_denial": 0.15,  # Linear decrease
            "payer_error": 0.05,          # Exponential decrease
            "provider_error": 0.03         # Exponential decrease
        }
        
        # Test at day 30 (past event)
        adjusted = await self.time_function.apply_time_function(
            risks,
            EventTense.PAST,
            30
        )
        
        # Retrospective denial: linear, should be 50% of base (1 - 30/60 = 0.5)
        expected_retro = 0.15 * 0.5  # 0.075
        assert adjusted["retrospective_denial"] == pytest.approx(expected_retro, abs=0.001)
        print(f"✓ Retrospective Denial Day 30: {adjusted['retrospective_denial']:.1%} (expected: {expected_retro:.1%})")
        
        # Payer error: exponential, should be deteriorated
        assert adjusted["payer_error"] < risks["payer_error"]
        print(f"✓ Payer Error Day 30: {adjusted['payer_error']:.1%} (decreased from {risks['payer_error']:.1%})")
        
        # Provider error: exponential, should be deteriorated
        assert adjusted["provider_error"] < risks["provider_error"]
        print(f"✓ Provider Error Day 30: {adjusted['provider_error']:.1%} (decreased from {risks['provider_error']:.1%})")
    
    @pytest.mark.asyncio
    async def test_unknown_event_tense(self):
        """Test that UNKNOWN event tense doesn't adjust risks"""
        base_risk = 0.10
        
        adjusted = await self.time_function.apply_time_function(
            {"coverage_loss": base_risk},
            EventTense.UNKNOWN,
            30
        )
        
        # Should remain unchanged
        assert adjusted["coverage_loss"] == pytest.approx(base_risk, abs=0.001)
        print(f"✓ UNKNOWN event tense: {adjusted['coverage_loss']:.1%} (unchanged from {base_risk:.1%})")


if __name__ == "__main__":
    print("=" * 70)
    print("TimeFunction Unit Tests")
    print("=" * 70)
    print()
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
