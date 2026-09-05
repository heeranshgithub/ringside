import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

const TICKS = [
  "M17.70 12.00L22.10 12.00",
  "M16.94 14.85L19.27 16.20",
  "M14.85 16.94L16.65 20.05",
  "M12.00 17.70L12.00 22.70",
  "M9.15 16.94L7.60 19.62",
  "M7.06 14.85L4.99 16.05",
  "M6.30 12.00L2.10 12.00",
  "M7.06 9.15L2.82 6.70",
  "M9.15 7.06L7.70 4.55",
  "M12.00 6.30L12.00 2.50",
  "M14.85 7.06L17.40 2.65",
  "M16.94 9.15L19.19 7.85",
];

/** Home-screen tile: the mark knocked out of the Halo gradient. */
export default function AppleIcon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(150deg, #c7eded 0%, #0e7f8a 100%)",
      }}
    >
      <svg
        width="112"
        height="112"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#ffffff"
        strokeWidth={1.95}
        strokeLinecap="round"
      >
        {TICKS.map((d) => (
          <path key={d} d={d} />
        ))}
      </svg>
    </div>,
    size,
  );
}
