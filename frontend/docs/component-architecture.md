# Component Architecture

This document describes the v2 design system component architecture for the icom-lan frontend.

## Button System

### `HardwareButton` — all interactive controls

The primary interactive control for the entire UI. Wraps `ControlButton` with `surface="hardware"`.

**Import:** `import { HardwareButton } from '$lib/Button'`

**Props:**
```typescript
interface HardwareButtonProps {
  active?: boolean;           // Lit/on state
  indicator?: 'dot' | 'edge-left' | 'edge-bottom';  // Default: 'dot'
  color?: 'cyan' | 'green' | 'amber' | 'red' | 'orange' | 'white';  // Default: 'cyan'
  compact?: boolean;          // Reduced size (22px vs 28px min-height)
  disabled?: boolean;
  title?: string | null;      // Tooltip text
  shortcutHint?: string | null;  // Keyboard shortcut, shown in title if no title
  onclick?: (event: MouseEvent) => void;
  children?: any;             // Button label content (Svelte snippet)
}
```

**Usage:**
```svelte
<HardwareButton active={nrEnabled} indicator="edge-left" color="amber" onclick={toggleNr}>
  NR
</HardwareButton>

<HardwareButton active={attEnabled} indicator="edge-left" color="green" compact>
  ATT
</HardwareButton>
```

**Used in:** DspPanel (NR, NB, NOTCH, ANF), TxPanel, CwPanel, RfFrontEnd (ATT, PRE, DIGI-SEL, IP+), AgcPanel, ModePanel, FilterPanel, BandSelector, RxAudioPanel.

---

### `StatusIndicator` — read-only display badges

Non-interactive status display for the VFO header. Shows mode, filter, band, slot, and DSP state.

**Import:** `import { StatusIndicator } from '$lib/Button'`

**Props:**
```typescript
interface StatusIndicatorProps {
  label: string;              // Text to display
  active?: boolean;           // Highlighted state (default: false)
  color?: 'cyan' | 'green' | 'amber' | 'orange' | 'red' | 'muted';
  size?: 'default' | 'xs';   // Default: 'default'
  title?: string | null;      // Tooltip
}
```

**Usage:**
```svelte
<StatusIndicator label={mode} active color="cyan" />
<StatusIndicator label="NR" active={nrOn} color="amber" />
<StatusIndicator label="DIGI-SEL" active={digiSelOn} color="green" />
```

**Used in:** VfoPanel control strip (MODE, FILTER, BAND, SLOT badges), VfoHeader (NR, NB, DIGI-SEL, NOTCH, ANF, ATT, PRE, IP+, RIT, XIT, SPLIT).

---

### `ControlButton` — internal base primitive

The base button component. Used internally by `HardwareButton`; do not use directly in panels.

**Props:**
```typescript
interface ControlButtonProps {
  active?: boolean;
  disabled?: boolean;
  compact?: boolean;
  surface?: 'flat' | 'hardware';
  indicatorStyle?: 'ring' | 'dot' | 'edge-bottom' | 'edge-left' | 'edge-sides' | 'fill';
  indicatorColor?: 'cyan' | 'green' | 'amber' | 'red' | 'orange' | 'white';
  glow?: 'color' | 'white' | 'warm';
  title?: string | null;
  shortcutHint?: string | null;
  onclick?: (event: MouseEvent) => void;
  children?: any;
}
```

---

### `ValueControl` — sliders and knobs

Polymorphic value control that dispatches to a renderer based on the `renderer` prop.

**Import:** `import ValueControl from '$components-v2/controls/value-control/ValueControl.svelte'`

**Props:**
```typescript
interface ValueControlProps {
  value: number;
  min: number;
  max: number;
  step: number;
  label: string;
  renderer: 'hbar' | 'bipolar' | 'knob' | 'discrete';
  onChange: (value: number) => void;

  // Optional
  defaultValue?: number;
  fineStepDivisor?: number;   // Default: 10 (for scroll/drag fine control)
  displayFn?: (v: number) => string;
  accentColor?: string;       // CSS color, default: var(--v2-accent-cyan)
  showValue?: boolean;        // Default: true
  showLabel?: boolean;        // Default: true
  compact?: boolean;
  variant?: 'modern' | 'hardware' | 'hardware-illuminated';
  disabled?: boolean;
  unit?: string;
  shortcutHint?: string | null;
  title?: string | null;

  // Knob-specific
  arcAngle?: number;          // Default: 270
  tickCount?: number;
  tickLabels?: string[];

  // Discrete-specific
  showAllTicks?: boolean;     // Default: true
  tickStyle?: 'ruler' | 'led' | 'notch';  // Default: 'ruler'
}
```

**Renderers:**
- `hbar` — horizontal bar (RF gain, squelch, PBT)
- `bipolar` — center-zero bar (PBT inner/outer, RIT offset)
- `knob` — rotary knob
- `discrete` — stepped/discrete selector

**Variants:**
- `modern` — flat dark UI (default)
- `hardware` — warm earth-tone skeuomorphic
- `hardware-illuminated` — vintage panel style with lamp glow

---

## Layout Components

### `RadioLayout`

Main application grid. 4 rows × 2 columns with responsive collapse.

**Grid rows (desktop):**
1. Status bar — 28px
2. Receiver deck — 156px (VFO panels)
3. Content row — flexible (left sidebar + spectrum)
4. Bottom dock — 112px

Collapses to single-column layout below 1024px. Uses `ResizeObserver` to track receiver deck width for compact rendering decisions.

**File:** `src/components-v2/layout/RadioLayout.svelte`

---

### `LeftSidebar`

Collapsible sidebar containing all radio control panels, organized into `CollapsiblePanel` sections:

1. **TUNING STEP** — step size, AUTO/MANUAL mode, keyboard hints
2. **RF FRONT END** → `RfFrontEnd` component (RF gain, squelch, ATT, PRE, DIGI-SEL, IP+)
3. **MODE** → `ModePanel` (SSB, CW, AM, FM, Data modes)
4. **FILTER** → `FilterPanel` (filter select, width, shape, PBT inner/outer)
5. **AGC** → `AgcPanel` (FAST, MID, SLOW, OFF)
6. **RIT / XIT** → `RitXitPanel` (toggles, offset control)
7. **BAND** → `BandSelector`

**File:** `src/components-v2/layout/LeftSidebar.svelte`

---

### `VfoPanel`

Individual VFO receiver panel (MAIN or SUB). Displays:
- Panel header: VFO label (A/B) + ACTIVE/STANDBY badge
- Header badges: BAR tag and slot tag
- S-meter (compact `LinearSMeter`)
- Frequency display (`FrequencyDisplayInteractive`)
- Optional RIT offset display
- Control strip: `StatusIndicator` badges for mode, filter, band, slot, and DSP state

Active receiver gets a glowing border in its accent color (`--v2-receiver-main-accent` or `--v2-receiver-sub-accent`).

**File:** `src/components-v2/vfo/VfoPanel.svelte`

---

## Color Scheme

| Color  | Use cases |
|--------|-----------|
| Cyan   | MAIN receiver accent, default controls, MODE, IP+, DATA badges |
| Green  | DIGI-SEL, ATT, PRE, SQL badges |
| Amber  | DSP controls (NR, NB, NOTCH, ANF), RIT, XIT, SPLIT badges |
| Orange | SUB receiver accent, NB badge |
| Red    | TX active, danger states |
| Muted  | Inactive badges |

---

## State Wiring

Radio state flows through:
- `src/components-v2/wiring/state-adapter.ts` — maps raw radio state to component props
- `src/components-v2/wiring/command-bus.ts` — dispatches user actions back to the radio

Components are pure (props in, events out). No component reads from the WebSocket directly.
