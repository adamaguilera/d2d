declare global {
    interface Window {
        dataLayer: unknown[]
        gtag?: (...args: unknown[]) => void
        __GA_MEASUREMENT_ID?: string
    }
}

function ensureGtagLoaded(measurementId: string): void {
    if (typeof window.gtag === 'function') return
    window.dataLayer = window.dataLayer || []
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    function gtag(...args: any[]): void {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ; (window.dataLayer as any[]).push(args)
    }
    window.gtag = gtag

    const script = document.createElement('script')
    script.async = true
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`
    document.head.appendChild(script)
}

export function initAnalytics(measurementId: string | undefined): void {
    if (!measurementId) return
    window.__GA_MEASUREMENT_ID = measurementId
    ensureGtagLoaded(measurementId)

    const gtag = window.gtag
    if (!gtag) return
    gtag('js', new Date())
    // Disable automatic page_view; we'll send on route changes
    gtag('config', measurementId, { send_page_view: false })
}

export function trackPageview(path: string, title?: string): void {
    const measurementId = window.__GA_MEASUREMENT_ID
    if (!measurementId || !window.gtag) return
    window.gtag('config', measurementId, {
        page_path: path,
        page_title: title,
    })
}


