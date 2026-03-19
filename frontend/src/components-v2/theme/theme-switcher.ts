export interface ThemeInfo {
  id: string;
  name: string;
  preview: string[]; // 5 colors for swatch
}

const STORAGE_KEY = 'icom-lan:theme';

const THEMES: ThemeInfo[] = [
  {
    id: 'default',
    name: 'Default Dark',
    preview: ['#121720', '#00D4FF', '#FF6A00', '#00CC66', '#F2CF4A'],
  },
  {
    id: 'dracula',
    name: 'Dracula',
    preview: ['#282a36', '#8be9fd', '#ff79c6', '#50fa7b', '#f1fa8c'],
  },
  {
    id: 'nord',
    name: 'Nord',
    preview: ['#2e3440', '#88c0d0', '#81a1c1', '#a3be8c', '#ebcb8b'],
  },
  {
    id: 'catppuccin-mocha',
    name: 'Catppuccin Mocha',
    preview: ['#1e1e2e', '#89b4fa', '#cba6f7', '#a6e3a1', '#f9e2af'],
  },
  {
    id: 'solarized-dark',
    name: 'Solarized Dark',
    preview: ['#002b36', '#2aa198', '#268bd2', '#859900', '#b58900'],
  },
  {
    id: 'gruvbox-dark',
    name: 'Gruvbox Dark',
    preview: ['#282828', '#689d6a', '#d65d0e', '#b8bb26', '#fabd2f'],
  },
  {
    id: 'tokyo-night',
    name: 'Tokyo Night',
    preview: ['#1a1b26', '#7dcfff', '#7aa2f7', '#9ece6a', '#ff9e64'],
  },
  {
    id: 'one-dark',
    name: 'One Dark',
    preview: ['#282c34', '#56b6c2', '#61afef', '#98c379', '#e5c07b'],
  },
  {
    id: 'ayu-dark',
    name: 'Ayu Dark',
    preview: ['#0d1017', '#73d0ff', '#ff8f40', '#aad94c', '#e6b450'],
  },
  {
    id: 'amoled-black',
    name: 'AMOLED Black',
    preview: ['#000000', '#00e5ff', '#ff9500', '#34c759', '#ffcc00'],
  },
  {
    id: 'high-contrast',
    name: 'High Contrast',
    preview: ['#000000', '#00ffff', '#ffaa00', '#00ff00', '#ffff00'],
  },
];

export function getAvailableThemes(): ThemeInfo[] {
  return THEMES;
}

export function getTheme(): string {
  if (typeof window === 'undefined') {
    return 'default';
  }
  try {
    return localStorage.getItem(STORAGE_KEY) || 'default';
  } catch {
    return 'default';
  }
}

export function setTheme(id: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  // Validate theme ID
  if (!THEMES.some((theme) => theme.id === id)) {
    console.warn(`Unknown theme ID: ${id}`);
    return;
  }

  // Store preference
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch (err) {
    console.warn('Failed to save theme preference:', err);
  }

  // Apply to DOM
  if (id === 'default') {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = id;
  }
}
