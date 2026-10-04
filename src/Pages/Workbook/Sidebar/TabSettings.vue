<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ApiError } from '@/stores/api';
import { useWorkbookSettings } from '@/stores/useWorkbookSettings';
import { useWorkbooksStore, type ChatConfiguration, type Workbook } from '@/stores/useWorkbooks';
import { useNotifier } from '@/Widgets';
import WButton from '@/Widgets/WButton.vue';
import WInput from '@/Widgets/WInput.vue';
import WTextarea from '@/Widgets/WTextarea.vue';
import WSelect from '@/Widgets/WSelect.vue';
import WOption from '@/Widgets/WOption.vue';
import WCheck from '@/Widgets/WCheck.vue';
import { readThumbnailFile } from '@/utils/thumbnail';

const props = defineProps<{
	profileId: number;
	workbookId: number;
	workbookName: string;
	workbookDescription: string;
	workbookThumbnail: string | null;
	isLoading: boolean;
	loadError: string;
}>();

const emit = defineEmits<{ workbookUpdated: [workbook: Workbook] }>();

const workbookStore = useWorkbooksStore();
const settings = useWorkbookSettings();
const { notify } = useNotifier();

const title = ref(props.workbookName);
const description = ref(props.workbookDescription);
const thumbnail = ref(props.workbookThumbnail ?? '');
const thumbnailError = ref('');
const isSaving = ref(false);
const chatConfiguration = ref<ChatConfiguration>(
	workbookStore.chatConfigurationFor(props.profileId, props.workbookId),
);

const maxToolCallsValue = computed<string | number>({
	get: () => chatConfiguration.value.maxToolCalls ?? 'unlimited',
	set: (value) => {
		const parsed = value === 'unlimited' ? null : Number(value);
		if (parsed === null || (Number.isSafeInteger(parsed) && parsed > 0)) {
			chatConfiguration.value.maxToolCalls = parsed;
		}
	},
});

function errorMessage(error: unknown): string {
	if (error instanceof ApiError) {
		return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
	}
	return error instanceof Error ? error.message : String(error);
}

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

async function saveWorkbook(): Promise<void> {
	isSaving.value = true;
	try {
		const workbook = await workbookStore.updateWorkbook(props.profileId, props.workbookId, {
			title: title.value.trim(),
			description: description.value.trim(),
			thumbnail: thumbnail.value,
		});
		if (!workbook) throw new Error('The workbook update was empty.');
		emit('workbookUpdated', workbook);
		notify('Workbook details saved.', 'success', 4000);
	} catch (error) {
		notify(`Could not save workbook details: ${errorMessage(error)}`, 'error', 8000);
	} finally {
		isSaving.value = false;
	}
}

async function toggleUseTools(enabled: boolean): Promise<void> {
	const previous = settings.useTools;
	settings.useTools = enabled;
	isSaving.value = true;
	try {
		await settings.saveSettings(props.profileId, props.workbookId);
	} catch (error) {
		settings.useTools = previous;
		notify(`Could not save tool setting: ${errorMessage(error)}`, 'error', 8000);
	} finally {
		isSaving.value = false;
	}
}

watch(() => props.workbookName, (name) => { title.value = name; });
watch(() => props.workbookDescription, (detail) => { description.value = detail; });
watch(() => props.workbookThumbnail, (value) => { thumbnail.value = value ?? ''; });
watch(
	chatConfiguration,
	(configuration) => {
		workbookStore.saveChatConfiguration(props.profileId, props.workbookId, configuration);
	},
	{ deep: true },
);
</script>

<template>
	<section class="h-full min-h-0 overflow-y-auto p-4">
		<div v-if="isLoading" class="px-1 py-4 text-[13px] text-neutral-500" role="status">
			Loading workbook settings…
		</div>

		<div v-else-if="loadError" class="px-1 py-4 text-[13px] text-red-700" role="alert">
			{{ loadError }}
		</div>

		<div v-else class="grid gap-6">
			<!-- Workbook identity -->
			<form class="grid gap-3" @submit.prevent="saveWorkbook">
				<header class="flex items-start justify-between gap-3">
					<div class="grid gap-0.5">
						<h3 class="text-xs font-bold tracking-tight text-neutral-700">Workbook</h3>
						<p class="text-[11px] leading-snug text-neutral-500">
							Name and description shown throughout the app.
						</p>
					</div>
					<WButton type="submit" size="sm" :loading="isSaving">Save</WButton>
				</header>

				<WInput v-model="title" label="Workbook name" maxlength="255" required />
				<WTextarea v-model="description" label="Description" :rows="3" />
				<div class="grid gap-2">
					<label class="grid gap-1.5 text-xs font-medium text-neutral-700">
						<span>Thumbnail</span>
						<input type="file" accept="image/png,image/jpeg,image/webp" class="min-w-0 text-[11px] file:mr-2 file:rounded file:border-0 file:bg-neutral-100 file:px-2 file:py-1.5 file:text-xs file:font-medium file:text-neutral-700 hover:file:bg-neutral-200" @change="selectThumbnail" />
					</label>
					<div v-if="thumbnail" class="aspect-16/7 overflow-hidden rounded border border-neutral-200 bg-neutral-50">
						<img :src="thumbnail" alt="Workbook thumbnail preview" class="size-full object-cover" />
					</div>
					<p v-if="thumbnailError" class="text-[11px] text-rose-700" role="alert">{{ thumbnailError }}</p>
					<WButton v-if="thumbnail" type="button" size="sm" variant="secondary" class="justify-self-start" @click="thumbnail = ''">Remove thumbnail</WButton>
					<p class="text-[11px] text-neutral-500">PNG, JPEG, or WebP up to 1 MB.</p>
				</div>
			</form>

			<hr class="border-neutral-100" />

			<!-- Response behavior -->
			<section class="grid gap-3">
				<header class="grid gap-0.5">
					<h3 class="text-xs font-bold tracking-tight text-neutral-700">Response</h3>
					<p class="text-[11px] leading-snug text-neutral-500">
						How the model replies and what it is allowed to do.
					</p>
				</header>

				<!-- Response mode -->
				<div class="flex items-center justify-between gap-3">
					<span class="text-xs font-medium text-neutral-600">Response mode</span>
					<div class="inline-flex gap-1" role="group" aria-label="Response mode">
						<WButton
							size="sm"
							:variant="chatConfiguration.stream ? 'ghost' : 'secondary'"
							:aria-pressed="!chatConfiguration.stream"
							@click="chatConfiguration.stream = false"
						>
							Standard
						</WButton>
						<WButton
							size="sm"
							:variant="chatConfiguration.stream ? 'secondary' : 'ghost'"
							:aria-pressed="chatConfiguration.stream"
							@click="chatConfiguration.stream = true"
						>
							Stream
						</WButton>
					</div>
				</div>

				<!-- Temperature -->
				<label class="flex items-center justify-between gap-3">
					<span class="text-xs font-medium text-neutral-600">Temperature</span>
					<div class="flex items-center gap-2">
						<input
							v-model.number="chatConfiguration.temperature"
							type="range"
							min="0"
							max="2"
							step="0.1"
							class="w-28 accent-green-700"
						/>
						<output class="w-8 text-right text-xs font-semibold tabular-nums text-neutral-800">
							{{ chatConfiguration.temperature.toFixed(1) }}
						</output>
					</div>
				</label>

				<!-- Top P -->
				<label class="flex items-center justify-between gap-3">
					<span class="text-xs font-medium text-neutral-600">Top P</span>
					<div class="flex items-center gap-2">
						<input
							v-model.number="chatConfiguration.topP"
							type="range"
							min="0"
							max="1"
							step="0.01"
							class="w-28 accent-green-700"
						/>
						<output class="w-8 text-right text-xs font-semibold tabular-nums text-neutral-800">
							{{ chatConfiguration.topP.toFixed(2) }}
						</output>
					</div>
				</label>

				<!-- History messages -->
				<label class="flex items-center justify-between gap-3">
					<span class="text-xs font-medium text-neutral-600">History messages</span>
					<input
						:value="chatConfiguration.contextLength"
						type="number"
						min="0"
						max="100"
						class="w-20 rounded-md border border-neutral-200 px-2 py-1 text-right text-xs tabular-nums text-neutral-800 focus:border-green-600 focus:outline-none"
						@input="
							chatConfiguration.contextLength = Math.min(
								100,
								Math.max(0, Math.floor(Number(($event.target as HTMLInputElement).value) || 0)),
							)
						"
					/>
				</label>

				<!-- Maximum tool calls -->
				<label class="flex items-center justify-between gap-3">
					<span class="text-xs font-medium text-neutral-600">Maximum tool calls</span>
					<select
						v-model="maxToolCallsValue"
						class="w-28 rounded-md border border-neutral-200 px-2 py-1 text-xs text-neutral-800 focus:border-green-600 focus:outline-none"
					>
						<option value="unlimited">Unlimited</option>
						<option v-for="limit in [1, 2, 3, 4, 5, 10, 20]" :key="limit" :value="limit">
							{{ limit }}
						</option>
					</select>
				</label>

				<!-- Toggles -->
				<div class="grid gap-2 pt-1">
					<WCheck v-model="chatConfiguration.allowHtml" class="items-start">
						<span class="grid gap-0.5">
							<strong class="text-xs font-semibold">Run HTML, CSS, and JavaScript previews</strong>
							<small class="text-[11px] leading-snug text-neutral-500">
								Runs fenced HTML snippets in an isolated sandbox.
							</small>
						</span>
					</WCheck>

					<WCheck
						:model-value="settings.useTools"
						:disabled="isSaving"
						class="items-start"
						@update:model-value="toggleUseTools"
					>
						<span class="grid gap-0.5">
							<strong class="text-xs font-semibold">Allow tools in chat</strong>
							<small class="text-[11px] leading-snug text-neutral-500">
								Let the model use selected workbook tools.
							</small>
						</span>
					</WCheck>
				</div>
			</section>
		</div>
	</section>
</template>