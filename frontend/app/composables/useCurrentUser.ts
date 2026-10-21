import type { User } from "~/types/user"

export function useCurrentUser() {
    return useState<User | null>('current-user', () => null)
}

export async function loadCurrentUser() {
    const currentUser = useCurrentUser()
    const requestFetch = useRequestFetch()
    try {
        currentUser.value = await requestFetch<User>('/api/auth/me')
    } catch {
        currentUser.value = null
    }
}