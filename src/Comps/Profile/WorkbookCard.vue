<script setup lang="ts">
import type { Workbook } from '@/stores/useWorkbooks';
import { RouterLink } from 'vue-router';

const props = defineProps<{ workbook: Workbook; profileName: string }>();
const emit = defineEmits<{ delete: [workbook: Workbook] }>();

function formatDate(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.getTime())
        ? value
        : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}
</script>

<template>
    <article
        class="flex min-h-40 flex-col justify-between border border-neutral-200 bg-white p-5 transition hover:border-neutral-400">
        <img v-if="workbook.thumbnail" :src="workbook.thumbnail" :alt="`${workbook.title} thumbnail`" class="mb-4 aspect-16/7 w-full rounded object-cover" />
        <div>
            <div class="mb-3 flex items-start justify-between gap-3">
                <h2 class="wrap-break-word text-lg font-semibold text-neutral-950">{{ workbook.title }}</h2>
                <span class="shrink-0 rounded-md bg-neutral-100 px-2 py-1 text-xs tabular-nums text-neutral-500">
                    #{{ workbook.id }}
                </span>
            </div>
            <p v-if="workbook.description" class="line-clamp-3 text-sm leading-6 text-neutral-600">
                {{ workbook.description }}
            </p>
            <p v-else class="text-sm text-neutral-400">No description</p>
                <div class="pt-3 flex items-center justify-end gap-2 text-xs text-neutral-400">
                    <button type="button" class="inline-flex h-9 items-center justify-center rounded border border-rose-300 px-3 text-sm font-medium text-rose-700 transition hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-700/20" @click="emit('delete', props.workbook)">
                    Delete
                    </button>
                    <RouterLink
                        :to="{ name: 'workbook', params: { name: profileName, workbookName: workbook.title } }"
                        class="inline-flex h-9 items-center justify-center gap-2 rounded border border-green-700 bg-green-700 px-3 text-sm font-medium text-white transition hover:bg-green-800 focus:outline-none focus:ring-2 focus:ring-green-700/25"
                    >
                        Open
                    </RouterLink>
            </div>
        </div>
        <p class="mt-5 text-xs text-neutral-400">Updated {{ formatDate(workbook.updated_at) }}</p>
    </article>
</template>
