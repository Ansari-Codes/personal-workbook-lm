import { defineStore } from "pinia";
import { ref } from 'vue';
import { apiRequest } from '@/stores/api';

export interface Profile {
    id: number;
    name: string;
    description?: string | null;
    thumbnail?: string | null;
}

export interface ProfileCreate {
    name: string;
    description?: string;
    thumbnail?: string | null;
}

export type ProfileUpdate = Partial<ProfileCreate>;

export const useProfilesStore = defineStore('profiles', () => {
    const endpoint = '/profiles';

    const profiles = ref<Profile[]>([]);
    const open_profiles = ref<Profile[]>([]);


    /**
     * GET /profiles -> list[ProfileRead]
     */
    async function fetchProfiles(): Promise<void> {
        const data = await apiRequest<Profile[]>(endpoint, 'GET');
        profiles.value = data || [];
    }

    /**
     * GET /profiles/{profile_id} -> ProfileRead
     */
    async function getProfile(id: number, trackAsOpen = false): Promise<Profile | null> {
        const data = await apiRequest<Profile>(`${endpoint}/${id}`, 'GET');

        if (data && trackAsOpen) {
            const alreadyOpen = open_profiles.value.some(p => p.id === data.id);
            if (!alreadyOpen) {
                open_profiles.value.push(data);
            }
        }
        return data;
    }

    /**
     * POST /profiles -> ProfileRead (Status 201)
     */
    async function createProfile(payload: ProfileCreate): Promise<Profile | null> {
        const newProfile = await apiRequest<Profile>(endpoint, 'POST', payload);
        if (newProfile) {
            profiles.value.push(newProfile);
        }
        return newProfile;
    }

    /**
     * PATCH /profiles/{profile_id} -> ProfileRead
     * Swapped from PUT to PATCH to explicitly match your FastAPI router schema.
     */
    async function updateProfile(id: number, payload: ProfileUpdate): Promise<Profile | null> {
        const updatedProfile = await apiRequest<Profile>(`${endpoint}/${id}`, 'PATCH', payload);

        if (updatedProfile) {
            const index = profiles.value.findIndex(p => p.id === id);
            if (index !== -1) profiles.value[index] = updatedProfile;
            const openIndex = open_profiles.value.findIndex(p => p.id === id);
            if (openIndex !== -1) open_profiles.value[openIndex] = updatedProfile;
        }
        return updatedProfile;
    }

    /**
     * DELETE /profiles/{profile_id} -> Status 204 Empty Body
     */
    async function deleteProfile(id: number): Promise<void> {
        await apiRequest<null>(`${endpoint}/${id}`, 'DELETE');
        profiles.value = profiles.value.filter(p => p.id !== id);
        closeProfile(id);
    }

    /**
     * Helper utility to safely remove a layout/view profile out of open tracker arrays
     */
    function closeProfile(id: number): void {
        open_profiles.value = open_profiles.value.filter(p => p.id !== id);
    }

    return {
        profiles,
        open_profiles,
        fetchProfiles,
        getProfile,
        createProfile,
        updateProfile,
        deleteProfile,
        closeProfile
    };
});

export default useProfilesStore;
