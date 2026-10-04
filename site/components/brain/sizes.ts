// The canvas's size, shared by the loading placeholder and the viewer so nothing below moves when the viewer arrives.
// Kept apart from viewer.tsx, which would bring three.js into every page that only shows the placeholder.
export const CANVAS = {
  full: "h-[min(60vh,110vw)] min-h-[320px] lg:h-[62vh]",
  compact: "h-[min(52vh,95vw)] min-h-[300px]",
} as const;
