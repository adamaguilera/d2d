function resolveBase(): string {
    const configured = import.meta.env.BASE_URL || '/'
    if (configured && configured !== './') {
        return configured.endsWith('/') ? configured : `${configured}/`
    }
    if (typeof window !== 'undefined') {
        const path = window.location.pathname
        const lastSlash = path.lastIndexOf('/')
        const base = lastSlash >= 0 ? path.slice(0, lastSlash + 1) : '/'
        return base || '/'
    }
    return '/'
}

export const BASE_URL: string = resolveBase()

export function withBase(path: string): string {
    const normalized = path.startsWith('/') ? path.slice(1) : path
    return `${BASE_URL}${normalized}`
}


