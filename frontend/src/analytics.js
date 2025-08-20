export function track(name, props = {}) {
  // graceful no-op if plausible is blocked or not yet available
  if (typeof window !== 'undefined' && typeof window.plausible === 'function') {
    window.plausible(name, { props })
  }
}