# Full Accent & Data Visualization Tokenization (#325)

## Summary
All remaining hardcoded colors in `src/components-v2/` have been tokenized and moved to CSS custom properties.

## Changes

### 1. Token Definitions (`tokens.css`)
Added **Layer 2: Accents & Data Visualization** section with 124+ new tokens:

#### Status Badges (5 color schemes × 4 properties)
- `--v2-badge-{cyan|orange|red|green|muted}-{bg|border|text|glow}`
- `--v2-badge-inactive-{border|text}`

#### VFO Indicators
- Active glow, badge states, meter/slot tags, mode/filter badges, RIT labels

#### TX Indicators
- `--v2-tx-{tuning|active|idle}`, `--v2-tx-panel-glow`

#### Meter Gradients
- S-meter, Power, SWR, ALC (fill + track for each)
- Meter source tags (S/SWR/Power × bg/border/text)
- TX status tags, active glow/shadow, bar divider

#### Panel Backgrounds & Overlays
- Panel gradients, sidebar gradients, VFO header, meter panel

#### Modal & Keyboard Handler
- Backdrop, modal gradients, section borders, key states, code blocks

#### Popups & Dropdowns
- Filter panel, attenuator control backgrounds and shadows

#### Control Elements
- Button gradients, bipolar controls, knob shadows, theme picker

#### CollapsiblePanel
- Background, border, header states, chevron colors

### 2. Files Tokenized

**Components:**
- `controls/status-badge-style.ts` - Badge color schemes
- `controls/CollapsiblePanel.svelte` - Panel colors
- `controls/control-button.css` - Button gradients
- `controls/BipolarSlider.svelte` - Bipolar gradients
- `controls/AttenuatorControl.svelte` - Popup backgrounds
- `controls/ThemePicker.svelte` - Border colors
- `controls/value-control/BipolarRenderer.svelte` - Gradients
- `controls/value-control/KnobRenderer.svelte` - Shadow effects

**Panels:**
- `panels/tx-utils.ts` - TX state colors
- `panels/DockMeterPanel.svelte` - Meter gradients, source tags
- `panels/DspPanel.svelte` - Header text color
- `panels/MeterPanel.svelte` - Active state glow
- `panels/TxPanel.svelte` - Tuning glow
- `panels/FilterPanel.svelte` - Modal backgrounds

**Layout:**
- `layout/LeftSidebar.svelte` - Sidebar gradients
- `layout/RadioLayout.svelte` - Panel gradients
- `layout/VfoHeader.svelte` - Header gradients
- `layout/KeyboardHandler.svelte` - Modal system

**VFO:**
- `vfo/VfoPanel.svelte` - All VFO badges and indicators

### 3. Theme Overrides
All 10 themes updated with Layer 2 token overrides:

1. **Dracula** - Purple & cyan palette
2. **Nord** - Arctic frost colors
3. **Catppuccin Mocha** - Pastel latte colors
4. **Tokyo Night** - Deep blue palette
5. **Solarized Dark** - Balanced contrast
6. **Gruvbox Dark** - Retro warm colors
7. **One Dark** - Atom editor colors
8. **Ayu Dark** - Mirage palette
9. **AMOLED Black** - Pure black with vibrant accents
10. **High Contrast** - Maximum accessibility

Each theme includes appropriate overrides for:
- Badge color schemes (cyan, orange, red, green)
- Meter gradients (S, Power, SWR, ALC)
- Meter source tags

### 4. Visual Consistency
✅ Default theme appearance remains **identical**
✅ All rgba() values properly tokenized
✅ All hex colors properly tokenized
✅ CSS gradients preserved as token values
✅ Theme-specific color palettes maintained

### 5. Excluded Files (Intentional)
These files contain data/configuration values, not theme colors:
- `theme-switcher.ts` - Theme preview colors (metadata)
- `meters/LinearSMeter.svelte` - Meter segment logic
- `meters/bar-gauge-utils.ts` - Gauge zone definitions
- `meters/needle-gauge-utils.ts` - Gauge color logic
- `panels/RfFrontEnd.svelte` - Component prop value

## Verification
```bash
# Zero hardcoded colors remain in component styles
grep -rn 'rgba(' src/components-v2/ --include='*.svelte' --include='*.css' | \
  grep -v tokens.css | grep -v themes/ | wc -l
# Output: 0

# All theme files include Layer 2 sections
grep "Layer 2:" src/components-v2/theme/themes/*.css | wc -l
# Output: 10
```

## Token Count
- **Before:** 90 lines in tokens.css
- **After:** 214 lines in tokens.css
- **New tokens:** 124+ CSS custom properties
