export interface SetData {
  weight_kg: number
  reps: number
}

export interface Exercise {
  id: string
  name: string
  position: number
  notes: string
  rest_seconds: number | null
  sets: SetData[]
}

export interface Workout {
  id: string
  name: string
  position: number
  exercises: Exercise[]
}

export interface HistoryPoint {
  date: string
  sets: SetData[]
  max_weight_kg: number
  volume_kg: number
}

export interface ImportPreview {
  workouts: {
    name: string
    existing_id: string | null
    exercises: { name: string; sets: SetData[]; warning: string | null }[]
  }[]
}

export interface User {
  id: string
  name: string
  email: string
  is_admin: boolean
}

export interface Invite {
  code: string
  created_at: string
  expires_at: string
  used_by_name: string | null
}
