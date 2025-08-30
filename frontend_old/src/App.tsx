import React, { useEffect, useMemo, useState } from "react";
import { fetchData, fetchDates, type DataV2, type DateMeta } from "./api";
import EnemyPicker from "./EnemyPicker";
import HeroImage from "./HeroImage";
import ResultsTable from "./ResultsTable";
import { scoreCandidates, type EnemyPick } from "./logic";
import DateSelector from "./DateSelector";

type EnemySlot = { slug: string | null; weight: number };

export default function App() {
    const [dates, setDates] = useState<DateMeta[]>([]);
    const [date, setDate] = useState<string>("");
    const [data, setData] = useState<DataV2>({});
    const [slots, setSlots] = useState<EnemySlot[]>(
        Array.from({ length: 5 }, () => ({ slug: null, weight: 0.5 }))
    );

    const [pickerOpenFor, setPickerOpenFor] = useState<number | null>(null);

    useEffect(() => {
        (async () => {
            const d = await fetchDates();
            setDates(d);
            if (d.length && !date) setDate(d[d.length - 1].date);
        })();
    }, []);

    useEffect(() => {
        if (!date) return;
        (async () => setData(await fetchData(date)))();
    }, [date]);

    // derive meta list that always covers available slugs from data
    const derivedMeta = useMemo(() => {
        const slugs = Object.keys(data);
        return slugs.map(slug => {
            const name = slug.replace(/-/g, " ");
            return { slug, name };
        });
    }, [data]);

    const heroesSet = useMemo(() => new Set(Object.keys(data)), [data]);

    const enemies: EnemyPick[] = useMemo(() => {
        return slots
            .filter(s => s.slug && heroesSet.has(s.slug))
            .map(s => ({ slug: s.slug!, weight: s.weight }));
    }, [slots, heroesSet]);

    const results = useMemo(
        () => scoreCandidates(data, enemies),
        [data, enemies]
    );

    return (
        <div className="max-w-6xl mx-auto p-6">
            <h1 className="text-2xl font-semibold mb-4">Dota Counter Picker</h1>

            <DateSelector dates={dates} value={date} onChange={setDate} />

            <div className="rounded-2xl bg-white shadow-soft p-4 mb-6">
                <h2 className="text-lg font-medium mb-3">Enemy Heroes</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                    {slots.map((slot, i) => {
                        const label = slot.slug ? slot.slug.replace(/-/g, " ") : "";
                        return (
                            <div key={i} className="rounded-xl border p-3 flex flex-col gap-3">
                                <button
                                    className="rounded-lg overflow-hidden border bg-slate-50 hover:bg-slate-100 aspect-[4/3] flex items-center justify-center"
                                    onClick={() => setPickerOpenFor(i)}
                                    aria-label={`Pick enemy hero for slot ${i + 1}`}
                                >
                                    {slot.slug ? (
                                        <HeroImage slug={slot.slug} fill />
                                    ) : (
                                        <div className="text-slate-400">Click to choose</div>
                                    )}
                                </button>

                                {slot.slug && (
                                    <>
                                        <div className="text-sm font-medium capitalize">{label}</div>
                                        <div className="flex items-center gap-3">
                                            <label className="text-sm text-slate-600">Weight</label>
                                            <input
                                                type="range"
                                                min={0}
                                                max={1}
                                                step={0.1}
                                                value={slot.weight}
                                                onChange={(e) => {
                                                    const weight = parseFloat(e.target.value);
                                                    setSlots(s => s.map((x, idx) => idx === i ? { ...x, weight } : x));
                                                }}
                                                className="w-full"
                                            />
                                            <div className="w-10 text-right text-sm">{slot.weight.toFixed(1)}</div>
                                        </div>

                                        <button
                                            onClick={() => setSlots(s => s.map((x, idx) => idx === i ? { slug: null, weight: 0.5 } : x))}
                                            className="text-sm text-red-600 hover:text-red-700 self-start"
                                        >
                                            Clear
                                        </button>
                                    </>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="rounded-2xl bg-white shadow-soft p-4">
                <h2 className="text-lg font-medium mb-3">Best Picks</h2>
                {enemies.length === 0 ? (
                    <div className="text-slate-500">Pick at least one enemy hero.</div>
                ) : (
                    <ResultsTable enemies={enemies} rows={results} />
                )}
            </div>

            <EnemyPicker
                open={pickerOpenFor !== null}
                onClose={() => setPickerOpenFor(null)}
                onPick={(slug) => {
                    if (pickerOpenFor === null) return;
                    setSlots(s => s.map((x, idx) => idx === pickerOpenFor ? { ...x, slug } : x));
                    setPickerOpenFor(null);
                }}
                heroesMeta={derivedMeta}
            />
        </div>
    );
}

// Placeholder moved into shared HeroImage component
