"""Tests for realize_core.evolution.engine -- auto-evolution engine."""

from realize_core.evolution.engine import (
    EvolutionEngine,
    EvolutionProposal,
    EvolutionRateLimiter,
    EvolutionType,
    ProposalStatus,
    RiskLevel,
    get_evolution_engine,
    validate_proposal,
)


class TestEvolutionType:
    def test_all_types(self):
        assert len(EvolutionType) == 5


class TestRiskLevel:
    def test_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.HIGH.value == "high"


class TestProposalStatus:
    def test_all_statuses(self):
        assert len(ProposalStatus) == 5


class TestEvolutionProposal:
    def test_defaults(self):
        p = EvolutionProposal(
            id="p1",
            evolution_type=EvolutionType.NEW_SKILL,
            title="New weather skill",
            description="Add weather lookup",
        )
        assert p.risk_level == RiskLevel.LOW
        assert p.status == ProposalStatus.PENDING
        assert p.priority == 0.5


class TestValidateProposal:
    def test_valid_proposal(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
            changes={"yaml": "name: test_skill\nversion: '2.0'"},
        )
        valid, reason = validate_proposal(p)
        assert valid
        assert reason == ""

    def test_blocked_path_env(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.CONFIG_CHANGE,
            title="Test", description="",
            changes={"target_path": "systems/my-system/.env"},
        )
        valid, reason = validate_proposal(p)
        assert not valid
        assert "Blocked path" in reason

    def test_blocked_path_config(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.CONFIG_CHANGE,
            title="Test", description="",
            changes={"target_path": "realize-os.yaml"},
        )
        valid, reason = validate_proposal(p)
        assert not valid
        assert "realize-os.yaml" in reason

    def test_blocked_path_identity(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.CONFIG_CHANGE,
            title="Test", description="",
            changes={"prompt_path": "A-agents/identity.md"},
        )
        valid, reason = validate_proposal(p)
        assert not valid

    def test_content_too_large(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
            changes={"content": "x" * 20000},
        )
        valid, reason = validate_proposal(p)
        assert not valid
        assert "too large" in reason.lower()

    def test_dangerous_import_subprocess(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
            changes={"content": "import subprocess"},
        )
        valid, reason = validate_proposal(p)
        assert not valid

    def test_safe_content(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
            changes={"yaml": "name: test\nsteps:\n  - search web"},
        )
        valid, _ = validate_proposal(p)
        assert valid

    def test_empty_changes_valid(self):
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        valid, _ = validate_proposal(p)
        assert valid


class TestEvolutionEngine:
    def test_propose(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        assert engine.propose(p)
        assert engine.proposal_count == 1

    def test_propose_duplicate(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        engine.propose(p)
        assert not engine.propose(p)

    def test_auto_approve_low_risk(self):
        engine = EvolutionEngine(auto_approve_low_risk=True, persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
            risk_level=RiskLevel.LOW,
        )
        engine.propose(p)
        assert p.status == ProposalStatus.APPROVED

    def test_no_auto_approve_medium_risk(self):
        engine = EvolutionEngine(auto_approve_low_risk=True, persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.CONFIG_CHANGE,
            title="Change config", description="",
            risk_level=RiskLevel.MEDIUM,
        )
        engine.propose(p)
        assert p.status == ProposalStatus.PENDING

    def test_manual_approve(self):
        engine = EvolutionEngine(auto_approve_low_risk=False, persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        engine.propose(p)
        assert engine.approve("p1")
        assert p.status == ProposalStatus.APPROVED

    def test_reject(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.CONFIG_CHANGE,
            title="Test", description="",
            risk_level=RiskLevel.HIGH,
        )
        engine.propose(p)
        assert engine.reject("p1", reason="Too risky")
        assert p.status == ProposalStatus.REJECTED
        assert p.metadata["rejection_reason"] == "Too risky"

    def test_apply(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        engine.propose(p)
        assert engine.apply("p1")
        assert p.status == ProposalStatus.APPLIED
        assert p.applied_at > 0

    def test_apply_unapproved_fails(self):
        engine = EvolutionEngine(auto_approve_low_risk=False, persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        engine.propose(p)
        assert not engine.apply("p1")

    def test_apply_dry_run(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
            changes={"yaml": "name: test"},
        )
        engine.propose(p)
        result = engine.apply("p1", dry_run=True)
        assert isinstance(result, dict)
        assert result["would_apply"] is True
        assert result["title"] == "Test"
        assert p.status == ProposalStatus.APPROVED  # Not applied

    def test_rollback(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        engine.propose(p)
        engine.apply("p1")
        assert engine.rollback("p1")
        assert p.status == ProposalStatus.ROLLED_BACK

    def test_rollback_non_applied_fails(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Test", description="",
        )
        engine.propose(p)
        assert not engine.rollback("p1")

    def test_rate_limit(self):
        engine = EvolutionEngine(rate_limit_per_hour=2, persist=False)
        for i in range(3):
            p = EvolutionProposal(
                id=f"p{i}", evolution_type=EvolutionType.NEW_SKILL,
                title=f"Test {i}", description="",
            )
            engine.propose(p)
            if i < 2:
                assert engine.apply(f"p{i}")
            else:
                assert not engine.apply(f"p{i}")

    def test_get_pending(self):
        engine = EvolutionEngine(auto_approve_low_risk=False, persist=False)
        for i, prio in enumerate([0.3, 0.9, 0.5]):
            engine.propose(
                EvolutionProposal(
                    id=f"p{i}", evolution_type=EvolutionType.NEW_SKILL,
                    title=f"Test {i}", description="",
                    priority=prio,
                )
            )
        pending = engine.get_pending()
        assert len(pending) == 3
        assert pending[0].priority == 0.9

    def test_get_applied(self):
        engine = EvolutionEngine(persist=False)
        engine.propose(
            EvolutionProposal(
                id="p1", evolution_type=EvolutionType.NEW_SKILL,
                title="A", description="",
            )
        )
        engine.apply("p1")
        applied = engine.get_applied()
        assert len(applied) == 1

    def test_status_summary(self):
        engine = EvolutionEngine(persist=False)
        engine.propose(
            EvolutionProposal(
                id="p1", evolution_type=EvolutionType.NEW_SKILL,
                title="A", description="",
            )
        )
        summary = engine.status_summary()
        assert summary["total"] == 1
        assert "approved" in summary["by_status"]

    def test_safety_rejection_blocked_path(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.CONFIG_CHANGE,
            title="Bad change", description="",
            changes={"target_path": ".env"},
        )
        assert not engine.propose(p)
        assert p.status == ProposalStatus.REJECTED
        assert "Safety" in p.metadata.get("rejection_reason", "")

    def test_safety_rejection_dangerous_content(self):
        engine = EvolutionEngine(persist=False)
        p = EvolutionProposal(
            id="p1", evolution_type=EvolutionType.NEW_SKILL,
            title="Bad skill", description="",
            changes={"content": "import subprocess"},
        )
        assert not engine.propose(p)
        assert p.status == ProposalStatus.REJECTED


class TestEvolutionRateLimiter:
    def test_allows_within_limit(self):
        limiter = EvolutionRateLimiter(max_calls_per_hour=5)
        assert limiter.check()
        limiter.record()
        assert limiter.check()
        assert limiter.remaining == 4

    def test_blocks_at_limit(self):
        limiter = EvolutionRateLimiter(max_calls_per_hour=2)
        limiter.record()
        limiter.record()
        assert not limiter.check()
        assert limiter.remaining == 0


class TestSingleton:
    def test_singleton(self):
        import realize_core.evolution.engine as mod

        mod._engine = None
        e1 = get_evolution_engine(persist=False)
        e2 = get_evolution_engine()
        assert e1 is e2
        mod._engine = None
