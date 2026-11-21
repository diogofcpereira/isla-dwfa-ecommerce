// src/composables/useFetch.ts — os estados de um ecrã que carrega dados num só sítio:
// a carregar · erro (com Retry) · dados. O "vazio" decide-o o ecrã, com os dados na mão.
import { ref, watchEffect, type Ref } from 'vue'

import { errorMessage } from '@/api/client'
import type { Status } from '@/types'

export function useFetch<T>(load: () => Promise<T>) {
  const data = ref<T | null>(null) as Ref<T | null>
  const status = ref<Status>('idle')
  const error = ref<string | null>(null)

  // Cada execução recebe um número; só a mais recente pode escrever o resultado.
  // Evita que uma resposta lenta de uma pesquisa antiga apague a da pesquisa nova.
  let ticket = 0

  async function run() {
    const mine = ++ticket
    status.value = 'loading'
    error.value = null
    try {
      // load() lê search.value, page.value, props.id… de forma síncrona antes do
      // primeiro await: é aí que o watchEffect fica a saber de que depende.
      const result = await load()
      if (mine !== ticket) return
      data.value = result
      status.value = 'ok'
    } catch (e) {
      if (mine !== ticket) return
      status.value = 'error'
      error.value = errorMessage(e)
    }
  }

  // Corre agora e outra vez sempre que algo que load() leu muda.
  watchEffect(() => {
    void run()
  })

  return { data, status, error, reload: run }
}
