/// <reference types="vite/client" />

// Tipos das variáveis de ambiente que a app lê (import.meta.env.VITE_*).
interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
