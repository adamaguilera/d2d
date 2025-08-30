import React, { useMemo, useState, useEffect } from "react";
import type { HeroesMeta } from "./api";
import HeroImage from "./HeroImage";

function slugSearchFilter(q: string, s: string) {
    const n = q.trim().toLowerCase();
    if (!n) return true;
    return s.includes(n);
}

// Placeholder logic moved to shared HeroImage component

// Local HeroImage removed in favor of shared component

export default function EnemyPicker({
    open,
    onClose,
    onPick,
    heroesMeta
}: {
    open: boolean;
    onClose: () => void;
    onPick: (slug: string) => void;
    heroesMeta: HeroesMeta;
}) {
    const [query, setQuery] = useState("");

    // Clear query when picker opens or closes
    useEffect(() => {
        setQuery("");
    }, [open]);

    const options = useMemo(() => {
        const q = query.trim().toLowerCase();
        // always show all heroes (from data) even if image missing
        return heroesMeta
            .filter(h => slugSearchFilter(q, h.slug) || slugSearchFilter(q, h.name ?? ""))
            .sort((a, b) => a.slug.localeCompare(b.slug));
    }, [query, heroesMeta]);

    if (!open) return null;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="w-[min(100vw-2rem,1100px)] max-h-[85vh] bg-white rounded-2xl shadow-soft p-4 flex flex-col">
                <div className="flex items-center gap-3 pb-3 border-b">
                    <input
                        autoFocus
                        placeholder="Search hero by slug or name…"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="w-full rounded-lg border px-3 py-2 outline-none focus:ring focus:ring-blue-200"
                    />
                    <button onClick={onClose} className="px-3 py-2 rounded-lg border hover:bg-slate-50">Close</button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 overflow-auto mt-3">
                    {options.map(h => (
                        <button
                            key={h.slug}
                            onClick={() => { onPick(h.slug); onClose(); }}
                            className="group flex items-center gap-3 rounded-xl border bg-white hover:bg-blue-50 hover:border-blue-300 p-2 text-left"
                        >
                            <div className="w-14 h-14 rounded-lg overflow-hidden bg-slate-100 shrink-0">
                                <HeroImage slug={h.slug} fill />
                            </div>
                            <div className="flex flex-col">
                                <span className="font-medium capitalize">{h.slug.replace(/-/g, " ")}</span>
                                <span className="text-xs text-slate-500">{h.name || h.slug}</span>
                            </div>
                        </button>
                    ))}
                    {options.length === 0 && (
                        <div className="col-span-full text-slate-500 px-2 py-6">
                            No heroes found for "{query}".
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
