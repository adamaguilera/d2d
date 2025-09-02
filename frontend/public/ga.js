(function () {
    var MEASUREMENT_ID = 'G-DHJ4QR42HT'

    window.dataLayer = window.dataLayer || []
    function gtag() { window.dataLayer.push(arguments) }
    if (!window.gtag) window.gtag = gtag

    // Initial page load
    gtag('js', new Date())
    gtag('config', MEASUREMENT_ID)

    // SPA pageview tracking: track on history changes
    function trackPageView() {
        if (!window.gtag) return
        window.gtag('config', MEASUREMENT_ID, {
            page_path: location.pathname + location.search + location.hash,
        })
    }

    var originalPushState = history.pushState
    var originalReplaceState = history.replaceState
    history.pushState = function () {
        originalPushState.apply(this, arguments)
        setTimeout(trackPageView, 0)
    }
    history.replaceState = function () {
        originalReplaceState.apply(this, arguments)
        setTimeout(trackPageView, 0)
    }
    window.addEventListener('popstate', trackPageView)
})()


