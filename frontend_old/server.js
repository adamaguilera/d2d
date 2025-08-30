import express from "express";
import cors from "cors";
import fs from "fs/promises";
import path from "path";

const app = express();
const PORT = 5174;

// Where your content lives (./content/...) — folder is outside ./frontend
const COUNTER_DIR = process.env.COUNTER_DIR || path.resolve(process.cwd(), "../content/counter");
const IMAGES_DIR = process.env.IMAGES_DIR || path.resolve(process.cwd(), "../content/images");

app.use(cors());
app.use(express.json());
app.use("/images", express.static(IMAGES_DIR));
// Also expose under /content/images for clients that reference that prefix
app.use("/content/images", express.static(IMAGES_DIR));


// Utility: read date folders
async function listDates() {
    const entries = await fs.readdir(COUNTER_DIR, { withFileTypes: true }).catch(() => []);
    return entries.filter(e => e.isDirectory()).map(e => e.name).sort();
}

async function readPatchForDate(date) {
    try {
        const metadataPath = path.join(COUNTER_DIR, date, "metadata.json");
        const raw = await fs.readFile(metadataPath, "utf-8");
        const meta = JSON.parse(raw);
        if (meta && typeof meta.patch === "string") return meta.patch;
    } catch (_) { }
    return "";
}

// data[hero] = { opponents: { opp: { winrate, matches } }, totalMatches }
async function loadData(date) {
    const dir = path.join(COUNTER_DIR, date);
    const files = await fs.readdir(dir).catch(() => []);
    const data = {};
    for (const file of files) {
        if (!file.endsWith(".json")) continue;
        const fp = path.join(dir, file);
        try {
            const obj = JSON.parse(await fs.readFile(fp, "utf-8"));
            const hero = String(obj.hero || path.basename(file, ".json")).toLowerCase();
            const opponents = {};
            let totalMatches = 0;

            for (const m of obj.matchups || []) {
                const opp = String(m.opponent || "").toLowerCase();
                const wr = typeof m.winrate === "number" ? m.winrate : null;
                const mt = typeof m.matches === "number" ? m.matches : null;
                if (!opp || wr == null || mt == null) continue;
                opponents[opp] = { winrate: wr, matches: mt };
                totalMatches += mt; // sum over all opponents (note: Dotabuff semantics double-count across enemies; OK for share r)
            }

            if (Object.keys(opponents).length) {
                data[hero] = { opponents, totalMatches };
            }
        } catch (_) { }
    }
    return data;
}



// --- API routes ---
app.get("/api/dates", async (_req, res) => {
    const dates = await listDates();
    const metas = await Promise.all(
        dates.map(async (d) => ({ date: d, patch: await readPatchForDate(d) }))
    );
    res.json(metas);
});

app.get("/api/data", async (req, res) => {
    const date = String(req.query.date || "");
    if (!date) return res.status(400).json({ error: "missing date" });
    const data = await loadData(date);
    res.json(data);
});

// Start server
app.listen(PORT, () => {
    console.log(`[API] listening on http://localhost:${PORT}`);
});