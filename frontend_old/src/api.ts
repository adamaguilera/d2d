import axios from "axios";

export type HeroesMeta = { slug: string; name: string }[];

export type DataV2 = Record<
    string,
    {
        opponents: Record<string, { winrate: number; matches: number }>;
        totalMatches: number;
    }
>;

export type DateMeta = { date: string; patch: string };

export async function fetchDates(): Promise<DateMeta[]> {
    const { data } = await axios.get("/api/dates");
    return data as DateMeta[];
}

export async function fetchData(date: string): Promise<DataV2> {
    const { data } = await axios.get("/api/data", { params: { date } });
    return data;
}
