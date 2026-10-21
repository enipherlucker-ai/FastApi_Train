<script setup lang="ts">
const currentUser = useCurrentUser()

async function onLogout(){
  await $fetch('api/auth/logout', {method: 'POST'})
  currentUser.value = null
  await navigateTo('/login')
}

</script>

<template>
  <main>
    <h1>Привет, {{ currentUser?.name }}!</h1>
    <button @click="onLogout">Выйти</button>
  </main>
</template>