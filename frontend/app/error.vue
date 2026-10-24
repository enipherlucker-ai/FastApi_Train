<script setup lang="ts">
import type { NuxtError } from '#app'
const props = defineProps<{ error: NuxtError }>()
</script>

<template>
 <main>
   <h1 v-if="props.error.statusCode === 404 ">Страница не найдена</h1>
   <h1 v-else>Что-то сломалось, пожалуйста подождите</h1>
   <button @click="clearError({ redirect: '/' })" > На главную </button>
 </main>
</template>

<style scoped>

</style>