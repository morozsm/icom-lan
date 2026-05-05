// IMPORTANT: localStorage migration MUST run before any other import.
// Several stores (`layout.svelte.ts`, `theme-switcher.ts`,
// `lcd-contrast.svelte.ts`, ...) read localStorage at module init, so
// the migration has to happen before they evaluate. Putting the call
// at the top of main.ts is the only reliable ordering.
import { migrateLegacyStorage } from './lib/migrate-legacy-storage'
migrateLegacyStorage()

import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app')!,
})

export default app
