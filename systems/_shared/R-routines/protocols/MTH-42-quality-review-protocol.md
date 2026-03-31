# MTH-42 — Quality Review Protocol

> Shared Protocol | Used by: ALL entities | Agent: Gatekeeper

---

## Purpose

The Gatekeeper reviews ALL agent outputs before delivery. No content, analysis, recommendation, or communication leaves the system without passing this protocol. This is the final quality gate.

## When to Use

- After ANY agent produces output (content, analysis, report, recommendation, email draft)
- Before sending any response to the user
- Before writing any output to O-output/
- Before updating any M-memory/ file with conclusions

## The 5-Check Review

### Check 1: Voice & Tone

| Verify | Pass | Fail |
|--------|------|------|
| Matches entity brand voice (see C-core/brand-voice.md) | Calm authority, peer-to-peer, generous | Salesy, corporate jargon, hype words |
| Anti-patterns clean (see shared-core/anti-patterns.md) | Zero banned words/phrases | Any match = automatic revision |
| Register matches channel | LinkedIn = professional, newsletter = warm, report = precise | Mixed registers, wrong audience fit |
| Asaf would put his name on it | Feels authentic, specific, human | Generic, could be anyone's content |

**Entity-specific voice rules:**
- **Realization:** Two registers (Hebrew warm/community, English structured/professional). Trilingual texture. Empathy > Authority > Generosity arc.
- **Burtucala:** English only. No em dashes. Numbers before adjectives. Operator voice. Plain English.
- **MC:** Professional, transparent, precise. Governance-aware. No ambiguity on financial figures.

### Check 2: Accuracy & Verification

| Verify | Pass | Fail |
|--------|------|------|
| Facts are sourced | Every claim has a reference or is framed as assumption | Unsourced assertions presented as fact |
| Numbers are verified | Financial figures match source data, calculations checked | Unverified numbers, math errors |
| No invented details | Everything stated actually exists or is clearly hypothetical | Fabricated examples, fake data points |
| Dates are current | References use current/recent data | Outdated information without disclaimer |

### Check 3: Structure & Completeness

| Verify | Pass | Fail |
|--------|------|------|
| Follows the requested format | Blog = blog structure, report = report structure | Wrong format for the task type |
| Has proper sections/flow | Logical progression, clear sections | Disjointed, missing sections |
| Appropriate length | Matches request and channel norms | Too long/short for the context |
| Actionable where needed | Recommendations include clear next steps | Vague suggestions without specifics |

### Check 4: Constraint Compliance

| Verify | Pass | Fail |
|--------|------|------|
| Entity constraints respected | Budget limits, governance thresholds, legal requirements | Ignoring declared constraints |
| Confidentiality maintained | No leaking info between entities unless authorized | Cross-entity data leakage |
| Disclaimers included | Financial content has investment disclaimers | Missing required disclaimers |
| Scope respected | Agent stayed within its defined domain | Agent overstepped into another agent's territory |

### Check 5: Anti-Pattern Sweep

Run the Litmus Test from `shared-core/anti-patterns.md`:

1. Would Asaf be happy to put his name on this?
2. Does it reflect calm authority, NOT loud self-promotion?
3. Does it GIVE value, not EXTRACT attention?
4. Is it specific, or could a competitor copy-paste it?

**If any answer is NO = revision required.**

---

## Review Decision

After running all 5 checks:

### APPROVED
All checks pass. Output is delivered to user or written to O-output/.

### REVISION REQUIRED
One or more checks fail. Return to the originating agent with:
1. Which check(s) failed
2. Specific issue(s) found
3. Concrete revision instructions

**Max revision loops: 2.** If the output fails after 2 revisions, escalate to Orchestrator with a summary of the persistent issue.

### ESCALATE
The issue is beyond the Gatekeeper's scope:
- Contradictory requirements from the user
- Missing information that only the user can provide
- Cross-entity conflict requiring Orchestrator mediation

---

## Context Parameters (Set by Entity State Map)

Each entity provides these via `T-tools/state-map.md`:

```yaml
# Example context parameters
entity: ENT-XX
voice_rules: "reference to C-core/brand-voice.md"
anti_patterns: "shared-core/anti-patterns.md"
special_constraints: "entity-specific rules"
```

## Quality Standards

- Review adds no more than 30 seconds to response time for simple content
- Financial content always gets a deeper review (Check 2 is mandatory deep-check)
- The Gatekeeper never changes the content itself — only approves, requests revision, or escalates
- Every revision request is specific and actionable (not "make it better")
- Patterns of repeated revisions are logged to M-memory/learning-log.md

---

> Status: active
> Last updated: 2026-02-10
