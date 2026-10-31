<script setup lang="ts">
import {
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartOptions,
} from 'chart.js'
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { formatSets, formatWeight } from '@/lib/format'
import type { HistoryPoint } from '@/types'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip)
ChartJS.defaults.font.family = getComputedStyle(document.body).fontFamily

const props = defineProps<{ points: HistoryPoint[] }>()

// Chart.js paints on canvas, so it reads the theme tokens instead of using CSS classes.
const token = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()
const SERIES_COLOR = token('--c-accent')
const SURFACE = token('--c-surface')
const MUTED_TEXT = token('--c-subtle')
const GRID = token('--c-line')
const TOOLTIP_BG = token('--c-fg')
const TOOLTIP_FG = token('--c-bg')

const data = computed(() => ({
  labels: props.points.map((point) => formatDate(point.date)),
  datasets: [
    {
      label: 'Carga máx.',
      data: props.points.map((point) => point.max_weight_kg),
      borderColor: SERIES_COLOR,
      backgroundColor: SERIES_COLOR,
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBorderColor: SURFACE,
      pointBorderWidth: 2,
      pointHitRadius: 16,
      tension: 0,
    },
  ],
}))

const options: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: TOOLTIP_BG,
      titleColor: TOOLTIP_FG,
      bodyColor: TOOLTIP_FG,
      displayColors: false,
      callbacks: {
        label: (item) => {
          const point = props.points[item.dataIndex]
          return [`${formatWeight(point.max_weight_kg)} kg`, formatSets(point.sets)]
        },
      },
    },
  },
  scales: {
    x: { grid: { display: false }, ticks: { color: MUTED_TEXT, maxRotation: 0, autoSkipPadding: 12 } },
    y: {
      grid: { color: GRID },
      border: { display: false },
      ticks: { color: MUTED_TEXT, callback: (value) => `${value} kg` },
    },
  },
}

function formatDate(isoDate: string) {
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year.slice(2)}`
}
</script>

<template>
  <div class="h-56">
    <Line :data="data" :options="options" aria-label="Evolução da carga máxima" role="img" />
  </div>
</template>
