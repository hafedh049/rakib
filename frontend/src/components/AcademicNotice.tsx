import { useT } from '@/i18n'

/**
 * Permanent, non-dismissible notice that this is a student project.
 *
 * The site carries a real bank's identity and asks members of the public for a
 * phone number or an email. Without this line, someone arriving from a search
 * engine has no way to tell it apart from the bank's own complaint form. It is
 * deliberately not dismissible and deliberately at the very top: a notice you
 * can close is a notice most people never read.
 */
export function AcademicNotice() {
  const { t } = useT()
  return (
    <div
      role="note"
      className="w-full border-b border-line bg-surface-2 px-4 py-1.5 text-center
                 text-2xs leading-snug text-ink-muted"
    >
      {t('academic.notice')}
    </div>
  )
}
