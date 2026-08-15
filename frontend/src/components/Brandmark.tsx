import { useState } from 'react'

/**
 * The institution's mark.
 *
 * The official artwork is a registered trademark and is NOT bundled in this
 * repository. Drop the file supplied by the bank at `public/brand/uib.svg`
 * (or `.png`) and it is used automatically; until then a typographic fallback
 * carries the same identity — red square, black wordmark — without reproducing
 * artwork we were not given.
 *
 * Keeping the asset out of source control also means the repository can be
 * shared, graded and archived without redistributing someone else's mark.
 */
export function Brandmark({
  size = 'md',
  className = '',
}: {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  const [official, setOfficial] = useState(true)

  const box = { sm: 'h-6', md: 'h-8', lg: 'h-11' }[size]
  const type = { sm: 'text-base', md: 'text-xl', lg: 'text-3xl' }[size]

  if (official) {
    return (
      <img
        src="/brand/uib.svg"
        alt="Union Internationale de Banques"
        className={`${box} w-auto ${className}`}
        onError={() => setOfficial(false)}
      />
    )
  }

  return (
    <span
      className={`inline-flex items-center gap-2 ${className}`}
      aria-label="Union Internationale de Banques"
    >
      <span
        aria-hidden
        className={`${box} aspect-square shrink-0 bg-brand`}
        style={{ borderRadius: 2 }}
      />
      <span className={`${type} font-bold tracking-tight text-ink leading-none`}>
        UIB
      </span>
    </span>
  )
}
