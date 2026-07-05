/**
 * Validates a `?next=` redirect target so it can only ever point at a
 * same-origin, relative path.
 *
 * Why this exists as a shared function rather than being duplicated per
 * page: Login.jsx implemented this check correctly, but Register.jsx's
 * own submit handler called `navigate(next, { replace: true })` using the
 * raw, unvalidated `next` query param — an open-redirect vector (e.g.
 * `/register?next=https://evil.example.com` or `next=//evil.example.com`)
 * that a copy-pasted-but-not-copied fix left open on one of the two pages
 * that both accept a `next` param. Centralizing the check means both
 * pages get the same guarantee and a future third page (or a future
 * tightening of the rule) only has to change one place.
 *
 * @param {string} path - the raw, attacker-controllable `next` query param.
 * @returns {string} a same-origin relative path, or '/' if `path` fails
 *   any of the safety checks (absolute URL, protocol-relative '//', path
 *   traversal, or an embedded scheme like 'javascript:').
 */
export function getSafeRedirect(path) {
  try {
    const decoded = decodeURIComponent(path)
    if (
      decoded.startsWith('/') &&
      !decoded.startsWith('//') &&
      !decoded.includes('..') &&
      !decoded.includes(':') &&
      !decoded.includes('\\')
    ) {
      return decoded
    }
  } catch {
    /* malformed encoding */
  }
  return '/'
}
