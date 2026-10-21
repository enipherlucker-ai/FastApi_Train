export default defineNuxtRouteMiddleware(async (to) => {
    const currentUser = useCurrentUser()
    if (currentUser.value === null) {
        await loadCurrentUser()
    }

    if (currentUser.value === null && to.path !== '/login') {
        return navigateTo('/login')
    }
    if (currentUser.value !== null && to.path === '/login') {
        return navigateTo('/')
    }
})