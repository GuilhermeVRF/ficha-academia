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

export type PlateColor = 'red' | 'blue' | 'yellow' | 'green' | 'white'

export interface Workout {
  id: string
  name: string
  position: number
  color: PlateColor
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

export interface SessionSet {
  exercise_id: string | null
  exercise_name: string
  exercise_position: number
  set_index: number
  weight_kg: number
  reps: number
  done: boolean
}

/** What the calendar needs about one trained session. Datetimes are ISO strings with offset. */
export interface SessionSummary {
  id: string
  workout_id: string | null
  workout_name: string
  workout_color: PlateColor | null
  started_at: string
  finished_at: string
  sets_done: number
  volume_kg: number
}

export interface SessionDetail extends SessionSummary {
  notes: string
  sets: SessionSet[]
}

export interface ExerciseSessionPoint {
  session_id: string
  started_at: string
  sets: SetData[]
}
