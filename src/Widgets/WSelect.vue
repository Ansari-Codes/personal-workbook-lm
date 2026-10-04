<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
    label?: string;
    error?: string;
    hint?: string;
    /** When true, the user can type a value instead of picking one. */
    acceptCustom?: boolean;
}>();

const model = defineModel<string | number>({ default: '' });

/* Which input mode to render. When acceptCustom is true we always show
   the text input, since the user may want to type OR pick — but keeping
   the native select visible alongside would be redundant. Simplest
   behaviour: swap the control entirely. */
const isCustomMode = computed(() => props.acceptCustom === true);

/* Custom-mode input just writes straight to the same model. */
const customValue = computed({
    get: () => model.value ?? '',
    set: (v: string) => {
        model.value = v;
    },
});
</script>

<template>
    <label class="grid gap-1.5 text-sm font-medium text-neutral-700">
        <span v-if="label">{{ label }}</span>

        <!-- Default: native select with slot-provided options -->
        <select
            v-if="!isCustomMode"
            v-model="model"
            class="h-9 w-full rounded border border-neutral-300 bg-white px-2.5 text-sm font-normal outline-none focus:border-green-700 focus:ring-2 focus:ring-green-700/10"
        >
            <slot />
        </select>

        <!-- Custom mode: free-text input that maps to the same v-model -->
        <input
            v-else
            v-model="customValue"
            type="text"
            class="h-9 w-full rounded border border-neutral-300 bg-white px-2.5 text-sm font-normal outline-none focus:border-green-700 focus:ring-2 focus:ring-green-700/10"
        />

        <span v-if="error" class="text-xs font-medium text-rose-500">{{ error }}</span>
        <span v-else-if="hint" class="text-xs font-normal text-slate-500">{{ hint }}</span>
    </label>
</template>