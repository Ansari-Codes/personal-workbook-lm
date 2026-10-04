<script setup lang="ts">
import { ref, watch } from 'vue';
import type { Tool } from '@/stores/useTools';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';

export interface ToolFormData {
  title: string;
  description: string;
  package?: File;
}

const props = withDefaults(defineProps<{ tool?: Tool | null; loading?: boolean }>(), {
  tool: null,
  loading: false,
});
const isOpen = defineModel<boolean>({ default: false });
const emit = defineEmits<{ submit: [payload: ToolFormData] }>();
const title = ref('');
const description = ref('');
const packageFile = ref<File | null>(null);
const error = ref('');

watch([isOpen, () => props.tool], ([open, tool]) => {
  if (open) {
    title.value = tool?.title ?? '';
    description.value = tool?.description ?? '';
    packageFile.value = null;
    error.value = '';
  } else {
    title.value = '';
    description.value = '';
    packageFile.value = null;
    error.value = '';
  }
});

function selectPackage(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] ?? null;
  error.value = '';
  if (file && !file.name.toLowerCase().endsWith('.zip')) {
    error.value = 'Select a ZIP archive.';
    input.value = '';
    packageFile.value = null;
    return;
  }
  if (file && file.size > 10 * 1024 * 1024) {
    error.value = 'ZIP files must be 10 MB or smaller.';
    input.value = '';
    packageFile.value = null;
    return;
  }
  packageFile.value = file;
}

function submit(): void {
  if (!title.value.trim()) {
    error.value = 'Tool title is required.';
    return;
  }
  if (!props.tool && !packageFile.value) {
    error.value = 'Choose the tool ZIP package.';
    return;
  }
  error.value = '';
  emit('submit', {
    title: title.value.trim(),
    description: description.value.trim(),
    ...(packageFile.value ? { package: packageFile.value } : {}),
  });
}
</script>

<template>
  <WDialog
    v-model="isOpen"
    :title="tool ? 'Edit tool details' : 'Upload tool package'"
    description="A ZIP must contain non-empty main.py, README.md, and schema.json files."
  >
    <div class="grid gap-4">
      <WInput v-model="title" label="Title" maxlength="150" required />
      <WTextarea v-model="description" label="Description" />
      <label class="grid gap-2 text-sm font-semibold text-neutral-700">
        <span>{{ tool ? 'Replace package (optional)' : 'Tool ZIP package' }}</span>
        <input
          type="file"
          accept=".zip,application/zip"
          :required="!tool"
          class="block w-full border border-neutral-300 bg-white px-3 py-2 text-sm file:mr-3 file:border-0 file:bg-neutral-100 file:px-3 file:py-2 file:text-sm file:font-semibold"
          @change="selectPackage"
        />
        <span v-if="packageFile" class="text-xs font-normal text-neutral-500">{{ packageFile.name }}</span>
        <span v-else-if="tool" class="text-xs font-normal text-neutral-500">Leave empty to keep the current package.</span>
      </label>
      <p v-if="error" role="alert" class="text-sm text-rose-700">{{ error }}</p>
    </div>
    <template #footer>
      <WButton variant="secondary" :disabled="loading" @click="isOpen = false">Cancel</WButton>
      <WButton :loading="loading" @click="submit">{{ tool ? 'Save changes' : 'Upload tool' }}</WButton>
    </template>
  </WDialog>
</template>
