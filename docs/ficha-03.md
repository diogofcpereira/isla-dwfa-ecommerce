## Respostas de reflexão

1. Um cliente pede GET /api/v1/orders/7/, encomenda de outro cliente. A API responde 404,
não 403. Expliquem a diferença entre 401, 403 e 404 neste contexto e porque é que a escolha
do 404 é uma decisão de segurança e não um erro.

R: 401 diz "não sei quem és" (sem token ou token inválido); 403 diz "sei quem és e o recurso existe, mas não podes"; 404 diz "para ti, isto não existe", porque o queryset filtrado por dono nem encontra a encomenda.
Responder 403 confirmaria a um atacante que a encomenda 7 existe, e ele podia percorrer ids para descobrir quantas encomendas há. O 404 não revela nada: é uma decisão de segurança (não divulgar informação), não um erro.

2. Configuraram CORS_ALLOWED_ORIGINS. Porque é que isso não protege o servidor de um curl ou
de um script feito por um atacante — e o que é que protege, então? O que é que de facto
impede o acesso indevido à API?

R: O CORS é aplicado pelo browser: o servidor só envia cabeçalhos a dizer que origens podem ler as respostas, e quem bloqueia é o browser. O `curl` ou um script ignoram esses cabeçalhos e conseguem sempre fazer o pedido. O CORS protege os utilizadores, porque impede que um site malicioso aberto no browser deles leia as respostas da API em nome deles. O que impede de facto o acesso indevido é a autenticação (JWT) e a autorização (permission classes e queryset filtrado), verificadas no servidor em cada pedido.