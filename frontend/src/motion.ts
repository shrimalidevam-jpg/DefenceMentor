export function closeWithMotion(selector: string, onClose: () => void, duration = 190): void {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    onClose()
    return
  }
  const surface = document.querySelector<HTMLElement>(selector)
  if (!surface || surface.dataset.motionExit === 'true') return

  surface.dataset.motionExit = 'true'
  const overlay = surface.closest<HTMLElement>(
    '.chat-overlay, .assessment-overlay, .diagnostic-overlay, .settings-overlay, .study-planner-overlay, .daily-review-overlay, .daily-growth-overlay, .ssb-overlay',
  )
  overlay?.setAttribute('data-motion-exit', 'true')
  window.setTimeout(onClose, duration)
}
