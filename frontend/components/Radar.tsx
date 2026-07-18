"use client";

/** Animated sonar/radar rings. Pulses when `active`, dim otherwise. */
export default function Radar({
  color,
  active,
}: {
  color: "green" | "purple";
  active: boolean;
}) {
  return (
    <div className={`radar ${color} ${active ? "active" : ""}`}>
      <span className="ring r1" />
      <span className="ring r2" />
      <span className="ring r3" />
      <span className="core" />
    </div>
  );
}
