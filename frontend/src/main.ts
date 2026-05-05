// IMPORTANT: this side-effect import MUST be first.
//
// `migrate-legacy-storage` runs the v1.x → v2.x localStorage migration as a
// module-top side-effect. ES modules evaluate transitive imports BEFORE the
// importing module's body runs, so a function call here in main.ts's body
// would race against stores that read localStorage at module init
// (`layout.svelte.ts`, `theme-switcher.ts`, `lcd-contrast.svelte.ts`,
// `lcd-display-mode.svelte.ts`). By making this import the first sibling,
// its body — including the migration call — runs before any other import
// is evaluated.
import './lib/migrate-legacy-storage'

import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app')!,
})

export default app
