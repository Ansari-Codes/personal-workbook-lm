<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useProfilesStore, type Profile, type ProfileCreate, type ProfileUpdate } from '@/stores/useProfiles';
import { ApiError } from '@/stores/api';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WDialog from '@/Widgets/WDialog.vue';
import WInput from '@/Widgets/WInput.vue';
import ProfileCreateDialog from '@/Comps/Profile/ProfileCreateDialog.vue';

const profileStore = useProfilesStore();
const router = useRouter();
const { notify } = useNotifier();

const is_open = ref(false);
const isSaving = ref(false);
const isDeleteOpen = ref(false);
const isDeleting = ref(false);
const query = ref('');
const selectedProfile = ref<Profile | null>(null);
const pendingDelete = ref<Profile | null>(null);

const filteredProfiles = computed(() => {
  const search = query.value.trim().toLocaleLowerCase();
  if (!search) return profileStore.profiles;
  return profileStore.profiles.filter((profile) =>
    `${profile.name} ${profile.description ?? ''}`.toLocaleLowerCase().includes(search),
  );
});

const hasProfiles = computed(() => profileStore.profiles.length > 0);
const hasResults = computed(() => filteredProfiles.value.length > 0);

function enterProfile(profile: Profile) {
  router.push({ name: 'profile', params: { name: profile.name } });
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status === null
      ? error.message
      : `${error.message} (HTTP ${error.status})`;
  }
  return error instanceof Error ? error.message : String(error);
}

function openCreateDialog() {
  selectedProfile.value = null;
  is_open.value = true;
}

function editProfile(profile: Profile): void {
  selectedProfile.value = profile;
  is_open.value = true;
}

function requestDelete(profile: Profile) {
  pendingDelete.value = profile;
  isDeleteOpen.value = true;
}

async function create(data: ProfileCreate) {
  isSaving.value = true;
  try {
    await profileStore.createProfile(data);
    is_open.value = false;
    selectedProfile.value = null;
    notify('Profile created successfully!', 'success', 10000);
  } catch (error) {
    notify(`Failed to create profile: ${errorMessage(error)}`, 'error', 10000);
  } finally {
    isSaving.value = false;
  }
}

async function saveProfile(data: ProfileUpdate): Promise<void> {
  if (!selectedProfile.value) {
    await create(data as ProfileCreate);
    return;
  }
  isSaving.value = true;
  try {
    await profileStore.updateProfile(selectedProfile.value.id, data);
    is_open.value = false;
    selectedProfile.value = null;
    notify('Profile settings saved.', 'success', 5000);
  } catch (error) {
    notify(`Could not save profile: ${errorMessage(error)}`, 'error', 10000);
  } finally {
    isSaving.value = false;
  }
}

async function deleteProfile(): Promise<void> {
  if (!pendingDelete.value) return;
  isDeleting.value = true;
  try {
    await profileStore.deleteProfile(pendingDelete.value.id);
    notify('Profile deleted.', 'success', 5000);
    pendingDelete.value = null;
    isDeleteOpen.value = false;
  } catch (error) {
    notify(`Could not delete profile: ${errorMessage(error)}`, 'error', 10000);
  } finally {
    isDeleting.value = false;
  }
}

onMounted(async () => {
  try {
    await profileStore.fetchProfiles();
  } catch (error) {
    notify(`Failed to load profiles: ${errorMessage(error)}`, 'error', 10000);
  }
});
</script>

<template>
  <div class="min-h-screen bg-linear-to-b from-neutral-50 to-white">
    <div class="max-w-6xl mx-auto px-6 py-10 font-sans antialiased sm:px-8">

      <!-- Header -->
      <header class="w-full border-b border-neutral-200 pb-6 mb-8 flex flex-wrap justify-between items-end gap-4">
        <div class="flex items-center gap-4">
          <img
            src="/public/LOGO.svg"
            alt="Logo"
            width="72"
            height="72"
            class="aspect-square rounded-xl shadow-sm ring-1 ring-neutral-200/60"
          />
          <div>
            <h1 class="text-3xl font-bold tracking-tight text-neutral-900">Profiles</h1>
            <p class="text-sm text-neutral-500 mt-1">
              Manage and view system profile information.
            </p>
          </div>
        </div>
        <WButton @click="openCreateDialog">
          <span class="inline-flex items-center gap-1.5">
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M10 3a1 1 0 0 1 1 1v5h5a1 1 0 1 1 0 2h-5v5a1 1 0 1 1-2 0v-5H4a1 1 0 1 1 0-2h5V4a1 1 0 0 1 1-1Z" />
            </svg>
            Create profile
          </span>
        </WButton>
      </header>

      <!-- Search -->
      <div class="mb-8 max-w-md">
        <WInput
          v-model="query"
          label="Search profiles"
          type="search"
          placeholder="Name or description"
        />
        <p v-if="hasProfiles" class="mt-2 text-xs text-neutral-400">
          {{ filteredProfiles.length }} of {{ profileStore.profiles.length }} profiles
        </p>
      </div>

      <!-- Roster grid -->
      <div
        v-if="hasResults"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
      >
        <article
          v-for="profile in filteredProfiles"
          :key="profile.id"
          class="group relative flex flex-col justify-between overflow-hidden bg-white border border-neutral-200 rounded-2xl transition-all duration-200 hover:border-neutral-300 hover:shadow-md hover:-translate-y-0.5"
        >
          <img
            v-if="profile.thumbnail"
            :src="profile.thumbnail"
            :alt="`${profile.name} thumbnail`"
            class="aspect-16/7 w-full object-cover bg-neutral-100"
            loading="lazy"
          />
          <div
            v-else
            class="aspect-16/7 w-full bg-gradient-to-br from-neutral-100 to-neutral-200 flex items-center justify-center"
          >
            <span class="text-3xl font-bold text-neutral-300 uppercase select-none">
              {{ profile.name.charAt(0) }}
            </span>
          </div>

          <div class="flex flex-1 flex-col justify-between p-5">
            <div class="flex flex-col gap-1.5">
              <h2 class="text-lg capitalize font-semibold tracking-tight text-neutral-900 group-hover:text-black">
                {{ profile.name }}
              </h2>
              <p
                v-if="profile.description"
                class="text-sm leading-relaxed text-neutral-600 line-clamp-3"
              >
                {{ profile.description }}
              </p>
              <p v-else class="text-sm italic text-neutral-400">
                No description provided.
              </p>
            </div>

            <div class="pt-5 mt-4 border-t border-neutral-100 flex flex-wrap items-center justify-end gap-2">
              <WButton variant="secondary" @click="editProfile(profile)">
                Settings
              </WButton>
              <WButton variant="danger" @click="requestDelete(profile)">
                Delete
              </WButton>
              <WButton @click="enterProfile(profile)">
                Enter
              </WButton>
            </div>
          </div>
        </article>
      </div>

      <!-- Empty: no profiles at all -->
      <div
        v-else-if="!hasProfiles"
        class="flex flex-col items-center justify-center border-2 border-dashed border-neutral-200 rounded-2xl p-16 text-center bg-white/60"
      >
        <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
          <svg class="h-7 w-7 text-neutral-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
        </div>
        <span class="text-base font-semibold text-neutral-900">No profiles yet</span>
        <p class="text-sm text-neutral-500 max-w-sm mt-1">
          There are currently no active profile configurations available. Get started by creating your first profile.
        </p>
        <div class="mt-6">
          <WButton @click="openCreateDialog">Create your first profile</WButton>
        </div>
      </div>

      <!-- Empty: no search results -->
      <div
        v-else
        class="py-16 text-center text-sm text-neutral-500"
      >
        No profiles match
        <span class="font-medium text-neutral-700">“{{ query }}”</span>.
        <button
          type="button"
          class="ml-1 font-medium text-neutral-900 underline underline-offset-2 hover:text-neutral-700"
          @click="query = ''"
        >
          Clear search
        </button>
      </div>
    </div>
  </div>

  <!-- Create / Edit dialog -->
  <ProfileCreateDialog
    v-model="is_open"
    :profile="selectedProfile"
    :loading="isSaving"
    @submit="saveProfile"
  />

  <!-- Delete confirmation -->
  <WDialog
    v-model="isDeleteOpen"
    title="Delete profile"
    description="This permanently removes the profile and its workbooks, keys, callers, and tools."
  >
    <p class="text-sm text-neutral-700">
      Are you sure you want to delete
      <strong class="font-semibold text-neutral-900">{{ pendingDelete?.name }}</strong>?
      This action cannot be undone.
    </p>
    <template #footer>
      <WButton variant="secondary" :disabled="isDeleting" @click="isDeleteOpen = false">
        Cancel
      </WButton>
      <WButton variant="danger" :loading="isDeleting" @click="deleteProfile">
        Delete profile
      </WButton>
    </template>
  </WDialog>
</template>