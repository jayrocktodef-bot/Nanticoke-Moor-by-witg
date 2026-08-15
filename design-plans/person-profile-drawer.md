# Unify PersonProfileDrawer with Global Design Language

Written against: unavailable

## Evidence chain

- Surface: `frontend/src/components/PersonProfileDrawer.jsx`
- Problem: The drawer component ignores the global design language, using generic Tailwind cool-grays (`slate`), default sans-serif headers, and standard accent colors (`amber`, `sky`, `emerald`) which clash with the application's sepia/historical aesthetic.
- Design evidence: `frontend/src/index.css` establishes `--bg-main: #121110`, `--bg-surface: #1C1A17`, `--border-main: #332D27`, `--accent-brass: #C68B59`, `--accent-gold: #D4A373`, `--text-primary: #F3EBE3`, and `.font-serif-header`. `HomeScreen.jsx` implements these strictly as hardcoded Tailwind hex values (e.g. `bg-[#1C1A17]`, `border-[#332D27]`, `text-[#F3EBE3]`).
- Owner: `frontend/src/components/HomeScreen.jsx`
- Scope and affected surfaces: `PersonProfileDrawer.jsx`
- Uncertainty: None. The design contract is clear and hardcoded in the underlying canvas.

## Design decision

Replace all generic Tailwind `slate` utility classes and primary accents in the drawer with the exact hex values and typography classes established by the global design language to ensure visual continuity.

## Reuse

- Hex values established in `index.css`: `#1C1A17`, `#121110`, `#332D27`, `#26221E`, `#F3EBE3`, `#A8A096`, `#8C8275`, `#C68B59`, `#D4A373`.
- Typography class: `font-serif-header`
- Exemplar: `frontend/src/components/HomeScreen.jsx`

## Changes

1. `frontend/src/components/PersonProfileDrawer.jsx`
   - Change: Replace `bg-slate-900` with `bg-[#141210]`. Replace `border-slate-800` with `border-[#26221E]`. Replace `text-slate-400` with `text-[#A8A096]`. Replace `text-white` with `text-[#F3EBE3]`. Replace `bg-slate-950` with `bg-[#1C1A17]`. Replace `bg-slate-800` with `bg-[#2B2621]`.
   - Change: Replace primary accents `amber-500` and `amber-400` with `#C68B59` and `#D4A373` respectively.
   - Change: Apply `font-serif-header` to the `<h2>` containing the person's name.
   - Preserve: Functional relationships logic, audit warning alert red/orange semantic colors (but muted if possible via opacity), and lightbox modal structure.
   - Verify: The drawer visually matches the warm, historical sepia aesthetic of the `HomeScreen` beneath it.

## Scope

- Inherit: `PersonProfileDrawer.jsx`
- Verify: The lightbox modal inside `PersonProfileDrawer.jsx` (ensure its background is still dark/black, but border colors match the theme).
- Exclude: Semantic audit warning colors (red/orange) which should remain to indicate critical/warning states.

## Validation

- Product: Users can open a profile drawer and see the details without visual jarring.
- Interface: Open a profile drawer from the Network Graph or Command Palette. Check the header typography, background panels, kinship cards, and icon colors.
- System: Confirm no generic `slate` or `amber` classes remain on primary structural elements.
- Repository: `grep -r "slate" frontend/src/components/PersonProfileDrawer.jsx` → Should return zero results for layout/background/text elements.

## Stop conditions

- Stop if changing the `amber` or `slate` classes breaks the specific `lucide-react` icon opacity layering without an explicit hex equivalent.

## Design documentation

- After acceptance and validation: None. The implementation aligns with the existing documentation in `index.css`.
