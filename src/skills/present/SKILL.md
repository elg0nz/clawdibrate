---
name: clawdbrt:present
description: Present the Faros AI take-home deck interactively via chat. An ASCII cow narrates each slide. User types "next slide" to advance.
---

# /present — Faros Deck Presentation

Present the clawdibrate take-home deck one slide at a time in the terminal. An ASCII cow delivers speaker notes for each slide.

## When to Use

When the user types `/clawdbrt:present` or asks to present, rehearse, or run through the Faros deck.

## Instructions

1. Read `docs/demo-deck.mdx` from the clawdibrate repo root.
2. Split the file into slides on `\n---\n` (the MDX slide separator). The YAML frontmatter block (before the first `---`) is not a slide — skip it.
3. **Pre-generate ALL speaker notes at once** before showing anything. Write them to a list in memory — one per slide. This avoids regenerating notes on every "next slide."
4. Show slide 1 immediately. For each slide:

   **a.** Print a header:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📽  Slide N of TOTAL
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

   **b.** Print the slide content as-is (raw markdown).

   **c.** Print the pre-generated speaker notes for this slide inside a cow. Draw the cow manually as ASCII art — do NOT use cowsay or any external tool:

   ```
         -----------------------------------------------
        / First line of speaker notes wraps at about    \
        | forty-five characters per line. Keep it       |
        | punchy and conversational. Tell the presenter |
        \ what to emphasize, not what the slide says.   /
         -----------------------------------------------
                \   ^__^
                 \  (oo)\_______
                    (__)\       )\/\
                        ||----w |
                        ||     ||
   ```

   Rules for the speech bubble:
   - Top border: spaces + dashes
   - First line starts with `/` and ends with `\`
   - Middle lines start with `|` and end with `|`
   - Last line starts with `\` and ends with `/`
   - Bottom border: spaces + dashes
   - Pad all lines to the same width inside the bubble
   - If the notes are only one line, use `< single line here >` with dashes above and below

   **d.** Print `Type "next slide" to advance.` and **STOP**. Wait for user input.

5. On the **final slide**, the cow says: `"That's the last slide. Go get 'em."` — no "next slide" prompt.

## Speaker Notes Guidelines

Generate 2–4 sentences per slide. Punchy, conversational — like a coach whispering what to emphasize. Tell the presenter what to *stress*, not what the slide already says. Wrap lines at ~45 characters.

## Critical Rules

- **ONE slide at a time.** Never print multiple slides in one response.
- **Wait for user input** between every slide.
- **Pre-generate all notes on first load** so advancing is instant — no thinking delay between slides.
- **No external dependencies.** Draw the cow manually. No cowsay, no Bash.
