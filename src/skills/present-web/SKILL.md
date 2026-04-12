---
name: clawdbrt:present-web
description: Launch the demo deck as a web slideshow using Slidev (npx, no install required)
---

# /present-web — Web Slideshow via Slidev

Launch `docs/demo-deck.mdx` as an interactive web presentation using Slidev.

## When to Use

When the user types `/clawdbrt:present-web` or asks to present the deck in a browser.

## Instructions

1. Run Slidev on the deck:

```bash
npx @slidev/cli docs/demo-deck.mdx --open
```

2. Report the local URL (default `http://localhost:3030`) and tell the user:
   - Arrow keys or space to navigate slides
   - `o` for slide overview
   - `d` for dark mode toggle
   - `f` for fullscreen

3. The process runs in the foreground. When the user is done, tell them to press `Ctrl+C` in the terminal or type "stop" to kill it.

## Critical Rules

- **No global install.** Always use `npx @slidev/cli`, never `npm install -g`.
- **No file modifications.** Slidev reads the MDX as-is. Do not convert, copy, or rename the deck.
- **Run in background** so the conversation stays alive. Use `run_in_background: true` on the Bash call.
