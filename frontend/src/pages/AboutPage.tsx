export default function AboutPage() {
    return (
        <div style={{ display: 'grid', gap: 16, justifyItems: 'center', textAlign: 'center' }}>
            <h1>About D2Draft</h1>
            <div style={{ width: '75%', background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16 }}>
                <p>
                    Hello 👋 I'm an Immortal-ranked Dota 2 player. I found other draft tools either
                    over-index on pro matches (most of us aren't pros!) or don't keep data fresh for
                    the current patch. I wanted something that knows which heroes play which roles, surfaces good matchups,
                    and helps improve draft win rate without extra mental load. Thus D2Draft was born!
                </p>
                <p>
                    Please leave any feedback via email at <a href="mailto:admin@d2draft.com">admin@d2draft.com</a>  I'd love to hear what you think.
                </p>
            </div>
        </div>
    )
}


