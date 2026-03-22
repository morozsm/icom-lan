<script lang="ts">
  import HBarRenderer from './value-control/HBarRenderer-variants.svelte';

  let value1 = $state(50);
  let value2 = $state(50);
  let value3 = $state(50);
  let value4 = $state(50);
  let value5 = $state(50);
</script>

<div class="demo-container">
  <div class="demo-header">
    <h1>HBar Variants Comparison</h1>
    <p>Hardware Illuminated slider design evolution</p>
  </div>

  <div class="demo-grid">
    <!-- Original -->
    <div class="demo-card">
      <div class="card-header">
        <h2>Original</h2>
        <span class="badge">hardware-illuminated</span>
      </div>
      <div class="slider-container">
        <HBarRenderer
          bind:value={value1}
          min={0}
          max={100}
          step={1}
          label="RF Gain"
          variant="hardware-illuminated"
          onChange={(v) => value1 = v}
          unit="%"
        />
      </div>
      <div class="description">
        <p><strong>Baseline design:</strong></p>
        <ul>
          <li>Moderate glow (0.08–0.20 opacity range)</li>
          <li>Standard metal gradient</li>
          <li>Basic shadow depth</li>
        </ul>
      </div>
    </div>

    <!-- V2 Brighter -->
    <div class="demo-card">
      <div class="card-header">
        <h2>V2: Brighter</h2>
        <span class="badge badge-v2">hw-illum-v2</span>
      </div>
      <div class="slider-container">
        <HBarRenderer
          bind:value={value2}
          min={0}
          max={100}
          step={1}
          label="RF Gain"
          variant="hw-illum-v2"
          onChange={(v) => value2 = v}
          unit="%"
        />
      </div>
      <div class="description">
        <p><strong>+50% brightness:</strong></p>
        <ul>
          <li>Oval glow: 0.12–0.30</li>
          <li>Slot glow: 0.22–1.05</li>
          <li>Element +15% lighter</li>
          <li>Stronger shadows</li>
        </ul>
      </div>
    </div>

    <!-- V3 Ultra-Bright -->
    <div class="demo-card">
      <div class="card-header">
        <h2>V3: Ultra-Bright</h2>
        <span class="badge badge-v3">hw-illum-v3</span>
      </div>
      <div class="slider-container">
        <HBarRenderer
          bind:value={value3}
          min={0}
          max={100}
          step={1}
          label="RF Gain"
          variant="hw-illum-v3"
          onChange={(v) => value3 = v}
          unit="%"
        />
      </div>
      <div class="description">
        <p><strong>×2 brightness:</strong></p>
        <ul>
          <li>Oval glow: 0.16–0.40</li>
          <li>Slot glow: 0.30–1.40 (can exceed 1.0!)</li>
          <li>Element +30% lighter</li>
          <li>Dramatic shadows</li>
        </ul>
      </div>
    </div>

    <!-- V4 Volumetric -->
    <div class="demo-card">
      <div class="card-header">
        <h2>V4: Volumetric</h2>
        <span class="badge badge-v4">hw-illum-v4</span>
      </div>
      <div class="slider-container">
        <HBarRenderer
          bind:value={value4}
          min={0}
          max={100}
          step={1}
          label="RF Gain"
          variant="hw-illum-v4"
          onChange={(v) => value4 = v}
          unit="%"
        />
      </div>
      <div class="description">
        <p><strong>Maximum 3D depth:</strong></p>
        <ul>
          <li>Multi-layer shadows (6 layers)</li>
          <li>Volumetric frame (top/bottom contrast)</li>
          <li>Center-lit gradient</li>
          <li>Bright glow: 0.14–0.39</li>
        </ul>
      </div>
    </div>

    <!-- Sync Test -->
    <div class="demo-card full-width">
      <div class="card-header">
        <h2>Synchronized Compare</h2>
        <span class="badge">All variants, same value</span>
      </div>
      <div class="sync-grid">
        <div class="sync-item">
          <p class="sync-label">Original</p>
          <HBarRenderer
            bind:value={value5}
            min={0}
            max={100}
            step={1}
            label="Sync Test"
            variant="hardware-illuminated"
            onChange={(v) => value5 = v}
            unit="%"
          />
        </div>
        <div class="sync-item">
          <p class="sync-label">V2</p>
          <HBarRenderer
            bind:value={value5}
            min={0}
            max={100}
            step={1}
            label="Sync Test"
            variant="hw-illum-v2"
            onChange={(v) => value5 = v}
            unit="%"
          />
        </div>
        <div class="sync-item">
          <p class="sync-label">V3</p>
          <HBarRenderer
            bind:value={value5}
            min={0}
            max={100}
            step={1}
            label="Sync Test"
            variant="hw-illum-v3"
            onChange={(v) => value5 = v}
            unit="%"
          />
        </div>
        <div class="sync-item">
          <p class="sync-label">V4</p>
          <HBarRenderer
            bind:value={value5}
            min={0}
            max={100}
            step={1}
            label="Sync Test"
            variant="hw-illum-v4"
            onChange={(v) => value5 = v}
            unit="%"
          />
        </div>
      </div>
    </div>
  </div>

  <div class="demo-footer">
    <p>🎛️ Drag sliders, use mouse wheel, or arrow keys to test responsiveness</p>
    <p>Double-click to reset to default (0)</p>
  </div>
</div>

<style>
  .demo-container {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0e12 0%, #141a22 100%);
    padding: 2rem;
    font-family: 'Roboto Mono', monospace;
  }

  .demo-header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .demo-header h1 {
    font-size: 2.5rem;
    color: #e0e8f0;
    margin: 0 0 0.5rem 0;
    font-weight: 600;
  }

  .demo-header p {
    font-size: 1rem;
    color: #8a9e78;
    margin: 0;
    letter-spacing: 0.05em;
  }

  .demo-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .demo-card {
    background: #0f1419;
    border: 1px solid #1a2028;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  }

  .demo-card.full-width {
    grid-column: 1 / -1;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .card-header h2 {
    font-size: 1.25rem;
    color: #c8d8a8;
    margin: 0;
    font-weight: 500;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    background: rgba(180, 140, 90, 0.15);
    color: #d2a56e;
    border: 1px solid rgba(180, 140, 90, 0.3);
    font-family: 'Roboto Mono', monospace;
  }

  .badge-v2 {
    background: rgba(220, 175, 120, 0.2);
    border-color: rgba(220, 175, 120, 0.4);
    color: #dcaf78;
  }

  .badge-v3 {
    background: rgba(255, 200, 120, 0.25);
    border-color: rgba(255, 200, 120, 0.5);
    color: #ffc878;
  }

  .badge-v4 {
    background: rgba(173, 177, 188, 0.25);
    border-color: rgba(173, 177, 188, 0.5);
    color: #adb1bc;
  }

  .slider-container {
    padding: 2rem 1rem;
    background: #080b0f;
    border-radius: 8px;
    margin-bottom: 1.5rem;
  }

  .description {
    font-size: 0.875rem;
    color: #7a8a9a;
    line-height: 1.6;
  }

  .description p {
    margin: 0 0 0.75rem 0;
  }

  .description strong {
    color: #c8d8a8;
  }

  .description ul {
    margin: 0;
    padding-left: 1.5rem;
  }

  .description li {
    margin: 0.25rem 0;
  }

  .sync-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 2rem;
    padding: 1rem;
  }

  .sync-item {
    background: #080b0f;
    border-radius: 8px;
    padding: 1.5rem 1rem;
  }

  .sync-label {
    font-size: 0.875rem;
    color: #8a9e78;
    text-align: center;
    margin: 0 0 1rem 0;
    font-weight: 500;
    letter-spacing: 0.05em;
  }

  .demo-footer {
    text-align: center;
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #1a2028;
  }

  .demo-footer p {
    font-size: 0.875rem;
    color: #7a8a9a;
    margin: 0.5rem 0;
  }

  @media (max-width: 768px) {
    .demo-header h1 {
      font-size: 1.75rem;
    }

    .demo-grid {
      grid-template-columns: 1fr;
    }

    .sync-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
