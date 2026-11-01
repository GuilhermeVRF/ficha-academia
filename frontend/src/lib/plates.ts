import type { PlateColor } from '@/types'

/** Competition bumper plate colors, in the order new workouts receive them. */
export const PLATE_COLORS: PlateColor[] = ['red', 'blue', 'yellow', 'green', 'white']

export const PLATE_LABELS: Record<PlateColor, string> = {
  red: 'Vermelha (25 kg)',
  blue: 'Azul (20 kg)',
  yellow: 'Amarela (15 kg)',
  green: 'Verde (10 kg)',
  white: 'Branca (5 kg)',
}

/** Literal class names so Tailwind keeps them in the build. */
export const PLATE_BG: Record<PlateColor, string> = {
  red: 'bg-plate-red',
  blue: 'bg-plate-blue',
  yellow: 'bg-plate-yellow',
  green: 'bg-plate-green',
  white: 'bg-plate-white',
}

/** Sessions of a deleted workout have no color. */
export const NO_PLATE_BG = 'bg-faint'

export function plateBg(color: PlateColor | null | undefined) {
  return color ? PLATE_BG[color] : NO_PLATE_BG
}

export function nextPlateColor(current: PlateColor) {
  return PLATE_COLORS[(PLATE_COLORS.indexOf(current) + 1) % PLATE_COLORS.length]
}

/** First color not used yet, cycling once all are taken (mirrors the server rule). */
export function unusedPlateColor(used: PlateColor[]) {
  return PLATE_COLORS.find((color) => !used.includes(color)) ?? PLATE_COLORS[used.length % PLATE_COLORS.length]
}
