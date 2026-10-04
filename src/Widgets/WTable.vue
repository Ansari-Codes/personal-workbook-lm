<script setup lang="ts" generic="TRow extends object">
import type { VNode } from 'vue';

export interface WTableColumn<TRow extends object> {
  key: keyof TRow & string;
  label: string;
  headerClass?: string;
  cellClass?: string;
}

const props = withDefaults(defineProps<{
  data: TRow[];
  columns: readonly WTableColumn<TRow>[];
  rowKey?: keyof TRow & string;
  emptyMessage?: string;
}>(), {
  emptyMessage: 'No rows to display.',
});

const emit = defineEmits<{
  'row-click': [row: TRow, event: MouseEvent];
  'row-left-click': [row: TRow, event: MouseEvent];
  'row-right-click': [row: TRow, event: MouseEvent];
  'row-hover': [row: TRow, event: MouseEvent];
  'row-hover-end': [row: TRow, event: MouseEvent];
}>();

defineSlots<{
  [slotName: `cell-${string}`]: (props: { row: TRow; value: unknown; column: WTableColumn<TRow> }) => VNode[];
  actions?: (props: { row: TRow }) => VNode[];
}>();

function rowIdentity(row: TRow, index: number): string | number {
  const value = props.rowKey ? row[props.rowKey] : undefined;
  return typeof value === 'string' || typeof value === 'number' ? value : index;
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function handleClick(row: TRow, event: MouseEvent): void {
  emit('row-click', row, event);
  emit('row-left-click', row, event);
}

function handleRightClick(row: TRow, event: MouseEvent): void {
  event.preventDefault();
  emit('row-right-click', row, event);
}
</script>

<template>
  <div class="w-full overflow-x-auto border border-neutral-200 bg-white">
    <table class="w-full min-w-2xl border-collapse text-left text-sm">
      <thead class="bg-neutral-50 text-xs uppercase text-neutral-500">
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            scope="col"
            :class="['px-4 py-3 font-semibold', column.headerClass]"
          >
            {{ column.label }}
          </th>
          <th v-if="$slots.actions" scope="col" class="px-4 py-3 text-right font-semibold">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-neutral-100">
        <tr v-if="data.length === 0">
          <td :colspan="columns.length + ($slots.actions ? 1 : 0)" class="px-4 py-12 text-center text-neutral-500">
            {{ emptyMessage }}
          </td>
        </tr>
        <tr
          v-for="(row, index) in data"
          :key="rowIdentity(row, index)"
          class="transition-colors hover:bg-neutral-50"
          @click="handleClick(row, $event)"
          @contextmenu="handleRightClick(row, $event)"
          @mouseenter="emit('row-hover', row, $event)"
          @mouseleave="emit('row-hover-end', row, $event)"
        >
          <td v-for="column in columns" :key="column.key" :class="['px-4 py-3 align-middle text-neutral-700', column.cellClass]">
            <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]" :column="column">
              {{ displayValue(row[column.key]) }}
            </slot>
          </td>
          <td v-if="$slots.actions" class="px-4 py-3 text-right" @click.stop>
            <slot name="actions" :row="row" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
