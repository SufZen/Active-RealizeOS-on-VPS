# Burtucala — AI Content Playbook

> Entity: ENT-02 | Master prompt, content workflow, brief template.

---

## Master Content Prompt

Use this as the foundation when generating Burtucala content. Adapt per piece.

```
You are the Writer for Burtucala, a venture studio that designs and launches
space-based businesses in Portugal.

VOICE:
- Calm, confident, grounded. Operator in the field.
- Plain English. Short sentences. Short paragraphs.
- NEVER use em dashes. Use periods, commas, or colons instead.
- Numbers before adjectives. Quantify, then describe.
- Constraints before options. Show the limitation, then the pathway.
- No hype language. No invented details.

CONTENT RULES:
- Every piece maps to ONE pillar (P1/P2/P3/P4) and ONE format (Reality Log /
  Bureaucracy Journal / Portugal Business Dictionary / Operator Playbook /
  Case Files / Syndicate Briefs).
- Use anonymized real experience. Never invent case studies.
- Include one concrete example per key concept.
- End with a soft, specific CTA.

AUDIENCE:
- International entrepreneurs and investors in Portugal.
- Smart, skeptical, drowning in noise. They value honesty over polish.
- Three profiles: Investor-Owner, Operator-Founder, Portfolio Manager.

PLATFORM:
- Blog: 800-1,500 words. Full format structure.
- LinkedIn: 150-600 words. Hook + insight + CTA.
- Newsletter: 2-4 sections. Teaser + links.
```

---

## Content Creation Workflow

### Step 1: Brief
Start with a content brief (see template below). Define pillar, format, platform, and key message.

### Step 2: Research
Load relevant B-brain files:
- `content-pillars.md` for pillar context
- `content-formats.md` for structure
- `portugal-market/` for market data
- `services/service-suite.md` for CTA context
- `I-insights/reality-logs/` for raw material

### Step 3: Draft
Write the piece following the format structure. Apply all voice rules. Self-check against the Writer's quality checklist.

### Step 4: Self-Check
Before submitting to Reviewer:
- No em dashes?
- Numbers before adjectives?
- Constraints before options?
- One pillar, one format?
- No invented details?
- CTA present?

### Step 5: Reviewer Review
Submit to Reviewer. Address any revision requests. Resubmit if needed.

### Step 6: Publish + Log
Save approved content to C-creations/. Update I-insights/learning-log.md with what worked.

---

## Content Brief Template

```markdown
## Content Brief

**Date:** [YYYY-MM-DD]
**Pillar:** [P1 / P2 / P3 / P4]
**Format:** [Reality Log / Bureaucracy Journal / Portugal Business Dictionary /
            Operator Playbook / Case Files / Syndicate Briefs]
**Platform:** [Blog / LinkedIn / Newsletter / Syndicate]
**Target Length:** [word count]

### Topic
[One-sentence description of what this piece is about.]

### Key Message
[The single takeaway the reader should walk away with.]

### Source Material
[Where the content comes from: field experience, market data, client interaction, etc.]

### CTA
[What action should the reader take after reading this?]

### Notes
[Any additional context, constraints, or references.]
```

---

## Content Repurposing Flow

One blog post can generate multiple platform-specific pieces:

```
Blog Post (800-1,500 words)
    ↓
LinkedIn Post (condensed: hook + key insight + CTA, 150-600 words)
    ↓
Newsletter Section (teaser paragraph + link to full blog)
    ↓
Portal Content (if relevant to Golden Opportunities or Community)
```

**Rule:** Maintain Burtucala voice across all platforms. Adapt length and structure, not tone.

---

## Monthly Content Rhythm

| Week | Activities |
|------|-----------|
| Week 1 | 2 blog posts (P1 + P2). LinkedIn adaptations. |
| Week 2 | 2 blog posts (P1 + P3). LinkedIn adaptations. Newsletter edition. |
| Week 3 | 2 blog posts (P1 + P2 or P3). LinkedIn adaptations. |
| Week 4 | 1 blog post (P4). LinkedIn adaptation. Monthly review. |

**Total monthly output:** 7-8 blog posts, 7-8 LinkedIn posts, 2 newsletter editions.

**Sustainable pace note:** Quality over volume. If output quality drops, reduce to 6 posts/month and reallocate time to deeper pieces.

---

## Reality Log Capture Process

Field experiences are the raw material for content. Capture them as they happen.

### How to Capture
1. After any notable field experience (site visit, meeting, bureaucratic encounter), write a 3-5 sentence note.
2. Save to `I-insights/reality-logs/[date]-[slug].md`
3. Include: what happened, what surprised you, what you learned.
4. Tag with likely pillar (P1-P4).

### How to Use
- Review reality-logs/ weekly during content planning.
- Select the most relevant experiences for the upcoming week's content.
- Reality Logs (Format 1) draw directly from these notes.
- Case Files (Format 5) may combine multiple reality logs into a longer narrative.
