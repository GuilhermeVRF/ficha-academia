import type { SetData } from '@/types'

export function formatWeight(value: number) {
  return String(value).replace('.', ',')
}

/** Compact summary: "4×10 · 45 kg" when uniform, otherwise "45×10  50×8". */
export function formatSets(sets: SetData[]) {
  const first = sets[0]
  if (!first) return '—'
  const sameWeight = sets.every((set) => set.weight_kg === first.weight_kg)
  const sameReps = sets.every((set) => set.reps === first.reps)
  if (sameWeight && sameReps) {
    const prescription = `${sets.length}×${first.reps}`
    return first.weight_kg ? `${prescription} · ${formatWeight(first.weight_kg)} kg` : prescription
  }
  if (sameWeight) {
    const reps = sets.map((set) => set.reps).join(',')
    return first.weight_kg ? `${reps} · ${formatWeight(first.weight_kg)} kg` : reps
  }
  return sets.map((set) => `${formatWeight(set.weight_kg)}×${set.reps}`).join('  ')
}
