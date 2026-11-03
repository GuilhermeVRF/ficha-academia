import type { MuscleGroup } from '@/types'

export const MUSCLE_GROUPS: { key: MuscleGroup; label: string }[] = [
  { key: 'peito', label: 'Peito' },
  { key: 'costas', label: 'Costas' },
  { key: 'ombros', label: 'Ombros' },
  { key: 'biceps', label: 'Bíceps' },
  { key: 'triceps', label: 'Tríceps' },
  { key: 'pernas', label: 'Pernas' },
  { key: 'gluteos', label: 'Glúteos' },
  { key: 'panturrilha', label: 'Panturrilha' },
  { key: 'abdomen', label: 'Abdômen' },
  { key: 'antebraco', label: 'Antebraço' },
]

export const MUSCLE_LABEL = Object.fromEntries(MUSCLE_GROUPS.map((item) => [item.key, item.label])) as Record<
  MuscleGroup,
  string
>
