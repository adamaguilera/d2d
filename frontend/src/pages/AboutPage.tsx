export default function AboutPage() {
    return (
        <div style={{ display: 'grid', gap: 16, justifyItems: 'center', textAlign: 'center' }}>
            <h1>About D2Draft</h1>
            <div style={{ width: '75%', background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, textAlign: 'left' }}>
                <p>
                    Hello 👋 D2Draft is made to help the average Dota 2 player make better hero picks. Most players rely on winrates
                    based on pro level matches which doesn't accurately represent the average player. The tool displays
                    individual hero matchup winrates with a simple interface to improve your drafting skills. Data is kept fresh and
                    updated daily.
                </p>
                <p>
                    Please leave any feedback via email at <a href="mailto:admin@d2draft.com">admin@d2draft.com</a>  I'd love to hear what you think.
                </p>
            </div>
        </div>
    )
}


