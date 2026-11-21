<!-- views/LoginView.vue — o formulário de login: fala com o TokenObtainPairSerializer. -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { useAuth } from '@/stores/auth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

// Para onde voltar depois do login (?next=/orders). Só caminhos internos: um
// ?next=https://outro-site.com seria um "open redirect".
function nextPath(): string {
  const next = route.query.next
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//')
    ? next
    : '/orders'
}

async function submit() {
  submitting.value = true
  error.value = null
  try {
    await auth.login(username.value, password.value)
    await router.push(nextPath()) // de volta para onde ia
  } catch (e) {
    const status = e instanceof ApiError ? e.status : 0
    if (status === 401) error.value = 'Utilizador ou password errados.'
    else if (status === 429) error.value = 'Demasiadas tentativas — espera um minuto.'
    else error.value = 'Erro de rede (a API está a correr?)'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="login">
    <h1>Entrar</h1>
    <!-- .prevent: o browser não recarrega a página ao submeter -->
    <form @submit.prevent="submit">
      <label>
        Utilizador
        <input v-model.trim="username" name="username" autocomplete="username" required />
      </label>
      <label>
        Password
        <input
          v-model="password"
          name="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <button type="submit" :disabled="submitting">
        {{ submitting ? 'A entrar…' : 'Entrar' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.login {
  max-width: 22rem;
}
form {
  display: grid;
  gap: 0.75rem;
}
label {
  display: grid;
  gap: 0.25rem;
}
input {
  padding: 0.5rem;
  font-size: 1rem;
}
.error {
  color: #b00020;
  margin: 0;
}
</style>
