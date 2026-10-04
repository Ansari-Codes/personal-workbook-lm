<script setup lang="ts">
import { ref, watch } from 'vue';
import type { Caller, CallerCreate } from '@/stores/useCallers';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';

const props = withDefaults(defineProps<{ caller?: Caller | null; loading?: boolean }>(), {
  caller: null,
  loading: false,
});
const isOpen = defineModel<boolean>({ default: false });
const emit = defineEmits<{ submit: [payload: CallerCreate] }>();
const name = ref('');
const description = ref('');
const content = ref('');
const error = ref('');

watch([isOpen, () => props.caller], ([open, caller]) => {
  if (open) {
    name.value = caller?.name ?? '';
    description.value = caller?.description ?? '';
    content.value = caller?.content ?? 'def INVOKE(**settings):\n    return {"success": False, "error": "Implement this caller"}\n\n\ndef MODEL(**settings):\n    return {"success": False, "models": [], "error": "Implement this caller"}\n';
    error.value = '';
  } else {
    name.value = '';
    description.value = '';
    content.value = '';
    error.value = '';
  }
});

function submit(): void {
  if (!name.value.trim() || !content.value.trim()) {
    error.value = 'Name and Python caller code are required.';
    return;
  }
  if (!/^\s*(async\s+)?def\s+INVOKE\s*\(/m.test(content.value)) {
    error.value = 'Caller code must define INVOKE(**kwargs).';
    return;
  }
  if (!/^\s*(async\s+)?def\s+MODEL\s*\(/m.test(content.value)) {
    error.value = 'Caller code must define MODEL(**kwargs).';
    return;
  }
  error.value = '';
  emit('submit', {
    name: name.value.trim(),
    description: description.value.trim(),
    content: content.value,
  });
}
</script>

<template>
  <WDialog
    v-model="isOpen"
    :title="caller ? 'Edit caller' : 'Add caller'"
    description="INVOKE and MODEL receive the selected settings and return success envelopes: {success, ...} or {success: false, error}."
  >
    <div class="grid gap-4">
      <WInput v-model="name" label="Name" maxlength="120" required />
      <WTextarea v-model="description" label="Description" />
      <label class="grid gap-2 text-sm font-semibold text-neutral-700">
        <span>Python code</span>
        <textarea
          v-model="content"
          rows="10"
          spellcheck="false"
          class="w-full resize-y border border-neutral-300 bg-neutral-950 p-3 font-mono text-sm text-neutral-100 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-600/20"
          aria-label="Caller Python code"
        />
      </label>
      <p v-if="error" role="alert" class="text-sm text-rose-700">{{ error }}</p>
    </div>
    <template #footer>
      <WButton variant="secondary" :disabled="loading" @click="isOpen = false">Cancel</WButton>
      <WButton :loading="loading" @click="submit">{{ caller ? 'Save changes' : 'Add caller' }}</WButton>
    </template>
  </WDialog>
</template>
