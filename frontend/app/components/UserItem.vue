<script setup lang="ts">
import type {User} from "~/types/user.ts";

defineProps<{ user: User }>()
const emit = defineEmits<{ delete: [id: number] }>()
</script>

<template>
  <li>
    {{ user.name }}, {{ user.age }}
    <span v-if="user.description">- {{ user.description }}</span>
    <button @click="emit('delete', user.id)"> Удалить </button>
  </li>
</template>

<style scoped>

</style>