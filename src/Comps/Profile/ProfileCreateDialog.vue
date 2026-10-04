<script setup lang="ts">
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';
import type { Profile, ProfileCreate } from '@/stores/useProfiles';
import { readThumbnailFile } from '@/utils/thumbnail';
import { ref, watch } from 'vue';

const props = withDefaults(defineProps<{ profile?: Profile | null; loading?: boolean }>(), {
    profile: null,
    loading: false,
});
const isOpen = defineModel<boolean>({ default: false })
const emit = defineEmits<{ submit: [data: ProfileCreate] }>()

const create_form_name = ref("")
const create_form_desc = ref("")
const thumbnail = ref("")
const thumbnailError = ref("")

const name_error = ref("")

function selectThumbnail(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    thumbnailError.value = "";
    void readThumbnailFile(file).then((value) => {
        thumbnail.value = value;
    }).catch((error: unknown) => {
        thumbnailError.value = error instanceof Error ? error.message : String(error);
    });
    input.value = "";
}

function handleSubmit(): void {
    if (!create_form_name.value.trim()) {
        name_error.value = "Profile name is required."
        return
    }

    name_error.value = ""
    emit('submit', {
        name: create_form_name.value.trim(),
        description: create_form_desc.value.trim(),
        thumbnail: thumbnail.value,
    })
}

watch(create_form_name, (newValue) => {
    if (newValue.trim()) {
        name_error.value = ""
    }
})

watch([isOpen, () => props.profile], ([open, profile]) => {
    if (open) {
        create_form_name.value = profile?.name ?? ""
        create_form_desc.value = profile?.description ?? ""
        thumbnail.value = profile?.thumbnail ?? ""
    } else {
        create_form_name.value = ""
        create_form_desc.value = ""
        thumbnail.value = ""
        name_error.value = ""
        thumbnailError.value = ""
    }
})
</script>

<template>
    <WDialog v-model="isOpen" :title="profile ? 'Profile settings' : 'Create profile'">
        <div class="grid w-full min-w-0 gap-4">
            <div>
                <WInput v-model="create_form_name" label="Name" :error="name_error" />
            </div>

            <WTextarea v-model="create_form_desc" label="Description" />
            <div class="grid gap-2">
                <label class="grid gap-1.5 text-sm font-medium text-neutral-700">
                    <span>Thumbnail</span>
                    <input type="file" accept="image/png,image/jpeg,image/webp" class="min-w-0 text-xs file:mr-3 file:rounded file:border-0 file:bg-neutral-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-neutral-700 hover:file:bg-neutral-200" @change="selectThumbnail" />
                </label>
                <div v-if="thumbnail" class="relative aspect-[16/7] max-w-sm overflow-hidden rounded border border-neutral-200 bg-neutral-50">
                    <img :src="thumbnail" alt="Profile thumbnail preview" class="size-full object-cover" />
                </div>
                <p v-if="thumbnailError" class="text-xs text-rose-700" role="alert">{{ thumbnailError }}</p>
                <WButton v-if="thumbnail" type="button" variant="secondary" class="justify-self-start" @click="thumbnail = ''">Remove thumbnail</WButton>
                <p class="text-xs text-neutral-500">PNG, JPEG, or WebP up to 1 MB.</p>
            </div>
        </div>
        <template #footer>
            <WButton variant="secondary" :disabled="loading" @click="isOpen = false">Cancel</WButton>
            <WButton :loading="loading" @click="handleSubmit">
                {{ profile ? 'Save profile' : 'Create profile' }}
            </WButton>
        </template>
    </WDialog>
</template>
