import React, { useState } from "react";

function Placeholder({ slug, size }: { slug: string; size: number }) {
    const initials = slug
        .split("-")
        .map(w => w[0]?.toUpperCase() ?? "")
        .slice(0, 2)
        .join("");
    const hash = Array.from(slug).reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
    const hue = hash % 360;
    const bg = `linear-gradient(135deg, hsl(${hue} 70% 85%), hsl(${(hue + 40) % 360} 70% 75%))`;
    return (
        <div
            style={{ width: size, height: size, background: bg }}
            className="flex items-center justify-center rounded-md text-slate-700"
        >
            <span className="font-bold" style={{ fontSize: Math.max(12, size * 0.28) }}>
                {initials}
            </span>
        </div>
    );
}

export default function HeroImage({ slug, size = 32, className, fill }: { slug: string; size?: number; className?: string; fill?: boolean }) {
    const [hasError, setHasError] = useState(false);

    if (hasError) {
        return <Placeholder slug={slug} size={size} />;
    }

    const imageUrl = `/content/images/heroes/${slug}.png`;

    const baseClass = className ?? "object-cover";
    const style = fill ? undefined : { width: size, height: size } as React.CSSProperties;

    return (
        <img
            src={imageUrl}
            alt={slug}
            className={fill ? `${baseClass} w-full h-full` : baseClass}
            style={style}
            onError={() => setHasError(true)}
        />
    );
}


