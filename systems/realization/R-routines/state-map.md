# State Map — Realization Portugal RE

Current state of the Portugal real estate operations. Update regularly so the AI team knows what's happening now.

**Last updated**: 2026-03-26

## Current Priorities

1. **Listing Quality Blitz** — Status: IN PROGRESS
   - Full audit completed on 8 of 11 listings (2026-03-26)
   - Optimized PT+EN descriptions ready for all 8
   - All properties below target — average quality ~58%
   - Next: Apply descriptions, add photos, add floor plans
2. **Apply Optimized Descriptions** — Status: Ready to execute
   - 8 descriptions ready (PT primary, EN secondary, HE for luxury)
   - Copy-paste into Idealista, PT as primary language
3. **Photo & Floor Plan Sprint** — Status: Not started
   - Every listing needs more photos + floor plan
   - Priority: Porto studios (8-10 photos each), Palácio De Luna (architectural photography)
4. **Refresh Stale Listings** — Status: Not started
   - 3 listings >1 month without update: Ligeiro, Combatentes, Arroios
   - Simple edit+save resets algorithm
5. **Republish Trav. Santa Maria** — Status: Description ready, needs photos
   - Inactive building (Idealista #34322355), optimized investor-focused description written
6. **Response Time Improvement** — Status: Not started
   - Target: <2 hours first response (currently ~24h)
   - Need n8n webhook for Idealista → WhatsApp notification
7. **Multi-Channel Expansion** — Status: Not started
   - Kyero registration (hero property: Baía Residence)

## Active Properties

### Bucket A: Momentum (Optimized descriptions ready, apply + amplify)

| Property | Price | Location | Quality | Updated | Contacts (30d) |
|----------|-------|----------|---------|---------|----------------|
| T4 Av. Combatentes | €495K | Setúbal | ~70% | >1mo (REFRESH) | [TBD] |
| T4 Baía Residence | €650K | Barreiro | ~72% | 8 days | [TBD] |
| Prédio R. António | €379K | Setúbal | [TBD] | [TBD] | [TBD] |

### Bucket B: Fixable (Apply descriptions + photos → monitor 30 days)

| Property | Price | Location | Quality | Updated | Key Fix |
|----------|-------|----------|---------|---------|---------|
| T1 Rua Ligeiro | €184K | Setúbal | ~55% | >1mo (REFRESH) | +photos, floor plan, area fix |
| T0 Rua do Paraíso | €230K | Porto | ~45% | 3 days | +photos (terrace!), floor plan, AL data |
| T0 João das Regras #W | €175K | Porto | ~42% | 3 days | +photos, floor plan, AL data |
| T0 João das Regras #2 | €175K | Porto | ~44% | 3 days | +photos, floor plan, AL data |
| Misericórdia | €445K | Lisbon | [TBD] | [TBD] | Not yet audited |

### Bucket I: Inactive (To republish)

| Property | Price | Location | Status |
|----------|-------|----------|--------|
| Prédio Trav. Santa Maria | €435K | Setúbal | Description ready, needs photos + floor plan before republishing |

### Bucket S: Special

| Property | Price | Location | Quality | Updated | Notes |
|----------|-------|----------|---------|---------|-------|
| T4 Palácio De Luna | €1.45M | Arroios, Lisbon | ~65% | >1mo (REFRESH) | Price FIRM. Find the right buyer, don't adjust price. |

### Bucket P: Paused

| Property | Price | Location | Status | Return Date |
|----------|-------|----------|--------|-------------|
| Douradores | €950K | Baixa, Lisbon | Under renovation | ~Aug-Sep 2026 |

## Data Gaps to Resolve

| Gap | Properties Affected | Owner |
|-----|-------------------|-------|
| Area inconsistencies | Ligeiro (50 vs 47m²), Combatentes (133 vs 120m²), Baía (169 vs 172m²) | Asaf — verify with owners/contracts |
| Floor level confusion | Porto studios (Ground floor vs Floor -1) | Asaf — verify physically |
| AL revenue data | All 3 Porto studios | Asaf — pull from Airbnb/Booking dashboards |
| Attic dimensions | Rua Ligeiro | Asaf — measure or estimate |
| Renovation cost estimate | Trav. Santa Maria building | Asaf — get contractor quote |
| Fraction letter | João das Regras #2 | Asaf — check caderneta |

## Channels

| Channel | Status | Properties Listed |
|---------|--------|-------------------|
| Idealista | Active | All except Trav. Santa Maria + Douradores |
| Kyero | Not registered | — (launch with Baía Residence) |
| realization.pt/for-sale | Not built | — (separate session) |
| Israeli network | Not active | — |

## Team

- **Asaf** — Principal, strategy, luxury leads, Israeli channel, owner relationships
- **MG** — Operations, first-responder, viewings, photo shoots, listing updates

## Key Dates

- [NOW] — Apply optimized descriptions to all 8 listings
- [This week] — Refresh 3 stale listings, verify data gaps
- [Week 2] — Photo shoots for all properties, add floor plans
- [Week 3] — Republish Trav. Santa Maria, register on Kyero
- [Week 4] — Set up n8n lead notifications
- [Month 2] — Audit Misericórdia + R. António, Hebrew brochures
- [Month 5-6] — Douradores premium relist after renovation
