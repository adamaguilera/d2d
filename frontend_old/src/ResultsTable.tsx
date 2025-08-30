import React from "react";
import HeroImage from "./HeroImage";
import type { EnemyPick } from "./logic";

type ResultRow = {
    hero: string;
    combined: number;
    perEnemy: { enemy: string; winrate: number | null }[];
};

export default function ResultsTable({ enemies, rows }: { enemies: EnemyPick[]; rows: ResultRow[]; }) {
    if (!rows.length) {
        return <div className="text-slate-500">No results for this selection.</div>;
    }
    return (
        <div className="overflow-auto">
            <table className="w-full border-collapse">
                <thead>
                    <tr className="text-left border-b">
                        <th className="py-2 pr-3">Hero</th>
                        <th className="py-2 pr-3">Result</th>
                        {enemies.map(e => (
                            <th key={e.slug} className="py-2 pr-3">
                                <div className="flex items-center gap-2">
                                    <span>vs</span>
                                    <div className="w-5 h-5 rounded-sm overflow-hidden">
                                        <HeroImage slug={e.slug} fill />
                                    </div>
                                    <span className="text-xs text-slate-500">(w={e.weight})</span>
                                </div>
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map(r => (
                        <tr key={r.hero} className="border-b last:border-b-0">
                            <td className="py-2 pr-3 flex items-center gap-2">
                                <div className="w-8 h-8 rounded-md overflow-hidden">
                                    <HeroImage slug={r.hero} fill />
                                </div>
                                <span className="capitalize">{r.hero.replace(/-/g, " ")}</span>
                            </td>
                            <td className="py-2 pr-3 font-medium">{r.combined.toFixed(2)}%</td>
                            {r.perEnemy.map(pe => (
                                <td key={r.hero + pe.enemy} className="py-2 pr-3">
                                    {pe.winrate == null ? "—" : `${pe.winrate.toFixed(2)}%`}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}


