import { useEffect, useMemo, useRef, useState } from 'react'

type Hero = {
    slug: string
    name: string
    image: string
}

type EnemyPick = {
    hero: Hero | null
    weight: number
}

type MatchupFile = {
    hero: string
    matchups: { opponent: string; winrate: number }[]
}

function clamp(x: number, lo: number, hi: number) {
    return Math.max(lo, Math.min(hi, x))
}

function pctToLogOdds(pct: number) {
    const p = clamp(pct / 100, 0.005, 0.995)
    return Math.log(p / (1 - p))
}

function logOddsToPct(lo: number) {
    const p = 1 / (1 + Math.exp(-lo))
    return 100 * p
}

const PATCHES = ['7.39D']

export default function DraftPage() {
    const [patch, setPatch] = useState<string>(PATCHES[0])
    const [heroes, setHeroes] = useState<Hero[]>([])
    const [enemyPicks, setEnemyPicks] = useState<EnemyPick[]>([
        { hero: null, weight: 0.5 },
        { hero: null, weight: 0.5 },
        { hero: null, weight: 0.5 },
        { hero: null, weight: 0.5 },
        { hero: null, weight: 0.5 },
    ])
    const [isPickerOpen, setPickerOpen] = useState<number | null>(null)
    const [filter, setFilter] = useState('')
    const filterInputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        fetch('/data/heroes.json')
            .then((r) => r.json())
            .then((j) => setHeroes(j.heroes as Hero[]))
            .catch(() => setHeroes([]))
    }, [])

    // Focus filter input on open and allow closing with Escape
    useEffect(() => {
        if (isPickerOpen !== null) {
            filterInputRef.current?.focus()
            const onKeyDown = (e: KeyboardEvent) => {
                if (e.key === 'Escape') setPickerOpen(null)
            }
            window.addEventListener('keydown', onKeyDown)
            return () => window.removeEventListener('keydown', onKeyDown)
        }
    }, [isPickerOpen])

    const selectedEnemySlugs = enemyPicks
        .map((p) => p.hero?.slug)
        .filter(Boolean) as string[]

    const candidateResults = useCounterResults(patch, selectedEnemySlugs, enemyPicks)

    function updateWeight(idx: number, weight: number) {
        setEnemyPicks((prev) => {
            const next = [...prev]
            next[idx] = { ...next[idx], weight }
            return next
        })
    }

    function clearPick(idx: number) {
        setEnemyPicks((prev) => {
            const next = [...prev]
            next[idx] = { ...next[idx], hero: null }
            return next
        })
    }

    function chooseHero(idx: number, hero: Hero) {
        setEnemyPicks((prev) => {
            const next = [...prev]
            next[idx] = { ...next[idx], hero }
            return next
        })
        setPickerOpen(null)
        setFilter('')
    }

    const filteredHeroes = useMemo(() => {
        const q = filter.trim().toLowerCase()
        if (!q) return heroes
        return heroes.filter((h) => h.name.toLowerCase().includes(q) || h.slug.includes(q))
    }, [filter, heroes])

    return (
        <div style={{ display: 'grid', gap: 16, justifyItems: 'center', textAlign: 'center' }}>
            <section style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'center' }}>
                <label htmlFor="patch">Patch</label>
                <select id="patch" value={patch} onChange={(e) => setPatch(e.target.value)}>
                    {PATCHES.map((p) => (
                        <option key={p} value={p}>
                            {p}
                        </option>
                    ))}
                </select>
            </section>

            <section>
                <h2 style={{ marginTop: 0 }}>Select enemy heroes</h2>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
                    {enemyPicks.map((pick, idx) => (
                        <div key={idx} style={{ width: 160 }}>
                            <button
                                onClick={() => setPickerOpen(idx)}
                                style={{
                                    width: 160,
                                    padding: 0,
                                    border: '1px solid #ccc',
                                    borderRadius: 8,
                                    background: '#fafafa',
                                    overflow: 'hidden',
                                    cursor: 'pointer',
                                    display: 'block',
                                    lineHeight: 0,
                                }}
                            >
                                {pick.hero ? (
                                    <img src={pick.hero.image} alt={pick.hero.name} style={{ width: '100%', height: 'auto', display: 'block' }} />
                                ) : (
                                    <div style={{ height: 88.88, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', color: '#888' }}>Select</div>
                                )}
                            </button>
                            <div style={{ marginTop: 8 }}>
                                <label style={{ fontSize: 12 }}>Weight: {pick.weight.toFixed(1)}</label>
                                <input
                                    type="range"
                                    min={0}
                                    max={1}
                                    step={0.1}
                                    value={pick.weight}
                                    onChange={(e) => updateWeight(idx, Number(e.target.value))}
                                    style={{ width: '100%' }}
                                />
                            </div>
                            {pick.hero && (
                                <button style={{ marginTop: 6, width: '100%' }} onClick={() => clearPick(idx)}>
                                    Clear
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            </section>

            {selectedEnemySlugs.length > 0 && (
                <section>
                    <h2 style={{ marginTop: 0 }}>Top counter picks</h2>
                    <ResultsTable
                        results={candidateResults}
                        enemies={enemyPicks.map((p) => p.hero).filter(Boolean) as Hero[]}
                        patch={patch}
                    />
                </section>
            )}

            {isPickerOpen !== null && (
                <div
                    role="dialog"
                    style={{
                        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
                    }}
                    onClick={() => setPickerOpen(null)}
                >
                    <div
                        style={{ background: 'white', borderRadius: 8, padding: 16, maxHeight: '80vh', overflow: 'auto' }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                            <strong>Select a hero</strong>
                            <button onClick={() => setPickerOpen(null)}>Close</button>
                        </div>
                        <input
                            placeholder="Type to filter heroes..."
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            style={{ width: '100%', marginBottom: 12 }}
                            ref={filterInputRef}
                        />
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, justifyItems: 'center', alignItems: 'start' }}>
                            {filteredHeroes
                                .filter((h) => !selectedEnemySlugs.includes(h.slug))
                                .map((h) => (
                                    <button
                                        key={h.slug}
                                        onClick={() => chooseHero(isPickerOpen, h)}
                                        style={{
                                            width: 150,
                                            padding: 0,
                                            border: '1px solid #eee',
                                            borderRadius: 10,
                                            background: '#ffffff',
                                            display: 'grid',
                                            gridTemplateRows: 'auto auto',
                                            overflow: 'hidden',
                                            cursor: 'pointer',
                                            textAlign: 'center',
                                        }}
                                    >
                                        <img src={h.image} alt={h.name} style={{ width: '100%', height: 'auto', objectFit: 'contain', objectPosition: 'top center', display: 'block' }} />
                                        <div style={{ fontSize: 14, padding: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', border: '1px solid #eee' }}>{h.name}</div>
                                    </button>
                                ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

type CounterResult = {
    hero: string
    combined: number
    perEnemy: { enemy: string; winrate: number | null }[]
}

function useCounterResults(patch: string, enemySlugs: string[], enemyPicks: EnemyPick[]): CounterResult[] {
    const [data, setData] = useState<Record<string, Record<string, number>>>({})

    useEffect(() => {
        if (!patch) return
        // Load all hero matchup JSON files for the patch
        const base = `/content/counter/${patch}`
        fetch(`${base}/metadata.json`).catch(() => null)
        const heroSlugs = heroesIndexCache
        Promise.all(
            heroSlugs.map((slug) => fetch(`${base}/${slug}.json`).then((r) => r.json()).catch(() => null))
        ).then((files: (MatchupFile | null)[]) => {
            const acc: Record<string, Record<string, number>> = {}
            for (const f of files) {
                if (!f) continue
                const map: Record<string, number> = {}
                for (const m of f.matchups) {
                    map[m.opponent.toLowerCase()] = m.winrate
                }
                acc[f.hero.toLowerCase()] = map
            }
            setData(acc)
        })
    }, [patch])

    const results = useMemo(() => {
        if (!enemySlugs.length) return []
        const enemies: { enemy: string; weight: number }[] = enemyPicks
            .filter((p) => p.hero)
            .map((p) => ({ enemy: (p.hero as Hero).slug, weight: p.weight }))

        const enemySet = new Set(enemies.map((e) => e.enemy))
        const out: CounterResult[] = []
        for (const [hero, oppMap] of Object.entries(data)) {
            if (enemySet.has(hero)) continue
            let weightedSum = 0
            let weightTotal = 0
            const perEnemy: { enemy: string; winrate: number | null }[] = []
            for (const { enemy, weight } of enemies) {
                const wr = oppMap?.[enemy]
                if (wr == null) {
                    perEnemy.push({ enemy, winrate: null })
                    continue
                }
                weightedSum += weight * pctToLogOdds(wr)
                weightTotal += weight
                perEnemy.push({ enemy, winrate: wr })
            }
            if (weightTotal <= 0) continue
            const combined = logOddsToPct(weightedSum / weightTotal)
            out.push({ hero, combined, perEnemy })
        }
        out.sort((a, b) => b.combined - a.combined)
        return out
    }, [data, enemyPicks, enemySlugs])

    return results
}

const heroesIndexCache: string[] = [
    'abaddon', 'alchemist', 'ancient-apparition', 'anti-mage', 'arc-warden', 'axe', 'bane', 'batrider', 'beastmaster', 'bloodseeker', 'bounty-hunter', 'brewmaster', 'bristleback', 'broodmother', 'centaur-warrunner', 'chaos-knight', 'chen', 'clinkz', 'clockwerk', 'crystal-maiden', 'dark-seer', 'dark-willow', 'dawnbreaker', 'dazzle', 'death-prophet', 'disruptor', 'doom', 'dragon-knight', 'drow-ranger', 'earth-spirit', 'earthshaker', 'elder-titan', 'ember-spirit', 'enchantress', 'enigma', 'faceless-void', 'grimstroke', 'gyrocopter', 'hoodwink', 'huskar', 'invoker', 'io', 'jakiro', 'juggernaut', 'keeper-of-the-light', 'kez', 'kunkka', 'legion-commander', 'leshrac', 'lich', 'lifestealer', 'lina', 'lion', 'lone-druid', 'luna', 'lycan', 'magnus', 'marci', 'mars', 'medusa', 'meepo', 'mirana', 'monkey-king', 'morphling', 'muerta', 'naga-siren', 'natures-prophet', 'necrophos', 'night-stalker', 'nyx-assassin', 'ogre-magi', 'omniknight', 'oracle', 'outworld-destroyer', 'pangolier', 'phantom-assassin', 'phantom-lancer', 'phoenix', 'primal-beast', 'puck', 'pudge', 'pugna', 'queen-of-pain', 'razor', 'riki', 'ringmaster', 'rubick', 'sand-king', 'shadow-demon', 'shadow-fiend', 'shadow-shaman', 'silencer', 'skywrath-mage', 'slardar', 'slark', 'snapfire', 'sniper', 'spectre', 'spirit-breaker', 'storm-spirit', 'sven', 'techies', 'templar-assassin', 'terrorblade', 'tidehunter', 'timbersaw', 'tinker', 'tiny', 'treant-protector', 'troll-warlord', 'tusk', 'underlord', 'undying', 'ursa', 'vengeful-spirit', 'venomancer', 'viper', 'visage', 'void-spirit', 'warlock', 'weaver', 'windranger', 'winter-wyvern', 'witch-doctor', 'wraith-king', 'zeus'
]

function useHeroRoles(patch: string): Record<string, string[]> {
    const [rolesByHero, setRolesByHero] = useState<Record<string, string[]>>({})

    useEffect(() => {
        if (!patch) return
        const base = `/content/roles/${patch}`
        const heroSlugs = heroesIndexCache
        Promise.all(
            heroSlugs.map((slug) =>
                fetch(`${base}/${slug}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
            )
        ).then((files: (any | null)[]) => {
            const acc: Record<string, string[]> = {}
            for (const f of files) {
                if (!f || !f.hero) continue
                const heroSlug = String(f.hero).toLowerCase()
                const roles: string[] = Array.isArray(f.roles) ? f.roles : []
                acc[heroSlug] = roles
            }
            setRolesByHero(acc)
        })
    }, [patch])

    return rolesByHero
}

function ResultsTable({ results, enemies, patch }: { results: CounterResult[]; enemies: Hero[]; patch: string }) {
    const rolesByHero = useHeroRoles(patch)
    const ALL_ROLES = ['carry', 'mid', 'offlane', 'support', 'hard support']
    const [isFilterOpen, setFilterOpen] = useState(false)
    const [selectedRoles, setSelectedRoles] = useState<string[]>(ALL_ROLES)

    function isFilteringActive(): boolean {
        return selectedRoles.length > 0 && selectedRoles.length < ALL_ROLES.length
    }

    function toggleRole(role: string) {
        setSelectedRoles((prev) => (prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]))
    }

    function setAll() {
        setSelectedRoles(ALL_ROLES.slice())
    }

    function clearAll() {
        setSelectedRoles([])
    }

    const displayedResults = useMemo(() => {
        if (!isFilteringActive()) return results
        const selected = new Set(selectedRoles)
        return results.filter((r) => {
            const roles = rolesByHero[r.hero] || []
            if (!roles.length) return false
            return roles.some((role) => selected.has(role))
        })
    }, [results, rolesByHero, selectedRoles])
    return (
        <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                    <tr>
                        <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span>Hero</span>
                                <button
                                    onClick={() => setFilterOpen(true)}
                                    title="Filter by role"
                                    style={{
                                        display: 'inline-flex', alignItems: 'center', gap: 6,
                                        padding: '4px 8px', borderRadius: 16, border: '1px solid #e0e0e0',
                                        background: isFilteringActive() ? '#0ea5e9' : '#ffffff',
                                        color: isFilteringActive() ? '#ffffff' : '#333333', cursor: 'pointer',
                                        boxShadow: '0 1px 2px rgba(0,0,0,0.06)'
                                    }}
                                >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M4 5h16l-6 7v5l-4 2v-7L4 5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                                    </svg>
                                    <span style={{ fontSize: 12 }}>Filter{isFilteringActive() ? ` (${selectedRoles.length})` : ''}</span>
                                </button>
                            </div>
                        </th>
                        <th style={{ textAlign: 'right', padding: 8, borderBottom: '1px solid #ddd' }}>Result</th>
                        {enemies.map((e) => (
                            <th key={e.slug} style={{ textAlign: 'right', padding: 8, borderBottom: '1px solid #ddd' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                                    <span>vs</span>
                                    <img src={`/content/images/heroes/${e.slug}.png`} alt={`vs ${e.name}`} style={{ width: 28, height: 28, borderRadius: 4, objectFit: 'cover' }} />
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {displayedResults.map((r) => (
                        <tr key={r.hero}>
                            <td style={{ padding: 8, borderBottom: '1px solid #f0f0f0' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <img src={`/content/images/heroes/${r.hero}.png`} alt={r.hero} style={{ width: 28, height: 28, borderRadius: 4, objectFit: 'cover' }} />
                                    <span style={{ textTransform: 'capitalize' }}>{r.hero.replace(/-/g, ' ')}</span>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                        {rolesByHero[r.hero] && rolesByHero[r.hero].length > 0 ? (
                                            rolesByHero[r.hero].map((role) => {
                                                const file = role.replace(/\s+/g, '_')
                                                return (
                                                    <img
                                                        key={role}
                                                        src={`/content/images/roles/${file}.png`}
                                                        alt={role}
                                                        title={role}
                                                        style={{ width: 16, height: 16, objectFit: 'contain' }}
                                                    />
                                                )
                                            })
                                        ) : (
                                            <svg
                                                width="16"
                                                height="16"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                xmlns="http://www.w3.org/2000/svg"
                                                style={{ display: 'block', color: '#888' }}
                                            >
                                                <title>No roles found</title>
                                                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                                                <path d="M9.09 9a3 3 0 0 1 5.91 1c0 2-3 2-3 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                <path d="M12 17h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        )}
                                    </div>
                                </div>
                            </td>
                            <td style={{ padding: 8, borderBottom: '1px solid #f0f0f0', textAlign: 'right' }}>{r.combined.toFixed(2)}%</td>
                            {r.perEnemy.map((pe) => (
                                <td key={pe.enemy} style={{ padding: 8, borderBottom: '1px solid #f0f0f0', textAlign: 'right' }}>
                                    {pe.winrate == null ? '—' : `${pe.winrate.toFixed(2)}%`}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
            {isFilterOpen && (
                <div
                    role="dialog"
                    onClick={() => setFilterOpen(false)}
                    style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}
                >
                    <div
                        onClick={(e) => e.stopPropagation()}
                        style={{ width: 420, maxWidth: '90vw', background: 'white', borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,0.2)', overflow: 'hidden' }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 14, borderBottom: '1px solid #f0f0f0' }}>
                            <strong>Filter by role</strong>
                            <button onClick={() => setFilterOpen(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#666' }} title="Close">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                </svg>
                            </button>
                        </div>
                        <div style={{ padding: 14, display: 'grid', gap: 12 }}>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {ALL_ROLES.map((role) => {
                                    const file = role.replace(/\s+/g, '_')
                                    const active = selectedRoles.includes(role)
                                    return (
                                        <button
                                            key={role}
                                            onClick={() => toggleRole(role)}
                                            style={{
                                                display: 'inline-flex', alignItems: 'center', gap: 8,
                                                padding: '8px 10px', borderRadius: 999,
                                                border: `1px solid ${active ? '#0ea5e9' : '#e5e7eb'}`,
                                                background: active ? 'rgba(14,165,233,0.1)' : '#ffffff',
                                                color: '#111827', cursor: 'pointer'
                                            }}
                                        >
                                            <img src={`/content/images/roles/${file}.png`} alt={role} title={role} style={{ width: 16, height: 16 }} />
                                            <span style={{ textTransform: 'capitalize', fontSize: 12 }}>{role}</span>
                                        </button>
                                    )
                                })}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    <button onClick={setAll} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer' }}>Add all</button>
                                    <button onClick={clearAll} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#ffffff', cursor: 'pointer' }}>Clear all</button>
                                </div>
                                <button onClick={() => setFilterOpen(false)} style={{ padding: '8px 12px', borderRadius: 8, border: 'none', background: '#0ea5e9', color: 'white', cursor: 'pointer' }}>Apply</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}


