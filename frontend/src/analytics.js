export function track(name, props = {}) {
  try {
    if (typeof window !== 'undefined' && typeof window.plausible === 'function') {
      window.plausible(name, { props });
    }
  } catch {}
}
