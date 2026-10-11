<script setup lang="ts">
import type {User} from '~/types/user'

const name = ref('')
const age = ref(18)
const description = ref('')
const formError = ref('')

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const {data: users, pending, error, refresh} = await useFetch<User[]>(`${apiBase}/users`)

async function createUser() {
  formError.value = ''
  try {
    await $fetch('/create_user', {
      baseURL: apiBase,
      method: 'POST',
      query: {
        name: name.value,
        age: age.value,
        description: description.value || undefined,
      },
    })
    name.value = ''
    description.value = ''
    await refresh()
  } catch {
    formError.value = 'Не удалось создать пользователя'
  }
}

async function deleteUser(id: number) {
  await $fetch(`/users/delete${id}`, {
    baseURL: apiBase,
    method: 'DELETE',
  })
  await refresh()
}

</script>


<template>
  <main>
    <h1>Пользователи</h1>


    <form @submit.prevent="createUser">
      <input v-model="name" placeholder="Имя" required>
      <input v-model.number="age" placeholder="Возраст" min="0" required>
      <input v-model="description" placeholder="Описание">
      <button type="submit">Создать</button>
      <p v-if="formError">{{ formError }}</p>
    </form>

    <p v-if="pending">Загрузка</p>
    <p v-else-if="error">Ошибка загрузки: {{ error.message }}</p>
    <p v-else-if="!users?.length">Нет пользователей</p>
    <ul v-else>
      <UserItem v-for="user in users" :key="user.id" :user="user" @delete="deleteUser"/>
    </ul>
    <p v-if="pending">Загрузка</p>
    <p v-if="pending">Загрузка</p>
  </main>
</template>

