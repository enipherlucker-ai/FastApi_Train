<script setup lang="ts">
import type { User } from '~/types/user'

useHead({title: 'Авторизация'})

const currentUser = useCurrentUser()
const login = ref('')
const password = ref('')
const errorText = ref('')
const loading = ref(false)

async function onSubmit() {
  errorText.value = ''
  loading.value = true
  try {
    currentUser.value = await $fetch<User>('/api/auth/login', {
      method: 'POST',
      body: {login: login.value, password: password.value},
    })
    await navigateTo('/')
  } catch (error) {
    const status = (error as {statusCode?: number}).statusCode
    if (status === 401) {
      errorText.value = 'Неверный логин или пароль'
    } else if (status === 422) {
      errorText.value = 'Логин или пароль не подходят по формату'
    } else if (status === 502 || status === 503) {
      errorText.value = 'Технические работы, сервис авторизации недоступен, пожалуйста подождите'
    } else {
      errorText.value = 'Сервер не отвечает'
    }
  } finally {
    loading.value = false
  }

}
</script>

<template>
  <main class="page">
    <form class="card" @submit.prevent="onSubmit">
      <h1>Вход</h1>
      <p v-if="errorText" class="error">{{ errorText }}</p>

      <label>
        Логин
        <input v-model="login" autocomplete="username" required>
      </label>

      <label>
        Пароль
        <input v-model="password" type="password" autocomplete="current-password" required>
      </label>

      <button type="submit" :disabled="loading">{{ loading ? 'Входим' : 'Войти' }}</button>
    </form>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card {
  width: 320px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

h1 {
  margin: 0;
  font-size: 24px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}

input {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 16px;
}

input:focus {
  outline: 2px solid #2563eb;
  border-color: transparent;
}

button {
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 16px;
  cursor: pointer;
}

button:disabled {
  background: #93c5fd;
  cursor: wait;
}

.error {
  margin: 0;
  color: #dc2626;
  font-size: 14px;
}
</style>