import React from 'react'
import Button from './Button.jsx'

/**
 * Standard "this section failed to load" state: a message plus a retry
 * action. Used anywhere a `useApiResource` (or similar) fetch fails, so a
 * failed request never leaves the UI stuck on a permanent skeleton loader
 * with no way for the user to recover.
 */
export default function ErrorState({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className="grid" role="alert">
      <div className="muted" style={{ color: 'var(--danger)' }}>{message}</div>
      {onRetry && (
        <Button variant="subtle" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}
