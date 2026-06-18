import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import App from './App'
import { I18nProvider, resolveTelegramLang } from './i18n'

const initialLang = resolveTelegramLang(window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider initialLang={initialLang}>
      <App />
    </I18nProvider>
  </StrictMode>
)
