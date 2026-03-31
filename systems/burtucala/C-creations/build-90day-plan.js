const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
  ExternalHyperlink
} = require("docx");

// --- Colors ---
const DARK = "1A1A2E";
const ACCENT = "E94560";
const ACCENT2 = "0F3460";
const LIGHT_BG = "F5F5F5";
const TABLE_HEADER = "1A1A2E";
const TABLE_HEADER_TEXT = "FFFFFF";
const TABLE_ALT = "F0F4F8";
const BORDER_COLOR = "D0D0D0";
const GREEN = "27AE60";
const ORANGE = "E67E22";
const RED_SOFT = "E74C3C";

const border = { style: BorderStyle.SINGLE, size: 1, color: BORDER_COLOR };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorders = {
  top: { style: BorderStyle.NONE, size: 0 },
  bottom: { style: BorderStyle.NONE, size: 0 },
  left: { style: BorderStyle.NONE, size: 0 },
  right: { style: BorderStyle.NONE, size: 0 },
};
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };
const PAGE_WIDTH = 12240;
const MARGIN = 1440;
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN; // 9360

// --- Helpers ---
function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: TABLE_HEADER, type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: TABLE_HEADER_TEXT, font: "Arial", size: 20 })] })],
  });
}

function cell(text, width, opts = {}) {
  const runs = Array.isArray(text)
    ? text
    : [new TextRun({ text, font: "Arial", size: 20, bold: opts.bold || false, color: opts.color || DARK })];
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ alignment: opts.align || AlignmentType.LEFT, children: runs })],
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 36, color: DARK })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 160 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 28, color: ACCENT2 })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 24, color: ACCENT })],
  });
}

function para(textOrRuns, opts = {}) {
  const children = Array.isArray(textOrRuns)
    ? textOrRuns
    : [new TextRun({ text: textOrRuns, font: "Arial", size: 22, color: DARK })];
  return new Paragraph({
    spacing: { after: 120 },
    alignment: opts.align || AlignmentType.LEFT,
    children,
  });
}

function bold(text) {
  return new TextRun({ text, bold: true, font: "Arial", size: 22, color: DARK });
}

function normal(text) {
  return new TextRun({ text, font: "Arial", size: 22, color: DARK });
}

function accent(text) {
  return new TextRun({ text, bold: true, font: "Arial", size: 22, color: ACCENT });
}

function bulletItem(textOrRuns) {
  const children = Array.isArray(textOrRuns)
    ? textOrRuns
    : [new TextRun({ text: textOrRuns, font: "Arial", size: 22, color: DARK })];
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60 },
    children,
  });
}

function spacer() {
  return new Paragraph({ spacing: { after: 80 }, children: [] });
}

function divider() {
  return new Paragraph({
    spacing: { before: 200, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 1 } },
    children: [],
  });
}

// --- Build Document ---
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: DARK },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: ACCENT2 },
        paragraph: { spacing: { before: 300, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: ACCENT },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_WIDTH, height: 15840 },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: ACCENT, space: 4 } },
          children: [
            new TextRun({ text: "BURTUCALA ", bold: true, font: "Arial", size: 18, color: ACCENT }),
            new TextRun({ text: "90-Day Marketing Pivot", font: "Arial", size: 18, color: "888888" }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 2, color: BORDER_COLOR, space: 4 } },
          children: [
            new TextRun({ text: "Confidential ", font: "Arial", size: 16, color: "999999", italics: true }),
            new TextRun({ text: "| Page ", font: "Arial", size: 16, color: "999999" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "999999" }),
          ],
        })],
      }),
    },
    children: [
      // === COVER / TITLE ===
      new Paragraph({ spacing: { before: 2400 }, children: [] }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [new TextRun({ text: "BURTUCALA", bold: true, font: "Arial", size: 56, color: ACCENT })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [new TextRun({ text: "90-Day Marketing Pivot", font: "Arial", size: 40, color: DARK })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 80 },
        children: [new TextRun({ text: "Red-Teamed & Optimized", font: "Arial", size: 28, color: ACCENT2 })],
      }),
      divider(),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [new TextRun({ text: "March 25, 2026", font: "Arial", size: 22, color: "666666" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [new TextRun({ text: "Based on Burtucala Portal Meeting Analysis", font: "Arial", size: 20, color: "888888", italics: true })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 },
        children: [new TextRun({ text: "Asaf Eyzenkot + Noam Perets", font: "Arial", size: 22, color: DARK })],
      }),

      // === CONTEXT ===
      new Paragraph({ children: [new PageBreak()] }),
      h1("Context"),
      para([
        bold("Meeting: "),
        normal("Burtucala Portal Ongoing (March 25, 2026, 64 min)"),
      ]),
      para([
        bold("Participants: "),
        normal("Asaf Eyzenkot + Noam Perets"),
      ]),
      para([
        bold("Core outcome: "),
        normal("3-month ultimatum (April-June). July 1st = go/no-go decision on Burtucala's future."),
      ]),
      spacer(),
      para("Both partners agree: the current content-heavy approach (8 articles/month, LinkedIn posts, Facebook group engagement) is structurally sound but emotionally flat."),
      spacer(),
      para([
        bold("Asaf's diagnosis: "),
        accent("\"It's mild, boring, lacking audacity. No pepper, no boldness. No conversion.\""),
      ]),
      spacer(),
      para("The strategy needs a Purple Cow transformation. Paulo agent is a separate workstream under RealizeOS, not part of this marketing plan."),

      // === STRATEGIC INSIGHT ===
      divider(),
      h1("The Strategic Insight"),
      para([bold("What Burtucala IS doing: "), normal("Publishing useful content that explains Portugal's business landscape to foreigners. Good SEO. Good structure. Professional voice.")]),
      spacer(),
      para([bold("What every other Portugal consultant is also doing: "), normal("Exactly the same thing. Articles about AL licenses. Posts about golden visas. \"Helpful tips for expats.\" The market is flooded with informational content.")]),
      spacer(),
      para([bold("What nobody is doing: "), normal("Making people FEEL the problem. Hitting the emotional nerve. Being the one brand that says \"I'll show you what a \u20AC200K mistake looks like\" instead of \"here are 5 tips for your renovation.\"")]),
      spacer(),
      new Paragraph({
        spacing: { before: 160, after: 160 },
        indent: { left: 480, right: 480 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 8 } },
        children: [
          new TextRun({ text: "The Purple Cow formula: ", bold: true, font: "Arial", size: 22, color: ACCENT }),
          new TextRun({ text: "Take your biggest strength (brutal honesty + real operational experience) and AMPLIFY it to a level that makes competitors uncomfortable.", font: "Arial", size: 22, color: DARK, italics: true }),
        ],
      }),

      // === RED TEAM ANALYSIS ===
      new Paragraph({ children: [new PageBreak()] }),
      h1("Red Team Analysis"),
      para("Each idea was stress-tested against: market resistance, people's feelings, cultural fit, realistic effort, and failure scenarios."),

      // --- IDEA 1: Anti-Pitch ---
      divider(),
      h2("IDEA #1: \"The Anti-Pitch\" (Contrarian LinkedIn Series)"),
      para([bold("Value-for-Effort: "), accent("\u2605\u2605\u2605\u2605\u2605")]),
      spacer(),
      para([bold("Concept: "), normal("Weekly LinkedIn posts where Asaf dismantles commonly repeated Portugal investment advice with data and experience. Provocative headlines, contrarian takes.")]),
      spacer(),
      h3("Red Team Challenges"),

      // Anti-Pitch risk table
      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 800, 6360],
        rows: [
          new TableRow({ children: [headerCell("Risk", 2200), headerCell("Severity", 800), headerCell("Analysis & Fix", 6360)] }),
          new TableRow({ children: [
            cell("Contrarian fatigue", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("If every post is \"everyone is wrong,\" Asaf looks like a perpetual critic. Fix: Alternate 2 contrarian / 2 constructive posts per month. Contrarian hook draws attention; constructive follow-up builds trust.", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Small community backlash", 2200, { bold: true }),
            cell([new TextRun({ text: "Med-High", bold: true, font: "Arial", size: 20, color: RED_SOFT })], 800),
            cell("Portugal's expat investment scene is tight. Calling out common advice indirectly calls out specific people. Fix: NEVER target people or companies. Target IDEAS and ASSUMPTIONS only. \"This common assumption costs investors \u20AC40K\" is bold. \"Real estate agents mislead you\" is hostile.", 6360),
          ]}),
          new TableRow({ children: [
            cell("Algorithm shelf life", 2200, { bold: true }),
            cell("Low", 800, { color: GREEN }),
            cell("LinkedIn posts disappear in 24-48h. Fix: Repurpose each Anti-Pitch as video clip, newsletter section, and blog reference. Create a flywheel.", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Comment section control", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("Provocative posts attract angry comments. Fix: Asaf must engage 15 min/day on post days. Never defensive. Turn debate into proof of expertise.", 6360),
          ]}),
        ],
      }),
      spacer(),
      para([accent("Verdict: PASSES"), normal(" with guardrails: alternate contrarian/constructive, target ideas not people, 15 min/day comment engagement, every post ends with value.")]),
      spacer(),
      para([bold("Monthly time cost: "), normal("3-4 hours (4 posts x 45 min + comment engagement)")]),
      para([bold("Cost: "), normal("Zero")]),

      // --- IDEA 2: 200K Mistake ---
      divider(),
      h2("IDEA #2: \"\u20AC200K Mistake\" (Video Series)"),
      para([bold("Value-for-Effort: "), accent("\u2605\u2605\u2605\u2605")]),
      spacer(),
      para([bold("Concept: "), normal("3 short videos (3-5 min each) telling anonymized stories of Portugal ventures that went wrong. Specific numbers, real consequences.")]),
      spacer(),
      h3("Red Team Challenges"),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 800, 6360],
        rows: [
          new TableRow({ children: [headerCell("Risk", 2200), headerCell("Severity", 800), headerCell("Analysis & Fix", 6360)] }),
          new TableRow({ children: [
            cell("Fear-mongering perception", 2200, { bold: true }),
            cell([new TextRun({ text: "Med-High", bold: true, font: "Arial", size: 20, color: RED_SOFT })], 800),
            cell("Fear works ONLY when paired with a credible solution. The ICP (35-55, risk-averse) responds to \"someone who understands my fear and shows me a way through.\" Fix: Structure every video as 40% fear / 60% solution. Always end with \"here's what prevents this.\"", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Authenticity doubts", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("Anonymized stories might seem fabricated. Fix: Use composite stories (blend multiple real situations). Add disclaimer: \"Based on patterns from multiple projects.\" Asaf's calm delivery adds credibility.", 6360),
          ]}),
          new TableRow({ children: [
            cell("Production quality", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("Too amateur undermines Burtucala's professional positioning. Fix: Phone camera is fine, but invest in a \u20AC30 lapel mic. Natural light. The bar is \"would I share this on LinkedIn?\" not Netflix.", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Content exhaustion", 2200, { bold: true }),
            cell("Low", 800, { color: GREEN }),
            cell("Fix: Cap at 3 videos not 5. Each covers a DIFFERENT mistake type: (1) licensing/legal, (2) financial/capex, (3) operational/design. Three is a series. Five is a rut.", 6360),
          ]}),
          new TableRow({ children: [
            cell("Makes Portugal look bad?", 2200, { bold: true }),
            cell("Low", 800, { color: GREEN }),
            cell("Message is \"Portugal is great IF you do it right.\" It's pro-Portugal, anti-stupidity. The ICP is already worried about these risks. Acknowledging them builds trust.", 6360, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      para([accent("Verdict: PASSES"), normal(" refined to 3 videos (not 5), 40% fear / 60% solution structure, lapel mic required, composite stories with disclaimer.")]),
      spacer(),
      para([bold("Total time cost: "), normal("5-6 hours for all 3 videos (then done, evergreen content)")]),
      para([bold("Cost: "), normal("\u20AC30 one-time (lapel mic)")]),

      // --- IDEA 3: Live Deal Review ---
      divider(),
      h2("IDEA #3: \"Live Deal Review\" (formerly \"Hot Seat\")"),
      para([bold("Value-for-Effort: "), accent("\u2605\u2605\u2605\u2605")]),
      spacer(),
      para([bold("Concept: "), normal("Monthly live session where 2-3 entrepreneurs present their Portugal venture concept. Asaf gives real-time, honest, numbers-based feedback on camera.")]),
      spacer(),
      h3("Critical Rebranding Note"),
      new Paragraph({
        spacing: { before: 80, after: 160 },
        indent: { left: 480, right: 480 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: ACCENT2, space: 8 } },
        children: [
          new TextRun({ text: "Renamed from \"The Hot Seat\" to \"Burtucala Live Deal Review\" or \"Open Office Hours.\" ", bold: true, font: "Arial", size: 22, color: ACCENT2 }),
          new TextRun({ text: "The framing is \"free expert analysis\" not \"public roasting.\" This is critical for getting applicants.", font: "Arial", size: 22, color: DARK }),
        ],
      }),

      h3("Red Team Challenges"),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 800, 6360],
        rows: [
          new TableRow({ children: [headerCell("Risk", 2200), headerCell("Severity", 800), headerCell("Analysis & Fix", 6360)] }),
          new TableRow({ children: [
            cell("Nobody applies", 2200, { bold: true }),
            cell([new TextRun({ text: "HIGH", bold: true, font: "Arial", size: 20, color: RED_SOFT })], 800),
            cell("The ICP (35-55, risk-averse) won't seek public vulnerability. \"Hot Seat\" is intimidating. Fix: Rebrand to \"Live Deal Review.\" Value prop = FREE EXPERT ANALYSIS, not scrutiny. Pre-screen via form. 5-min pre-call with each participant to build comfort.", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Low attendance", 2200, { bold: true }),
            cell([new TextRun({ text: "HIGH", bold: true, font: "Arial", size: 20, color: RED_SOFT })], 800),
            cell("Niche audience, no webinar track record. Getting 15+ is ambitious. Fix: Set real target at 8-12 for session #1. Position as \"intimate session, limited seats.\" Personal invitations from LinkedIn/email. 8 engaged > 30 passive.", 6360),
          ]}),
          new TableRow({ children: [
            cell("Cultural sensitivity", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("Israelis handle directness; Brits/Dutch/Germans may not. Fix: Pre-call sets expectations. Asaf's natural style is respectful: he quantifies, doesn't mock.", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Effort underestimated", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("It's NOT \"just show up.\" Need: application form, screening, prep, hosting, follow-up, clip editing. Reality: 4-5 hours per session. Half-day per month. Still worth it for qualified leads.", 6360),
          ]}),
          new TableRow({ children: [
            cell("No follow-up path", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("Fix: Every reviewed participant gets personal follow-up within 24h. Non-selected applicants get Fit Call invitation. Both groups convert.", 6360, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      para([accent("Verdict: PASSES"), normal(" with significant reframing: rename to \"Live Deal Review,\" pre-call with presenters, target 8-12 for session #1, structured follow-up for ALL applicants, EN first (HE only if EN works).")]),
      spacer(),
      para([bold("Monthly time cost: "), normal("5 hours per session (screening, prep, live, follow-up)")]),
      para([bold("Cost: "), normal("Zero (Zoom/Meet)")]),

      // --- ELIMINATED: Walk & Talk ---
      divider(),
      h2("ELIMINATED: \"Walk & Talk\" (Physical Pop-Ups)"),
      para([bold("Value-for-Effort: "), new TextRun({ text: "\u2605\u2605\u2605 (eliminated)", font: "Arial", size: 22, color: "999999" })]),
      spacer(),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 800, 6360],
        rows: [
          new TableRow({ children: [headerCell("Risk", 2200), headerCell("Severity", 800), headerCell("Why It Fails", 6360)] }),
          new TableRow({ children: [
            cell("Wrong audience", 2200, { bold: true }),
            cell([new TextRun({ text: "HIGH", bold: true, font: "Arial", size: 20, color: RED_SOFT })], 800),
            cell("Coworking spaces are full of digital nomads, not investors with \u20AC150K-2M. The ICP isn't at NomadX. They're in their apartments doing research or not in Portugal yet.", 6360, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("Uncontrollable variables", 2200, { bold: true }),
            cell([new TextRun({ text: "HIGH", bold: true, font: "Arial", size: 20, color: RED_SOFT })], 800),
            cell("Filming permissions, ambient noise, people who don't approach, conversations that go nowhere. Ratio of usable content to wasted time could be terrible.", 6360),
          ]}),
          new TableRow({ children: [
            cell("Brand positioning risk", 2200, { bold: true }),
            cell("Medium", 800, { color: ORANGE }),
            cell("\"Guy with a sign at a cafe\" could read as desperate rather than audacious. The line between bold and weird is thin.", 6360, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      para([accent("Alternative if you still want physical presence: "), normal("Pre-announced \"Burtucala Office Hours\" at a fixed location, with a booking link. People sign up for 15-min slots. Only happens if enough sign up. Consider as Month 3 experiment ONLY if the other 3 ideas are generating traction.")]),

      // === FINAL 3 RANKED ===
      new Paragraph({ children: [new PageBreak()] }),
      h1("Final 3 Campaigns, Ranked"),
      para("Ranked by value-for-effort. Together they form a natural funnel."),
      spacer(),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [600, 2200, 1200, 2400, 2960],
        rows: [
          new TableRow({ children: [
            headerCell("#", 600),
            headerCell("Campaign", 2200),
            headerCell("Value/Effort", 1200),
            headerCell("Role in Funnel", 2400),
            headerCell("Monthly Cost", 2960),
          ]}),
          new TableRow({ children: [
            cell("1", 600, { bold: true, align: AlignmentType.CENTER }),
            cell("The Anti-Pitch (LinkedIn)", 2200, { bold: true }),
            cell("\u2605\u2605\u2605\u2605\u2605", 1200, { color: GREEN }),
            cell("THE MAGNET: draws attention, builds audience", 2400, { shading: TABLE_ALT }),
            cell("3-4 hrs/month, \u20AC0", 2960, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("2", 600, { bold: true, align: AlignmentType.CENTER }),
            cell("\u20AC200K Mistake Videos", 2200, { bold: true }),
            cell("\u2605\u2605\u2605\u2605", 1200, { color: GREEN }),
            cell("THE TRIGGER: creates emotional urgency", 2400),
            cell("5-6 hrs TOTAL (then done), \u20AC30", 2960),
          ]}),
          new TableRow({ children: [
            cell("3", 600, { bold: true, align: AlignmentType.CENTER }),
            cell("Live Deal Review", 2200, { bold: true }),
            cell("\u2605\u2605\u2605\u2605", 1200, { color: GREEN }),
            cell("THE CONVERTER: generates qualified leads", 2400, { shading: TABLE_ALT }),
            cell("5 hrs/session, \u20AC0", 2960, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      para([bold("How they work together: "), normal("Anti-Pitch builds awareness on LinkedIn "), accent("\u2192"), normal(" \u20AC200K videos create emotional urgency "), accent("\u2192"), normal(" Live Deal Review captures qualified leads. It's a funnel, not isolated campaigns.")]),

      // === 90-DAY PLAN ===
      new Paragraph({ children: [new PageBreak()] }),
      h1("The 90-Day Battle Plan"),

      // MONTH 1
      h2("Month 1: April \u2014 \"Light the Match\""),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [800, 4560, 1200, 2800],
        rows: [
          new TableRow({ children: [headerCell("Week", 800), headerCell("Action", 4560), headerCell("Owner", 1200), headerCell("Output", 2800)] }),
          new TableRow({ children: [
            cell("1", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch post #1: \"Stop saying Portugal is cheap. Here's what things actually cost.\"", 4560), cell("Asaf", 1200), cell("LinkedIn post + engagement", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("1", 800, { align: AlignmentType.CENTER }), cell("Design Live Deal Review: format, application form, landing page", 4560), cell("Noam + Sofia", 1200), cell("Application form live", 2800),
          ]}),
          new TableRow({ children: [
            cell("2", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch post #2: \"I told 3 investors NOT to invest. Here's why.\"", 4560), cell("Asaf", 1200), cell("LinkedIn post", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("2", 800, { align: AlignmentType.CENTER }), cell("Record \u20AC200K Mistake video #1 (licensing mistake)", 4560), cell("Asaf", 1200), cell("Posted on LinkedIn + YouTube", 2800),
          ]}),
          new TableRow({ children: [
            cell("3", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch post #3 (constructive): \"The 3 checks I run before any deal.\"", 4560), cell("Asaf", 1200), cell("LinkedIn post", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("3", 800, { align: AlignmentType.CENTER }), cell("Record \u20AC200K Mistake video #2 (financial/capex mistake)", 4560), cell("Asaf", 1200), cell("Posted", 2800),
          ]}),
          new TableRow({ children: [
            cell("3", 800, { align: AlignmentType.CENTER }), cell("Promote Live Deal Review #1: LinkedIn, email list, personal DMs", 4560), cell("Noam", 1200), cell("8+ applications", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("4", 800, { align: AlignmentType.CENTER }), cell([bold("Live Deal Review #1 (EN)"), normal(" \u2014 review 2-3 concepts live")], 4560), cell("Asaf", 1200), cell("8-12 attendees", 2800),
          ]}),
          new TableRow({ children: [
            cell("4", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch post #4 (constructive): \"What a \u20AC2,800 diagnostic actually produces.\"", 4560), cell("Asaf", 1200), cell("LinkedIn post", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("4", 800, { align: AlignmentType.CENTER }), cell("Follow-up all applicants (selected + non-selected)", 4560), cell("Noam", 1200), cell("Fit Call invitations sent", 2800),
          ]}),
          new TableRow({ children: [
            cell("4", 800, { align: AlignmentType.CENTER }), cell("Publish 2 support articles (Boutique Hotel Numbers + Emails to Bureaucrats)", 4560), cell("Sofia", 1200), cell("Published on blog", 2800, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      para([bold("April targets: "), normal("4 Fit Calls booked, 1 Blueprint request, 10+ Live Deal Review applications, 3%+ LinkedIn engagement rate, 500+ combined video views")]),

      // MONTH 2
      h2("Month 2: May \u2014 \"Build the Fire\""),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [800, 4560, 1200, 2800],
        rows: [
          new TableRow({ children: [headerCell("Week", 800), headerCell("Action", 4560), headerCell("Owner", 1200), headerCell("Output", 2800)] }),
          new TableRow({ children: [
            cell("1-2", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch posts #5-#6 (1 contrarian + 1 constructive)", 4560), cell("Asaf", 1200), cell("LinkedIn posts", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("1", 800, { align: AlignmentType.CENTER }), cell("Record \u20AC200K Mistake video #3 (operational/design) \u2014 final video", 4560), cell("Asaf", 1200), cell("Posted, series complete", 2800),
          ]}),
          new TableRow({ children: [
            cell("2", 800, { align: AlignmentType.CENTER }), cell("Promote Live Deal Review #2", 4560), cell("Noam", 1200), cell("12+ applications", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("2-3", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch posts #7-#8", 4560), cell("Asaf", 1200), cell("LinkedIn posts", 2800),
          ]}),
          new TableRow({ children: [
            cell("3", 800, { align: AlignmentType.CENTER }), cell([bold("Live Deal Review #2 (EN)")], 4560), cell("Asaf", 1200), cell("12-18 attendees", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("4", 800, { align: AlignmentType.CENTER }), cell("Direct LinkedIn outreach: 30+ personal DMs to ICP contacts", 4560), cell("Noam", 1200), cell("5+ responses, 3+ Fit Calls", 2800),
          ]}),
          new TableRow({ children: [
            cell("4", 800, { align: AlignmentType.CENTER }), cell([bold("Mid-sprint check: "), normal("Are Fit Calls converting? What's working? Adjust.")], 4560), cell("Both", 1200), cell("Decision on June approach", 2800, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      para([bold("May targets: "), normal("6 Fit Calls booked (cumulative: 10), 2 Blueprint requests (cumulative: 3), 25+ Live Deal Review applications total, 1+ paid engagement started")]),

      // MONTH 3
      h2("Month 3: June \u2014 \"Prove It\""),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [800, 4560, 1200, 2800],
        rows: [
          new TableRow({ children: [headerCell("Week", 800), headerCell("Action", 4560), headerCell("Owner", 1200), headerCell("Output", 2800)] }),
          new TableRow({ children: [
            cell("1-2", 800, { align: AlignmentType.CENTER }), cell("Anti-Pitch posts #9-#12", 4560), cell("Asaf", 1200), cell("LinkedIn posts", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("2", 800, { align: AlignmentType.CENTER }), cell([bold("Live Deal Review #3 (EN)"), normal(" \u2014 with a guest co-host for amplification")], 4560), cell("Asaf", 1200), cell("20+ attendees", 2800),
          ]}),
          new TableRow({ children: [
            cell("3", 800, { align: AlignmentType.CENTER }), cell("Optional: Live Deal Review (HE) \u2014 only if EN proved the model", 4560), cell("Asaf", 1200), cell("Bonus", 2800, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("3-4", 800, { align: AlignmentType.CENTER }), cell([bold("Full metrics review. Prepare July 1st decision.")], 4560), cell("Both", 1200), cell("Go/no-go brief", 2800),
          ]}),
        ],
      }),
      spacer(),
      para([bold("June targets: "), normal("8 Fit Calls booked (cumulative: 18), 3 Blueprint requests (cumulative: 6), 40+ applications total, 1+ Sprint 0 started, \u20AC5,000+ revenue")]),

      // === JULY 1st DECISION ===
      new Paragraph({ children: [new PageBreak()] }),
      h1("July 1st Decision Framework"),
      para("The bar for Burtucala to continue:"),
      spacer(),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [3000, 3180, 3180],
        rows: [
          new TableRow({ children: [headerCell("Signal", 3000), headerCell("Minimum to Continue", 3180), headerCell("Stretch (Strong)", 3180)] }),
          new TableRow({ children: [cell("Fit Calls booked (total)", 3000, { bold: true }), cell("12+", 3180, { shading: TABLE_ALT }), cell("20+", 3180, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("Blueprint / Strategy revenue", 3000, { bold: true }), cell("\u20AC2,500+", 3180), cell("\u20AC5,000+", 3180)] }),
          new TableRow({ children: [cell("Sprint 0 engagements", 3000, { bold: true }), cell("1 started", 3180, { shading: TABLE_ALT }), cell("2+ started", 3180, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("Total service revenue", 3000, { bold: true }), cell("\u20AC5,000+", 3180), cell("\u20AC15,000+", 3180)] }),
          new TableRow({ children: [cell("Live Deal Review demand", 3000, { bold: true }), cell("30+ applications", 3180, { shading: TABLE_ALT }), cell("50+ applications", 3180, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("Qualitative signal", 3000, { bold: true }), cell("\"People recognize Burtucala\"", 3180), cell("\"People refer others to us\"", 3180)] }),
        ],
      }),
      spacer(),
      bulletItem([bold("Minimum NOT met: "), normal("Close Burtucala as discussed. Market isn't responding.")]),
      bulletItem([bold("Minimum met, stretch not: "), normal("Continue with adjustments. Model works but needs optimization.")]),
      bulletItem([bold("Stretch met: "), normal("Double down. Add Hebrew track, Operators Room, physical Office Hours.")]),

      // === ANTI-PITCH TOPICS ===
      divider(),
      h1("Anti-Pitch Topic Bank (12 Posts)"),
      para("Each post follows: Contrarian hook \u2192 Data/experience \u2192 What to do instead \u2192 Soft CTA"),
      para([normal("C = Contrarian, V = Value/Constructive. Alternating pattern.")]),
      spacer(),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [500, 800, 600, 5660, 1800],
        rows: [
          new TableRow({ children: [headerCell("#", 500), headerCell("Month", 800), headerCell("Type", 600), headerCell("Headline", 5660), headerCell("Pillar", 1800)] }),
          new TableRow({ children: [cell("1", 500, { align: AlignmentType.CENTER }), cell("Apr", 800), cell("C", 600, { color: ACCENT }), cell("\"Stop saying Portugal is cheap. Here's what things actually cost in 2026.\"", 5660, { shading: TABLE_ALT }), cell("P2: Investment", 1800, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("2", 500, { align: AlignmentType.CENTER }), cell("Apr", 800), cell("C", 600, { color: ACCENT }), cell("\"I told 3 investors this month NOT to invest. Here's why.\"", 5660), cell("P2: Investment", 1800)] }),
          new TableRow({ children: [cell("3", 500, { align: AlignmentType.CENTER }), cell("Apr", 800), cell("V", 600, { color: GREEN }), cell("\"The 3 checks I run before looking at any Portugal deal. Takes 20 minutes.\"", 5660, { shading: TABLE_ALT }), cell("P2: Investment", 1800, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("4", 500, { align: AlignmentType.CENTER }), cell("Apr", 800), cell("V", 600, { color: GREEN }), cell("\"What a \u20AC2,800 diagnostic actually produces. Full output. No secrets.\"", 5660), cell("P1: Energy", 1800)] }),
          new TableRow({ children: [cell("5", 500, { align: AlignmentType.CENTER }), cell("May", 800), cell("C", 600, { color: ACCENT }), cell("\"The AL license gold rush is over. Here's what's actually working now.\"", 5660, { shading: TABLE_ALT }), cell("P4: Biz OS", 1800, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("6", 500, { align: AlignmentType.CENTER }), cell("May", 800), cell("V", 600, { color: GREEN }), cell("\"One renovation decision saved a client \u20AC35K. It took 10 minutes.\"", 5660), cell("P3: Design", 1800)] }),
          new TableRow({ children: [cell("7", 500, { align: AlignmentType.CENTER }), cell("May", 800), cell("C", 600, { color: ACCENT }), cell("\"Your architect designs beautiful spaces that lose money. Here's the math.\"", 5660, { shading: TABLE_ALT }), cell("P3: Design", 1800, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("8", 500, { align: AlignmentType.CENTER }), cell("May", 800), cell("V", 600, { color: GREEN }), cell("\"The 4 numbers that tell you if a boutique hotel deal works.\"", 5660), cell("P2: Investment", 1800)] }),
          new TableRow({ children: [cell("9", 500, { align: AlignmentType.CENTER }), cell("Jun", 800), cell("C", 600, { color: ACCENT }), cell("\"Everyone is excited about the Algarve. The smart operators are looking elsewhere.\"", 5660, { shading: TABLE_ALT }), cell("P2: Investment", 1800, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("10", 500, { align: AlignmentType.CENTER }), cell("Jun", 800), cell("V", 600, { color: GREEN }), cell("\"How we turned a bad deal into a viable one by changing one variable.\"", 5660), cell("P3: Design", 1800)] }),
          new TableRow({ children: [cell("11", 500, { align: AlignmentType.CENTER }), cell("Jun", 800), cell("C", 600, { color: ACCENT }), cell("\"The most expensive words in Portugal RE: 'My agent said it would be fine.'\"", 5660, { shading: TABLE_ALT }), cell("P1: Energy", 1800, { shading: TABLE_ALT })] }),
          new TableRow({ children: [cell("12", 500, { align: AlignmentType.CENTER }), cell("Jun", 800), cell("V", 600, { color: GREEN }), cell("\"3 years of Portugal ventures. The 5 patterns that predict success.\"", 5660), cell("P1: Energy", 1800)] }),
        ],
      }),
      spacer(),
      h3("Guardrails for Every Post"),
      bulletItem("Target IDEAS and ASSUMPTIONS, never specific people or companies"),
      bulletItem("End with value: \"here's what to do instead\" or \"here's what works\""),
      bulletItem("Asaf engages with comments for 15 min on posting day"),
      bulletItem("No hashtag spam (3 max, per brand voice guide)"),

      // === VIDEO SPECS ===
      divider(),
      h1("\u20AC200K Mistake Video Specs"),
      para("3 videos. One per mistake category. Each follows this structure:"),
      spacer(),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [1600, 3200, 4560],
        rows: [
          new TableRow({ children: [headerCell("#", 1600), headerCell("Working Title", 3200), headerCell("Key Message", 4560)] }),
          new TableRow({ children: [
            cell("1: Licensing", 1600, { bold: true }),
            cell("\"He bought the building before checking the license.\"", 3200, { shading: TABLE_ALT }),
            cell("Municipal zoning + AL saturation = \u20AC200K trapped in an unlicensable property", 4560, { shading: TABLE_ALT }),
          ]}),
          new TableRow({ children: [
            cell("2: Financial", 1600, { bold: true }),
            cell("\"The renovation budget was \u20AC150K. The final bill was \u20AC280K.\"", 3200),
            cell("Capex underestimation without Fiscaliza\u00E7\u00E3o + contractor misalignment", 4560),
          ]}),
          new TableRow({ children: [
            cell("3: Operational", 1600, { bold: true }),
            cell("\"Beautiful space. Losing \u20AC2,400/month.\"", 3200, { shading: TABLE_ALT }),
            cell("Architect optimized for aesthetics, not revenue per sqm. No space program.", 4560, { shading: TABLE_ALT }),
          ]}),
        ],
      }),
      spacer(),
      h3("Video Structure (3-5 min each)"),
      bulletItem([bold("Hook (15 sec): "), normal("\"This investor lost \u20AC200K because of one check he skipped.\"")]),
      bulletItem([bold("The Story (90 sec): "), normal("What happened. Specific but anonymized. Numbers. Timeline.")]),
      bulletItem([bold("Root Cause (60 sec): "), normal("Why it went wrong. The assumption that killed it.")]),
      bulletItem([bold("Prevention (60 sec): "), normal("\"Here's the check that would have caught this in 30 minutes.\"")]),
      bulletItem([bold("Bridge (15 sec): "), normal("\"This is exactly what Sprint 0 diagnoses before you commit capital.\"")]),
      spacer(),
      h3("Production Requirements"),
      bulletItem("Phone camera (iPhone quality is fine)"),
      bulletItem("Lapel mic (\u20AC30, essential for audio)"),
      bulletItem("Natural light, quiet environment (cafe, office, or construction site)"),
      bulletItem("Text overlay with headline + key numbers (Sofia in CapCut or similar)"),
      bulletItem("End card: \"Don't make these mistakes. Book a Fit Call at burtucala.com\""),
      bulletItem("Distribution: LinkedIn native video, YouTube, Instagram Reels"),

      // === LIVE DEAL REVIEW PLAYBOOK ===
      new Paragraph({ children: [new PageBreak()] }),
      h1("Live Deal Review \u2014 Operational Playbook"),

      h3("Session Format"),
      bulletItem([bold("Duration: "), normal("75 min")]),
      bulletItem([bold("Participants: "), normal("2-3 presenters (pre-screened via application)")]),
      bulletItem([bold("Audience: "), normal("8-20 viewers (growing over time)")]),
      bulletItem([bold("Platform: "), normal("Zoom (allows recording + breakout rooms)")]),
      spacer(),

      h3("Session Flow"),
      bulletItem([bold("Pre-session (1 week before): "), normal("Noam screens applications, selects 2-3, does 5-min pre-call with each to set expectations")]),
      bulletItem([bold("Live (75 min): "), normal("5 min intro + ground rules \u2192 15 min per concept (5 min pitch, 10 min review) \u2192 10 min open Q&A \u2192 5 min wrap + announce next session")]),
      bulletItem([bold("Post-session (within 24h): "), normal("Personal follow-up to presenters with recommended next step. Non-selected applicants get Fit Call invitation. 2-3 highlight clips extracted for LinkedIn.")]),
      spacer(),

      h3("Application Form Fields"),
      bulletItem("Name, email, phone"),
      bulletItem("Venture type (dropdown: hotel, guesthouse, cafe/restaurant, cowork, wellness, other)"),
      bulletItem("Location (city/region in Portugal)"),
      bulletItem("Budget range (dropdown)"),
      bulletItem("Timeline (when do you want to launch?)"),
      bulletItem("Brief description (2-3 sentences)"),
      bulletItem("\"Are you comfortable with your concept being discussed in a live format?\" (consent)"),

      // === CLOSING ===
      divider(),
      new Paragraph({
        spacing: { before: 400, after: 200 },
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "April 1 \u2192 July 1", bold: true, font: "Arial", size: 32, color: ACCENT }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [
          new TextRun({ text: "90 days. 3 campaigns. Full power. No more hiding behind the keyboard.", font: "Arial", size: 24, color: DARK, italics: true }),
        ],
      }),
    ],
  }],
});

// Generate
const OUTPUT_PATH = "G:\\RealizeOS-Full-V03\\systems\\burtucala\\C-creations\\Burtucala-90-Day-Marketing-Pivot.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT_PATH, buffer);
  console.log("Created: " + OUTPUT_PATH);
});
