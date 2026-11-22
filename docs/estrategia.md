# Descrição da Estratégia

## Índice

1. **Interface com a Engine e Ciclo de Vida**

    1.1. Assinatura da função (`estrategia(grafo)`) e perspectiva normalizada (`time` 0, 1, 2)

    1.2. Persistência do módulo em memória entre rodadas e partidas

2. **Pré-computação e Cache Estático Global**
   
   2.1. Assinatura estrutural do grafo e invalidação de cache entre mapas

   2.2. Mapeamento bietivo de rótulos para índices (`0..n-1`) e vetor de pesos ($W$)

   2.3. Cálculo único da matriz de distâncias mínimas ($D$) via `networkx`

   2.4. Pré-cálculo da Centralidade de Proximidade Ponderada ($C_w$)

3. **Leitura do Estado Atual e Representação Canônica**

   3.1. Identificação dos conjuntos atuais ($A$ e $B$) e vértices livres

   3.2. Codificação de estados via *bitmasks* (aproveitamento da comutatividade)
   
   3.3. Cálculo automático da profundidade restante ($6 - (|A| + |B|)$)

4. **Ordenação de Movimentos Candidatos**

   4.1. Priorização de vértices livres por $C_w$ decrescente para acelerar cortes

5. **Motor de Busca: Minimax com Poda Alfa-Beta e Tabela de Transposição**

   5.1. Estrutura recursiva (`MAX` / `MIN`) e indução retroativa

   5.2. Consulta e atualização da Tabela de Transposição com flags (`EXATO`, `LOWER`, `UPPER`)
   5.3. Aplicação dos cortes Alfa-Beta ($\alpha \ge \beta$)

6. **Avaliação Terminal nas Folhas ($|A| = 3$ e $|B| = 3$)**

   6.1. Cálculo exato da utilidade $U(A, B) = S_{\text{próprio}} - S_{\text{adversário}}$

   6.2. Tratamento de empates de distância ($+0,5 \cdot W[v]$)

   6.3. Otimização do laço interno de avaliação em Python

7. **Decisão na Raiz e Cascata de Desempate Determinística**

   7.1. Coleta dos lances ótimos de mesmo valor garantido ($V^*$)

   7.2. Critério 1: Resiliência (Margem Média contra respostas do oponente)

   7.3. Critério 2: Centralidade de Proximidade Ponderada ($C_w$)

   7.4. Critério 3: Máxima Distância Interna (Anti-Canibalização)

   7.5. Critério 4: Ordem Lexicográfica / Menor Índice

8. **Retorno, Validação e Conformidade**

   8.1. Conversão do índice escolhido de volta ao rótulo original em `grafo.nodes`

   8.2. Requisitos de entrega (`resposta.py`), testes de benchmark e roteiro de defesa presencial