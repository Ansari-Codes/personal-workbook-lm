<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';

defineProps<{ profileName: string }>();
</script>

<template>
    <header class="border-b border-neutral-200 bg-white">
        <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-8">
            <div class="flex min-w-0 items-center gap-4">
                <RouterLink to="/" aria-label="Back to profiles"
                    class="inline-flex size-9 shrink-0 items-center justify-center rounded-lg border border-neutral-200 text-neutral-600 transition hover:bg-neutral-50 hover:text-neutral-950">
                    <span aria-hidden="true">&#8592;</span>
                </RouterLink>
                <div class="min-w-0">
                    <h1 class="truncate capitalize text-xl font-semibold text-neutral-950">Profile: {{ profileName }}</h1>
                </div>
            </div>

            <nav aria-label="Profile managers" class="flex flex-wrap items-center gap-2">
                <RouterLink :to="{ name: 'profile', params: { name: profileName } }"
                    class="inline-flex h-9 items-center rounded-lg border border-neutral-200 px-3 text-sm font-medium text-neutral-700 transition hover:bg-neutral-50 hover:text-neutral-950">
                    Workbooks
                </RouterLink>
                <RouterLink :to="{ name: 'profile-apis', params: { name: profileName } }"
                    class="inline-flex h-9 items-center rounded-lg border border-neutral-200 px-3 text-sm font-medium text-neutral-700 transition hover:bg-neutral-50 hover:text-neutral-950">
                    APIs
                </RouterLink>
                <RouterLink :to="{ name: 'profile-callers', params: { name: profileName } }"
                    class="inline-flex h-9 items-center rounded-lg border border-neutral-200 px-3 text-sm font-medium text-neutral-700 transition hover:bg-neutral-50 hover:text-neutral-950">
                    Callers
                </RouterLink>
                <RouterLink :to="{ name: 'profile-tools', params: { name: profileName } }"
                    class="inline-flex h-9 items-center rounded-lg border border-neutral-200 px-3 text-sm font-medium text-neutral-700 transition hover:bg-neutral-50 hover:text-neutral-950">
                    Tools
                </RouterLink>
            </nav>
        </div>
    </header>
    <RouterView></RouterView>
</template>
