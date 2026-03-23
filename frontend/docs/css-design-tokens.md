# CSS Design Tokens

All v2 tokens are defined in `src/components-v2/theme/tokens.css` and loaded via the theme system. The legacy `src/styles/tokens.css` provides only minimal globals (`--bg`, `--accent`, etc.) for v1 components.

---

## Receiver Accent Tokens

The MAIN/SUB distinction is the most important semantic token pair:

```css
--v2-receiver-main-accent: #00D4FF;   /* cyan — MAIN receiver */
--v2-receiver-sub-accent:  #FF6A00;   /* orange — SUB receiver */
```

Derived border/glow pairs:
```css
--v2-vfo-main-control-border: rgba(0, 212, 255, 0.48);
--v2-vfo-main-control-glow:   rgba(0, 212, 255, 0.12);
--v2-vfo-sub-control-border:  rgba(255, 106, 0, 0.48);
--v2-vfo-sub-control-glow:    rgba(255, 106, 0, 0.12);
```

---

## Badge Tokens (`--v2-badge-*`)

Each color variant has four properties: bg, border, text, glow.

```css
/* Cyan */
--v2-badge-cyan-bg:     #0D3B66;
--v2-badge-cyan-border: #00D4FF;
--v2-badge-cyan-text:   #FFFFFF;
--v2-badge-cyan-glow:   rgba(0, 212, 255, 0.14);

/* Orange */
--v2-badge-orange-bg:     #3D2200;
--v2-badge-orange-border: #FF6A00;
--v2-badge-orange-text:   #FFF0E4;
--v2-badge-orange-glow:   rgba(255, 106, 0, 0.14);

/* Amber */
--v2-badge-amber-bg:     #3D3000;
--v2-badge-amber-border: #F2CF4A;
--v2-badge-amber-text:   #FFFAE6;
--v2-badge-amber-glow:   rgba(242, 207, 74, 0.14);

/* Red */
--v2-badge-red-bg:     #3D0A0A;
--v2-badge-red-border: #FF2020;
--v2-badge-red-text:   #FFF0ED;
--v2-badge-red-glow:   rgba(255, 32, 32, 0.14);

/* Green */
--v2-badge-green-bg:     #0A3D1A;
--v2-badge-green-border: #00CC66;
--v2-badge-green-text:   #F0FFF6;
--v2-badge-green-glow:   rgba(0, 204, 102, 0.14);

/* Muted (inactive) */
--v2-badge-muted-bg:     #1A2028;
--v2-badge-muted-border: #4D6074;
--v2-badge-muted-text:   #8DA2B8;
--v2-badge-muted-glow:   rgba(77, 96, 116, 0.10);

--v2-badge-inactive-border: #1A2028;
--v2-badge-inactive-text:   #4D6074;
```

### Per-feature badge color assignments

These map each radio feature to its badge color. Override in a theme to change the color scheme.

```css
--v2-badge-nr-color:      amber;
--v2-badge-nb-color:      amber;
--v2-badge-notch-color:   amber;
--v2-badge-anf-color:     amber;
--v2-badge-digi-sel-color: green;
--v2-badge-ip-plus-color:  cyan;
--v2-badge-att-color:     green;
--v2-badge-pre-color:     green;
--v2-badge-rfg-color:     amber;
--v2-badge-sql-color:     green;
--v2-badge-split-color:   amber;
--v2-badge-rit-color:     amber;
--v2-badge-xit-color:     amber;
--v2-badge-data-color:    cyan;
--v2-badge-default-color: cyan;
```

---

## Background Tokens (`--v2-bg-*`)

```css
--v2-bg-app:            #121720;   /* main application background */
--v2-bg-card:           #0E1420;   /* card/panel surface */
--v2-bg-input:          #151C28;   /* input field background */
--v2-bg-darker:         #060A10;   /* darker recessed areas */
--v2-bg-darkest:        #07090D;   /* deepest background */
--v2-bg-panel:          #1E252C;   /* elevated panel surface */
--v2-bg-gradient-start: #0d1117;
--v2-bg-gradient-panel: #1a1a2e;
```

---

## Border Tokens (`--v2-border-*`)

```css
--v2-border:        #243040;   /* standard border */
--v2-border-subtle: #2A3340;
--v2-border-dark:   #18202A;
--v2-border-darker: #1a2734;
--v2-border-panel:  #18222d;

/* Opacity-based borders */
--v2-border-soft:         rgba(72, 96, 122, 0.42);
--v2-border-softer:       rgba(72, 96, 122, 0.24);
--v2-border-subtle-soft:  rgba(72, 96, 122, 0.18);
--v2-border-cyan:         rgba(0, 212, 255, 0.24);
--v2-border-cyan-bright:  rgba(0, 212, 255, 0.48);
```

---

## Text Tokens (`--v2-text-*`)

```css
--v2-text-primary:   #F5F8FC;   /* main content */
--v2-text-secondary: #A0B4C8;   /* secondary content */
--v2-text-muted:     #607890;   /* de-emphasized */
--v2-text-header:    #A0B8D0;   /* section headers */
--v2-text-bright:    #F0F5FA;
--v2-text-white:     #FFFFFF;
--v2-text-light:     #d8e3f0;
--v2-text-lighter:   #EAF1F8;
--v2-text-dim:       #6F8196;
--v2-text-dimmer:    #546578;
--v2-text-disabled:  #4D6074;
--v2-text-subdued:   #8ca0b8;
--v2-text-subtle:    #7b8da1;
```

---

## Accent Tokens (`--v2-accent-*`, `--v2-indicator-*`)

```css
/* Primary accents */
--v2-accent-cyan:   #00D4FF;
--v2-accent-orange: #FF6A00;
--v2-accent-red:    #FF2020;
--v2-accent-green:  #00CC66;
--v2-accent-yellow: #F2CF4A;

/* Indicator aliases (used by button/badge color system) */
--v2-indicator-cyan:   #00D4FF;
--v2-indicator-green:  #00CC66;
--v2-indicator-amber:  #F2CF4A;
--v2-indicator-red:    #FF2020;
--v2-indicator-orange: #FF6A00;
--v2-indicator-white:  #F5F8FC;
```

---

## VFO-Specific Tokens

### Frequency display
```css
/* MAIN receiver frequency colors */
--v2-vfo-main-freq-active:        var(--v2-accent-cyan-bright);
--v2-vfo-main-freq-inactive:      var(--v2-text-muted);
--v2-vfo-main-freq-hover:         var(--v2-text-white);
--v2-vfo-main-freq-selected-bg:   var(--v2-accent-cyan);
--v2-vfo-main-freq-selected-text: var(--v2-text-white);

/* SUB receiver frequency colors */
--v2-vfo-sub-freq-active:         var(--v2-text-white);
--v2-vfo-sub-freq-inactive:       var(--v2-text-muted);
--v2-vfo-sub-freq-selected-bg:    rgba(255, 255, 255, 0.92);
--v2-vfo-sub-freq-selected-text:  var(--v2-bg-darkest);

/* Glow effects (lamp/LED/tube style) */
--v2-vfo-main-freq-glow: 0 0 12px rgba(124, 252, 229, 0.5);
--v2-vfo-sub-freq-glow:  0 0 12px rgba(255, 255, 255, 0.42);
--v2-vfo-freq-glow-intensity: 1.0;   /* 0.0–2.0 multiplier */
```

### VFO font
```css
--v2-vfo-font-family: 'Roboto Mono', monospace;
--v2-vfo-font-weight: 700;
--v2-vfo-font-style:  normal;
```
Override per theme to use 7-segment or other retro digital fonts.

### Badge backgrounds
```css
--v2-vfo-active-glow:           rgba(0, 212, 255, 0.08);
--v2-vfo-badge-active-bg:       rgba(21, 74, 34, 0.68);
--v2-vfo-badge-active-border:   rgba(61, 110, 72, 0.9);
--v2-vfo-badge-standby-bg:      rgba(20, 27, 36, 0.74);
--v2-vfo-badge-standby-border:  rgba(64, 81, 102, 0.86);
--v2-vfo-mode-badge-bg:         rgba(8, 58, 85, 0.66);
--v2-vfo-filter-badge-bg:       rgba(15, 24, 34, 0.86);
--v2-vfo-meter-tag-bg:          rgba(8, 53, 76, 0.62);
--v2-vfo-slot-tag-bg:           rgba(16, 23, 31, 0.8);
--v2-vfo-rit-label-bg:          rgba(9, 39, 56, 0.5);
--v2-vfo-rit-offset-bg:         rgba(62, 31, 7, 0.6);
--v2-vfo-rit-offset-border:     rgba(195, 126, 17, 0.82);
```

---

## Typography Tokens

```css
--v2-font-mono:           'Roboto Mono', monospace;
--v2-font-size-xs:        7px;
--v2-font-size-sm:        9px;
--v2-font-size-md:        11px;
--v2-font-size-lg:        15px;
--v2-font-size-xl:        18px;
--v2-font-size-2xl:       28px;
--v2-header-letter-spacing: 1.4px;
--v2-header-font-weight:    700;
```

---

## Spacing Tokens

```css
--v2-gap-xs:      4px;
--v2-gap-sm:      8px;
--v2-gap-md:      12px;
--v2-gap-lg:      16px;
--v2-gap-xl:      24px;
--v2-panel-padding: 12px;
--v2-panel-radius:  10px;
```

---

## Effect Tokens

### Glows
```css
--v2-glow-cyan:   0 0 8px rgba(0, 212, 255, 0.15);
--v2-glow-orange: 0 0 8px rgba(255, 106, 0, 0.15);
--v2-glow-red:    0 0 8px rgba(255, 32, 32, 0.15);
```

### Shadows
```css
--v2-shadow-sm: 0 6px 18px rgba(0, 0, 0, 0.28);
--v2-shadow-md: 0 12px 24px rgba(0, 0, 0, 0.32);
--v2-shadow-lg: 0 32px 80px rgba(0, 0, 0, 0.46);
```

---

## Theming

All tokens above are defined in the default (dark) theme. The theme system in `src/components-v2/theme/` provides override files for:

- `amoled-black`, `ayu-dark`, `catppuccin-mocha`, `catppuccin-latte`
- `dracula`, `gruvbox-dark`, `gruvbox-light`, `high-contrast`
- `nord`, `nord-light`, `one-dark`, `solarized-dark`, `solarized-light`
- `tokyo-night`, `github-light`
- **Specialty:** `crt-green`, `lcd-blue`, `nixie-tube`

Specialty themes also override `--v2-vfo-font-family` and glow intensity to match their aesthetic.

VFO-specific theme overrides live in `src/components-v2/theme/vfo-themes/`.
