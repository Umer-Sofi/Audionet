"use client";

/** A single signal-quality metric tile (icon, value, rating). */
export default function MetricTile({
  icon,
  label,
  value,
  rating,
  ratingColor,
}: {
  icon: string;
  label: string;
  value: string;
  rating?: string;
  ratingColor?: "good" | "excellent" | "muted";
}) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {rating && <div className={`metric-rating ${ratingColor ?? "muted"}`}>{rating}</div>}
    </div>
  );
}
