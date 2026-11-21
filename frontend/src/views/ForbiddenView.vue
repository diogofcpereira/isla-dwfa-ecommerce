<!-- views/ForbiddenView.vue — um cliente tentou abrir um ecrã só de gestores (o 403 da SPA). -->
<template>
  <section>
    <h1>Sem permissão</h1>
    <p>Este ecrã é só para gestores. Se achas que devias ter acesso, fala com a DriveNow.</p>
    <RouterLink :to="{ name: 'cars' }">Ir para o catálogo</RouterLink>
  </section>
</template>
