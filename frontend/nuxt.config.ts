// https://nuxt.com/docs/api/configuration/nuxt-config
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  app: {
      head: {
          title: 'Cometa',
          htmlAttrs: { lang: 'ru' },
      },
  },
  routeRules: {
    '/api/auth/login': { proxy: `${apiTarget}/auth/login` },
    '/api/auth/logout': { proxy: `${apiTarget}/auth/logout` },
    '/api/auth/me': { proxy: `${apiTarget}/auth/me` },
  },
})