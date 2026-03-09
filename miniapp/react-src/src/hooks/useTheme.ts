import { useState, useEffect, useCallback } from 'react';
import { Theme } from '../types';

export function useTheme(initial: Theme = 'auto') {
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      return (localStorage.getItem('ncfu_theme') as Theme) || initial;
    } catch {
      return initial;
    }
  });

  const applyTheme = useCallback((t: Theme) => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const dark = t === 'dark' || (t === 'auto' && prefersDark);
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');

    const tg = window.Telegram?.WebApp;
    if (dark) {
      tg?.setHeaderColor?.('#080808');
      tg?.setBackgroundColor?.('#080808');
    } else {
      tg?.setHeaderColor?.('#f8f8f8');
      tg?.setBackgroundColor?.('#f8f8f8');
    }
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme, applyTheme]);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'auto') applyTheme('auto');
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme, applyTheme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try { localStorage.setItem('ncfu_theme', t); } catch {}
  }, []);

  return { theme, setTheme };
}
