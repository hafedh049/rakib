import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { ar } from './ar'
import { fr, type TranslationKey } from './fr'

export type Locale = 'fr' | 'ar'

const DICTIONARIES = { fr, ar } as const
const STORAGE_KEY = 'rakib.locale'

interface I18nValue {
  locale: Locale
  dir: 'ltr' | 'rtl'
  setLocale: (locale: Locale) => void
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nValue | null>(null)

function readInitialLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'fr' || stored === 'ar') return stored
  return navigator.language?.startsWith('ar') ? 'ar' : 'fr'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readInitialLocale)
  const dir = locale === 'ar' ? 'rtl' : 'ltr'

  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = dir
  }, [locale, dir])

  const setLocale = useCallback((next: Locale) => {
    localStorage.setItem(STORAGE_KEY, next)
    setLocaleState(next)
  }, [])

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>) => {
      // Arabic covers the portal; anything else falls back to French rather
      // than rendering a raw key at the user.
      const dictionary = DICTIONARIES[locale] as Partial<
        Record<TranslationKey, string>
      >
      let value = dictionary[key] ?? fr[key] ?? key
      if (vars) {
        for (const [name, replacement] of Object.entries(vars)) {
          value = value.replace(`{${name}}`, String(replacement))
        }
      }
      return value
    },
    [locale],
  )

  const value = useMemo(
    () => ({ locale, dir, setLocale, t }),
    [locale, dir, setLocale, t],
  )
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useT() {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useT must be used inside I18nProvider')
  return context
}
