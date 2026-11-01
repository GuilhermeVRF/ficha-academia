/** Calendar helpers. Days are local "YYYY-MM-DD" keys; weeks start on Monday. */

const DAY_MS = 24 * 60 * 60 * 1000

export function dayKey(date: Date) {
  return date.toLocaleDateString('sv-SE')
}

export function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

export function startOfWeek(date: Date) {
  const day = startOfDay(date)
  const offset = (day.getDay() + 6) % 7
  return new Date(day.getFullYear(), day.getMonth(), day.getDate() - offset)
}

export function addDays(date: Date, days: number) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
}

export function startOfMonth(year: number, month: number) {
  return new Date(year, month, 1)
}

/** Whole days between two dates, ignoring the time of day. */
export function daysBetween(earlier: Date, later: Date) {
  return Math.round((startOfDay(later).getTime() - startOfDay(earlier).getTime()) / DAY_MS)
}

/** "hoje", "ontem", "há 3 dias". */
export function relativeDays(date: Date, now = new Date()) {
  const days = daysBetween(date, now)
  if (days <= 0) return 'hoje'
  if (days === 1) return 'ontem'
  return `há ${days} dias`
}

/** Consecutive weeks with at least one session, counting back from this week (or last week, if this one is still empty). */
export function weekStreak(sessionDates: Date[], now = new Date()) {
  const weeks = new Set(sessionDates.map((date) => dayKey(startOfWeek(date))))
  let week = startOfWeek(now)
  if (!weeks.has(dayKey(week))) week = addDays(week, -7)
  let streak = 0
  while (weeks.has(dayKey(week))) {
    streak += 1
    week = addDays(week, -7)
  }
  return streak
}

/** "42:18" or "1:02:05". */
export function formatDuration(ms: number) {
  const total = Math.max(0, Math.floor(ms / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (value: number) => String(value).padStart(2, '0')
  return hours ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}

export function formatLongDate(date: Date) {
  return date.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })
}
