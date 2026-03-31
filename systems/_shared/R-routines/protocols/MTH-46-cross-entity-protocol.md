# MTH-46 — Cross-Entity Protocol

> Shared Protocol | Used by: Burtucala (ENT-02), MC (ENT-05), Realization (ENT-01) | Agents: Orchestrator, all agents when cross-entity context is needed

---

## Purpose

Governs how systems reference, share, and collaborate across entity boundaries. Prevents data leakage while enabling legitimate cross-entity work. Maintains clear ownership and accountability.

## When to Use

- An agent needs context or output from another entity's system
- A task spans multiple entities (e.g., MC project needing Realization content)
- Financial or legal matters cross entity boundaries
- Shared resources (people, vendors, knowledge) are referenced across systems

## Core Principles

### 1. Entity Sovereignty
Each entity system owns its data, voice, and decisions. Cross-entity access is a controlled handoff, not shared ownership.

### 2. Explicit Reference, Not Copy
When referencing another entity's work, link to the source — don't duplicate content. Duplication creates drift.

### 3. Voice Isolation
An entity's voice rules NEVER bleed into another entity's output. If Realization creates content about MC's project, it uses Realization's voice. If MC reports on Realization's strategy, it uses MC's reporting voice.

### 4. Governance Respect
Each entity's governance thresholds and approval chains apply to their scope. Cross-entity decisions escalate to the Orchestrator level.

---

## Cross-Entity Interaction Patterns

### Pattern A: Content Support

**Scenario:** Entity A needs content created, but Entity B has the content creation capability.

**Example:** MC (ENT-05) needs marketing content for Arena Habitat, but MC has no content agents. Realization (ENT-01) Copywriter creates it.

**Process:**
1. MC Orchestrator requests content from Realization Orchestrator
2. Realization Copywriter receives the brief with MC context parameters
3. Copywriter creates content using Realization voice + MC subject matter
4. Realization Gatekeeper reviews for Realization voice compliance
5. Output is delivered to MC for factual accuracy review
6. MC uses the content within its communications

**Key rule:** The content is created in the producing entity's voice. The requesting entity can request factual edits but not voice changes.

### Pattern B: Financial Cross-Reference

**Scenario:** Financial data from one entity informs decisions in another.

**Example:** Realization's ROI model for a property is referenced in Burtucala's Syndicate Dossier.

**Process:**
1. Requesting entity references the source entity + document
2. Source entity provides read-only access to the relevant data
3. Requesting entity cites the source with date and version
4. Any modifications or updates to source data trigger a notification

**Key rule:** Financial data is referenced, not copied. The source entity remains the authority on their numbers.

### Pattern C: Shared Resource Coordination

**Scenario:** A person, vendor, or resource works across multiple entities.

**Example:** Asaf is Project Director at MC and Strategist at Realization. A decision in one role affects the other.

**Process:**
1. The agent identifies the cross-entity impact
2. Both relevant Orchestrators are notified
3. Decision is logged in BOTH entities' M-memory/decisions.md
4. If conflict exists, escalate to the human (Asaf) for resolution

**Key rule:** Shared resources don't create shared governance. Each entity's rules apply within its boundaries.

### Pattern D: Deal Pipeline Referral

**Scenario:** A deal evaluated in one entity is more suitable for another.

**Example:** Burtucala evaluates a property that's better suited for MC's residential development model.

**Process:**
1. Source entity completes initial evaluation (MTH-15 Phase 1)
2. Source entity flags the opportunity as "better fit for [target entity]"
3. Evaluation data is shared with target entity's Orchestrator
4. Target entity runs its own full evaluation with its own criteria
5. Source entity's initial work is credited and referenced

**Key rule:** The receiving entity always runs its own evaluation. A referral is not an endorsement.

---

## Entity Relationship Map

| From | To | Common Interactions |
|------|----|-------------------|
| **Realization** (ENT-01) | **Burtucala** (ENT-02) | Content repurposing, venture strategy, market insights |
| **Realization** (ENT-01) | **MC** (ENT-05) | Content creation for Arena Habitat, strategic oversight |
| **Burtucala** (ENT-02) | **Realization** (ENT-01) | Brand positioning insights, client referrals |
| **Burtucala** (ENT-02) | **MC** (ENT-05) | Deal referrals, market comps |
| **MC** (ENT-05) | **Realization** (ENT-01) | Content requests, strategy input, GP coordination |
| **MC** (ENT-05) | **Burtucala** (ENT-02) | Market data sharing, comp analysis |

## Governance Cross-Reference

### MC-Specific (ENT-05)
```yaml
gp_structure: "Realization (33%) + Zodiaco (67%)"
gp_threshold: "Internal GP approves <5,000 EUR"
joint_threshold: "Joint GP decision 5,000-10,000 EUR"
lp_threshold: "LP approval required >10,000 EUR"
variance_flag: ">2.5% variance from plan = LP notification"
```

When MC agents encounter decisions crossing these thresholds, the Cross-Entity Protocol intersects with the governance rules — both apply.

## Data Boundaries

### Shareable Across Entities
- Published content (already public)
- Market data and comps (non-proprietary)
- General strategy direction (high-level)
- Shared-library methods (MTH-XX — designed to be shared)

### NOT Shareable Without Explicit Authorization
- Client lists and contact details
- Financial details of specific deals
- Internal pricing or margin data
- Unpublished strategy documents
- LP communications and investor terms

---

## Quality Standards

- Every cross-entity interaction is logged in both entities' M-memory/decisions.md
- Voice isolation is verified by Gatekeeper (MTH-42) on every cross-entity output
- Financial cross-references include date, version, and source entity
- Conflicting priorities between entities are escalated to Asaf, never resolved autonomously

---

> Status: active
> Last updated: 2026-02-10
