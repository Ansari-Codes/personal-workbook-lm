<script setup lang="ts">
import { ref, watch } from 'vue';
import type { WorkbookCreate } from '@/stores/useWorkbooks';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';
import { readThumbnailFile } from '@/utils/thumbnail';

withDefaults(defineProps<{ loading?: boolean }>(), { loading: false });
const isOpen = defineModel<boolean>({ default: false });
const emit = defineEmits<{ create: [data: WorkbookCreate] }>();

const title = ref('');
const description = ref('');
const titleError = ref('');
const thumbnail = ref('');
const thumbnailError = ref('');

function selectThumbnail(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  thumbnailError.value = '';
  void readThumbnailFile(file).then((value) => {
    thumbnail.value = value;
  }).catch((error: unknown) => {
    thumbnailError.value = error instanceof Error ? error.message : String(error);
  });
  input.value = '';
}

function submit(): void {
  const cleanTitle = title.value.trim();
  if (!cleanTitle) {
    titleError.value = 'Workbook title is required.';
    return;
  }
  titleError.value = '';
  emit('create', {
    title: cleanTitle,
    description: description.value.trim(),
    thumbnail: thumbnail.value,
  });
}

watch(title, (value) => {
  if (value.trim()) titleError.value = '';
});

watch(isOpen, (open) => {
  if (!open) {
    title.value = '';
    description.value = '';
    titleError.value = '';
    thumbnail.value = '';
    thumbnailError.value = '';
  }
});
</script>

<template>
  <WDialog v-model="isOpen" title="Create workbook" description="Add a workbook to this profile.">
    <div class="flex w-full flex-col gap-3 p-1">
      <WInput v-model="title" label="Title" :error="titleError" />
      <WTextarea v-model="description" label="Description" />
      <div class="grid gap-2">
        <label class="grid gap-1.5 text-sm font-medium text-neutral-700">
          <span>Thumbnail</span>
          <input type="file" accept="image/png,image/jpeg,image/webp" class="min-w-0 text-xs file:mr-3 file:rounded file:border-0 file:bg-neutral-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-neutral-700 hover:file:bg-neutral-200" @change="selectThumbnail" />
        </label>
        <div v-if="thumbnail" class="relative aspect-[16/7] max-w-sm overflow-hidden rounded border border-neutral-200 bg-neutral-50">
          <img :src="thumbnail" alt="Workbook thumbnail preview" class="size-full object-cover" />
        </div>
        <p v-if="thumbnailError" class="text-xs text-rose-700" role="alert">{{ thumbnailError }}</p>
        <WButton v-if="thumbnail" type="button" variant="secondary" class="justify-self-start" @click="thumbnail = ''">Remove thumbnail</WButton>
        <p class="text-xs text-neutral-500">PNG, JPEG, or WebP up to 1 MB.</p>
      </div>
    </div>
    <template #footer>
      <WButton :loading="loading" @click="submit">Create workbook</WButton>
    </template>
  </WDialog>
</template>
