# Phase 110: Dark Mode & Theme System - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure + visual polish phase)

<domain>
## Phase Boundary

Ensure dark/light theme toggle works correctly across all pages with persistent preference. Most infrastructure already exists (next-themes, provider, CSS vars, toggle button). Focus is on auditing hardcoded colors and ensuring full dark mode coverage.

</domain>

<decisions>
## Implementation Decisions

### Theme Infrastructure
- next-themes already installed and wired in providers.tsx — reuse existing setup
- Class-based dark mode already configured in globals.css — no Tailwind config changes needed
- Theme toggle already in navbar.tsx with useTheme() — verify persistence works
- Default should respect system prefers-color-scheme (next-themes attribute="class" defaultTheme="system")

### Color Audit
- shadcn/ui components already use CSS variables — theme-aware by default
- Hardcoded hex colors found in trading-plan-panel.tsx and potentially other components — need CSS variable replacement
- Chart colors (lightweight-charts) need dark mode variants
- Use existing CSS variable pattern from globals.css (:root for light, .dark for dark)

### Agent's Discretion
All remaining implementation choices at agent's discretion — infrastructure phase with clear patterns established.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `next-themes` ThemeProvider in providers.tsx (lines 23-30)
- Theme toggle button in navbar.tsx (lines 77-90) using useTheme()
- CSS variables in globals.css (:root lines 7-53, .dark lines 100-139)
- shadcn/ui components in src/components/ui/ — already theme-aware

### Established Patterns
- Class-based dark mode via `dark:` Tailwind variants
- CSS custom properties for theme tokens (--background, --foreground, etc.)
- shadcn imports: `@import "shadcn/tailwind.css"` in globals.css

### Integration Points
- providers.tsx wraps entire app with ThemeProvider
- navbar.tsx has toggle button
- globals.css defines all theme tokens
- Hardcoded colors in: trading-plan-panel.tsx, potentially other chart/data components

</code_context>

<specifics>
## Specific Ideas

- Audit ALL components for hardcoded hex/rgb colors and replace with CSS variables
- Ensure lightweight-charts respects dark mode (background, grid, text colors)
- Verify prefers-color-scheme is respected on first visit

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
