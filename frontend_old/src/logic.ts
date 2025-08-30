import type { DataV2 } from "./api";

function clamp(x: number, lo: number, hi: number) {
    return Math.max(lo, Math.min(hi, x));
}
function pctToLogOdds(pct: number) {
    const p = clamp(pct / 100, 0.005, 0.995);
    return Math.log(p / (1 - p));
}
function logOddsToPct(lo: number) {
    const p = 1 / (1 + Math.exp(-lo));
    return 100 * p;
}
function logit(x: number) {
    const p = clamp(x, 1e-6, 1 - 1e-6);
    return Math.log(p / (1 - p));
}

export type EnemyPick = { slug: string; weight: number };

export function scoreCandidates(
    data: DataV2,
    enemies: EnemyPick[]
) {
    const enemySet = new Set(enemies.map(e => e.slug));

    const results: {
        hero: string;
        combined: number;
        perEnemy: { enemy: string; winrate: number | null }[];
        matchShare: number; // r in [0,1]
    }[] = [];

    for (const hero of Object.keys(data)) {
        if (enemySet.has(hero)) continue;

        const oppMap = data[hero]?.opponents || {};
        const totalMatches = Math.max(1, data[hero]?.totalMatches || 1);

        // skill component: weighted log-odds of winrates
        let lsum = 0;
        let wsum = 0;
        const perEnemy: { enemy: string; winrate: number | null }[] = [];

        for (const { slug, weight } of enemies) {
            const rec = oppMap[slug];
            if (!rec) {
                perEnemy.push({ enemy: slug, winrate: null });
                continue;
            }
            const win01 = clamp(rec.winrate / 100, 0, 1);
            lsum += weight * win01;
            wsum += weight;
            perEnemy.push({ enemy: slug, winrate: rec.winrate });
        }
        if (wsum <= 0) continue;

        const combined01 = lsum / wsum;
        const r = 0; // deprecated

        const finalPct = 100 * combined01;

        results.push({ hero, combined: finalPct, perEnemy, matchShare: r });
    }

    results.sort((a, b) => b.combined - a.combined);
    return results;
}
