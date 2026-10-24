<script setup lang="ts">
const currentUser = useCurrentUser()
const logoutError = ref('')

useHead({title: 'Главная'})

async function onLogout(){
  logoutError.value = ''
  try {
    await $fetch('/api/auth/logout', {method: 'POST'})
    currentUser.value = null
    await navigateTo('/login')
  } catch (err) {
    logoutError.value = 'Сервис авторизации недоступен, пожалуйста подождите'
  }

}

</script>

<template>
  <main>
    <h1>Привет, {{ currentUser?.name }}!</h1>
    {{ logoutError }}
    <button @click="onLogout">Выйти</button>
  </main>
</template>