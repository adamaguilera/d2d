import React from "react";
import type { DateMeta } from "./api";

export default function DateSelector({
    dates,
    value,
    onChange
}: {
    dates: DateMeta[];
    value: string;
    onChange: (newDate: string) => void;
}) {
    return (
        <div className="rounded-2xl bg-white shadow-soft p-4 mb-6 grid gap-4 sm:grid-cols-2">
            <div>
                <label className="text-sm text-slate-600">Select date</label>
                <select
                    className="mt-1 w-full rounded-xl border px-3 py-2 outline-none focus:ring focus:ring-blue-200"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                >
                    <option value="" disabled>Select date…</option>
                    {dates.map(dm => (
                        <option key={dm.date} value={dm.date}>
                            {dm.patch ? `${dm.patch} - ${dm.date}` : dm.date}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
}


