import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import { authMiddleware } from './api/auth'
import { api } from './api/client'
import App from './App.vue'
import router from './router'
import { useAuth } from './stores/auth'

const app = createApp(App)

app.use(createPinia())
api.use(authMiddleware) // Bearer em todos os pedidos + renovar uma vez num 401

// Antes de montar (e antes da primeira navegação): se há refresh guardado, recuperar a
// sessão. Assim o guard decide com a informação certa e um F5 não manda para o /login.
await useAuth().bootstrap() // top-level await: o Vite suporta

app.use(router)
app.mount('#app')
