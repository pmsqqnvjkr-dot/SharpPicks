# Sharp Journal Article Spec

**Version:** 1.0 (May 2026)
**Status:** Locked. All Sharp Journal articles must match this spec.
**Reference render:** `sharp-journal-locked.html`
**Component target:** `<SharpJournalArticle />` in both `~/Projects/SharpPicks` (iOS) and `~/Projects/evan_cole_hq` (web)

---

## What this spec covers

Every Sharp Journal article (morning edition, evening edition, Field Guide piece, How It Works explainer, editorial commentary) renders with these locked patterns. New article types do not get new patterns. If a pattern is not in this spec, it does not exist.

---

## Locked elements

### 1. Reading progress bar

- Always rendered at the top of every article view
- 2px height, full width
- Track: `var(--sp-surface-2)`
- Fill: `var(--sp-green)` at the percentage of article scroll position
- Sticky to top of viewport, z-index 50

### 2. Nav bar

- "Back to SHARP JOURNAL" uppercase mono, 12px, letter-spacing 0.24em
- Back chevron at left, 32x32 tap target
- Bottom border: `var(--sp-border)` 1px

### 3. Article meta line

Format: `[Content tag] · Sharp Journal · [N] min read`

- Content tag colors locked by category (see content tag taxonomy below)
- Middle dots in `var(--sp-text-5)` for visual lightness
- Meta text in JetBrains Mono 11px, `var(--sp-text-3)`
- Margin-bottom 18px

### 4. Article H1 (headline)

- IBM Plex Serif, weight 700, size 30px
- Line-height 1.18, letter-spacing -0.012em
- Color: `var(--sp-text)`
- One H1 per article (the headline)
- Forbidden: hyphens-as-separators, em-dashes, exclamation marks, all-caps emphasis

### 5. Date line

- Locked format: `Mon DD, YYYY` (e.g. "Feb 25, 2026")
- If timestamp matters: `Mon DD, YYYY · HH:MM AM ET`
- JetBrains Mono 11px, `var(--sp-text-3)`, letter-spacing 0.06em

### 6. Byline

- Format: `By [Name] · [Title]`
- For Evan: `By Evan Cole · Head of Signal Intelligence` (the title is locked verbatim)
- JetBrains Mono 11px, `var(--sp-text-3)`
- Name in `var(--sp-text-2)`, weight 500
- Margin-bottom 28px (creates breathing room before lede paragraph)

### 7. Section dividers

- Thin horizontal rule, `var(--sp-border)` (8% white opacity)
- Margin: 32px top and bottom
- Always appears before every H2
- Never appears before H3 (sub-sections sit closer to their parent H2)

### 8. Article H2 (section header)

- IBM Plex Serif, weight 600, size 22px
- Line-height 1.25, letter-spacing -0.005em
- Color: `var(--sp-text)`
- Margin-bottom 14px
- Use case: new section of the article

### 9. Article H3 (sub-section header)

- IBM Plex Serif, weight 600, size 17px
- Line-height 1.3
- Color: `var(--sp-text)`
- Margin-top 22px (sits closer to body, not to a divider)
- Margin-bottom 10px
- Use case: sub-topic within a section, narrower than an H2 deserves

### 10. Body copy

- IBM Plex Serif, weight 400, size 16px
- Line-height 1.6
- Color: `var(--sp-text-2)` (78% opacity for reading comfort over long paragraphs)
- Margin-bottom 18px between paragraphs
- Inline emphasis:
  - `<strong>` renders in `var(--sp-text)` full opacity, weight 600
  - `<em>` renders italic in `var(--sp-text)`
  - `<code>` renders in JetBrains Mono 14px on a dark surface background, padding 1x6px

### 11. Inline stat highlights

For numerical values that earn their own visual weight:

```html
<span class="stat">+1.5</span>           <!-- neutral -->
<span class="stat green">+2.0</span>     <!-- positive value -->
<span class="stat negative">-3.4</span>  <!-- negative value -->
```

JetBrains Mono, 0.92em (slightly smaller than body), background `rgba(255,255,255,0.04)`, padding 1x5px. Use sparingly. Over-using stats turns prose into a data dump.

### 12. Sharp Principle pull-quote

LOCKED PATTERN. Every Sharp Journal article that surfaces a brand principle uses this exact construction:

```html
<div class="sharp-principle">
  <div class="sharp-principle-eyebrow">Sharp Principle</div>
  <div class="sharp-principle-quote">[The principle text in italic IBM Plex Serif.]</div>
</div>
```

- Background: `var(--sp-green-soft)` (12% green tint)
- Border-left: 3px solid `var(--sp-green)`
- Border-radius: `0 12px 12px 0`
- Padding: 22px 24px
- Margin: 28px 0 (significant breathing room above and below)
- Eyebrow: JetBrains Mono 10px, green, "Sharp Principle" (always exactly these words)
- Quote: IBM Plex Serif 19px ITALIC weight 400 (matches home screen pattern)
- Line-height 1.45

Voice rules for principle quotes:

- Two sentences maximum
- Declarative, not aspirational
- No first-person pronouns ("I/we") because principles are universal
- Examples: "Discipline compounds. Variance does not." / "One pick beats five." / "Pass days are not missed opportunities. They are proof the system is working."

### 13. Observation callout (mid-article aside)

For analytical observations that interrupt the main argument:

```html
<div class="observation">
  <div class="observation-eyebrow">Observation</div>
  <div class="observation-text">[Aside content in IBM Plex Serif 14px regular.]</div>
</div>
```

- Background: `var(--sp-green-soft)`
- Border-left: 2px solid `var(--sp-green)` (thinner than Sharp Principle)
- Padding: 16px 20px
- Margin: 24px 0
- Eyebrow: JetBrains Mono 9px green, "Observation"
- Body: IBM Plex Serif 14px, NOT italic (Observation is analytical, not aphoristic)

Use case: specific data point or example that supports the surrounding argument. Not for principles. Not for storytelling. For observations.

### 14. Pull quote (rare, editorial drama only)

For headlines-within-the-article moments. Used in editorial pieces, not in Field Guide / How It Works content:

```html
<div class="pull-quote">[Centered serif statement, 22px weight 600.]</div>
```

- No background, no border, no eyebrow
- Centered text
- IBM Plex Serif 22px weight 600
- Margin: 32px 0

Use sparingly. One pull-quote per article maximum. If the article does not need editorial drama, skip it.

### 15. WHY THIS MATTERS footer (REQUIRED)

LOCKED. Every article ends with this card. No exceptions for educational/reference content. Editorial commentary may use a different concluding pattern but most articles get this footer.

```html
<div class="why-matters">
  <div class="why-matters-eyebrow">Why this matters</div>
  <div class="why-matters-text">[1-2 sentence takeaway.]</div>
</div>
```

- Background: `var(--sp-surface)` (NOT green; this is a closing card, not an editorial moment)
- Border: 1px solid `var(--sp-border)`
- Border-radius: 12px
- Padding: 20px 22px
- Margin-top: 36px
- Eyebrow: JetBrains Mono 10px, "Why this matters" (always exactly these words)
- Body: IBM Plex Serif 15px, full opacity text, line-height 1.5

Voice rules for the takeaway:

- One or two sentences maximum
- Connects the article content to the user's actual decision-making or trust
- Not a summary of the article
- Examples: "Understanding how the system works builds the trust needed to follow it through variance." / "Pass days are signals, not silence." / "If you can spot it before the model fires, you understand the model."

### 16. Cross-edition link

When linking morning to evening editions, or "read next" suggestions:

```html
<a class="cross-link" href="...">
  <div class="cross-link-content">
    <div class="cross-link-eyebrow">Read next</div>
    <div class="cross-link-title">[Title of the linked article.]</div>
  </div>
  <svg class="cross-link-arrow">></svg>
</a>
```

- Background: `var(--sp-surface)` with 1px border
- Padding: 16px 20px
- Eyebrow color: `var(--sp-blue)` (cross-content links use blue, distinct from green editorial accents)
- Title: IBM Plex Serif 14px weight 600

### 17. Article footer

- Below the cross-link
- Top border: 1px solid `var(--sp-border)`
- Padding-top 18px
- Centered text, JetBrains Mono 10px, uppercase, letter-spacing 0.16em
- Color: `var(--sp-text-4)` (very muted)
- Format: `Updated [Date] · [Content type] [version]`
- Examples: `Updated Feb 25, 2026 · Field Guide v1.0` / `Published May 7, 2026 · Morning Edition`

---

## Content tag taxonomy

Every article gets exactly one content tag. Color is locked per category.

| Tag | Color | When to use |
|---|---|---|
| `How it works` | Signal Blue | System mechanics, methodology, technical explanations |
| `Field Guide` | Edge Green | Educational discipline content, principles, framing |
| `Editorial` | Calibration Amber | Opinion pieces, market commentary, time-sensitive takes |
| `Morning Edition` | Edge Green | Daily Sharp Journal morning recap |
| `Evening Edition` | Edge Green | Daily Sharp Journal evening recap with results |

The tag color must match the category. Do not invent new tags. If a piece does not fit a category, the writer rewrites the piece, not the spec.

---

## Voice rules (locked)

These apply to all article copy without exception.

### Forbidden

- Em-dashes. Use periods or restructure the sentence.
- ASCII hyphens flanked by spaces (e.g. `bet - finding edges`). This is em-dash work without the em-dash. Forbidden. Use a colon or period.
- Exclamation marks. Zero exceptions.
- Emoji. Anywhere. Ever.
- All-caps emphasis in body copy. Use `<strong>` instead.
- AI-speak: "let's dive in," "happy to help," "great question," "it's worth noting," "in conclusion."
- Gambling slang: "lock," "hammer," "smash," "cash," "bag," "tail."
- Hype words: "incredible," "huge," "massive," "fire," "loaded," "elite."
- Vague claims: "the market eventually adjusts," "over time things work out." Replace with falsifiable timing or thresholds.

### Required

- Bloomberg analyst register, not ESPN personality.
- Specific over general: "10 of 14 edges on dogs" not "lots of underdog action."
- Falsifiable claims: name the timeframe, the threshold, the methodology.
- Short sentences when possible. Do not pad for length.
- Cut every word that does not earn its place.

### Hyphen replacement examples

| Forbidden | Locked |
|---|---|
| "Closing Line Value - What It Is" | "Closing line value: what it is." |
| "to do - finding real edges" | "to do: finding real edges" |
| "the line at game time - the closing line - reflects" | "the line at game time, called the closing line, reflects" |
| "How We Use It" | "How we use it." (sentence case + period for declarative tone) |

### Heading capitalization

- Sentence case in headlines and sub-headers. Not Title Case. Not ALL CAPS.
- End headlines with a period when they are declarative statements. Skip the period when the heading is a noun phrase or question.
- Example: "Closing line value: what it is." (declarative, period) vs. "How we use it." (declarative, period) vs. "A note on sample size" (noun phrase, no period).

---

## Heading hierarchy guidance

The spec locks the styles, not the count. Articles use whatever depth their content needs.

- Most articles use H1 + H2 only. Two levels, clean structure.
- Use H3 when an H2 section has multiple distinct sub-topics that earn their own headers. If a section is one topic, no H3 needed.
- Never use H4 or deeper. If you need H4, the article is structured wrong. Restructure or split into two articles.
- Never use multiple H1s. One headline per article. Multiple H1s break SEO and screen reader navigation.

---

## Length guidance

| Content type | Target read time | Word count range |
|---|---|---|
| Field Guide | 3-5 min | 600-1000 |
| How it works | 2-4 min | 400-800 |
| Editorial | 2-3 min | 400-600 |
| Morning Edition | 4-6 min | 800-1200 |
| Evening Edition | 4-6 min | 800-1200 |

If an article exceeds these ranges, ask whether it should be split into two pieces or whether sections can be cut. Long articles dilute the institutional voice. Every sentence must earn its place.

---

## Implementation notes for Claude Code

When building the `<SharpJournalArticle />` component:

1. Reference `sharp-journal-locked.html` for exact CSS values
2. All colors must come from `tokens.css` (no hardcoded hex)
3. Sharp Principle component (`<SharpPrinciple>`) renders ONLY with italic IBM Plex Serif. If the implementation strips italic styling, this is a brand-breaking bug.
4. Why This Matters footer (`<WhyThisMatters>`) is a required terminal block. The article container template renders it automatically based on article frontmatter. Do not allow articles to skip it.
5. Section dividers render automatically before each H2. Do not require article writers to insert them manually.
6. Reading progress bar is a single component (`<ReadingProgressBar>`) bound to scroll position via `IntersectionObserver` or scroll event listener, throttled to 60fps.
7. Voice rules are enforced at content authoring time, not at render time. The article CMS or markdown linter should reject submissions containing em-dashes, exclamation marks, etc.

---

## Changelog

- v1.0 (May 7, 2026): Initial locked spec. Codifies patterns from the existing CLV article and the locked design system v1.1.
