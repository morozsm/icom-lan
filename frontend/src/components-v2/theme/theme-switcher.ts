export interface ThemeInfo {
  id: string;
  name: string;
  category: 'dark' | 'light';
  preview: string[]; // 5 colors for swatch
}

const STORAGE_KEY = 'icom-lan:theme';

const THEMES: ThemeInfo[] = [
  // Dark themes
  {
    id: 'default',
    name: 'Default Dark',
    category: 'dark',
    preview: ['#121720', '#00D4FF', '#FF6A00', '#00CC66', '#F2CF4A'],
  },
  {
    id: 'dracula',
    name: 'Dracula',
    category: 'dark',
    preview: ['#282a36', '#8be9fd', '#ff79c6', '#50fa7b', '#f1fa8c'],
  },
  {
    id: 'nord',
    name: 'Nord',
    category: 'dark',
    preview: ['#2e3440', '#88c0d0', '#81a1c1', '#a3be8c', '#ebcb8b'],
  },
  {
    id: 'catppuccin-mocha',
    name: 'Catppuccin Mocha',
    category: 'dark',
    preview: ['#1e1e2e', '#89b4fa', '#cba6f7', '#a6e3a1', '#f9e2af'],
  },
  {
    id: 'solarized-dark',
    name: 'Solarized Dark',
    category: 'dark',
    preview: ['#002b36', '#2aa198', '#268bd2', '#859900', '#b58900'],
  },
  {
    id: 'gruvbox-dark',
    name: 'Gruvbox Dark',
    category: 'dark',
    preview: ['#282828', '#689d6a', '#d65d0e', '#b8bb26', '#fabd2f'],
  },
  {
    id: 'tokyo-night',
    name: 'Tokyo Night',
    category: 'dark',
    preview: ['#1a1b26', '#7dcfff', '#7aa2f7', '#9ece6a', '#ff9e64'],
  },
  {
    id: 'one-dark',
    name: 'One Dark',
    category: 'dark',
    preview: ['#282c34', '#56b6c2', '#61afef', '#98c379', '#e5c07b'],
  },
  {
    id: 'ayu-dark',
    name: 'Ayu Dark',
    category: 'dark',
    preview: ['#0d1017', '#73d0ff', '#ff8f40', '#aad94c', '#e6b450'],
  },
  {
    id: 'amoled-black',
    name: 'AMOLED Black',
    category: 'dark',
    preview: ['#000000', '#00e5ff', '#ff9500', '#34c759', '#ffcc00'],
  },
  {
    id: 'high-contrast',
    name: 'High Contrast',
    category: 'dark',
    preview: ['#000000', '#00ffff', '#ffaa00', '#00ff00', '#ffff00'],
  },

  // Light themes
  {
    id: 'solarized-light',
    name: 'Solarized Light',
    category: 'light',
    preview: ['#fdf6e3', '#2aa198', '#268bd2', '#859900', '#b58900'],
  },
  {
    id: 'catppuccin-latte',
    name: 'Catppuccin Latte',
    category: 'light',
    preview: ['#eff1f5', '#1e66f5', '#8839ef', '#40a02b', '#df8e1d'],
  },
  {
    id: 'nord-light',
    name: 'Nord Light',
    category: 'light',
    preview: ['#eceff4', '#88c0d0', '#5e81ac', '#a3be8c', '#ebcb8b'],
  },
  {
    id: 'gruvbox-light',
    name: 'Gruvbox Light',
    category: 'light',
    preview: ['#fbf1c7', '#076678', '#af3a03', '#79740e', '#b57614'],
  },
  {
    id: 'github-light',
    name: 'GitHub Light',
    category: 'light',
    preview: ['#ffffff', '#0969da', '#8250df', '#1a7f37', '#9a6700'],
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
