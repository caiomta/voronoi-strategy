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

8. **Conversão do índice escolhido de volta ao rótulo original em `grafo.nodes`**

## 1. Interface com a Engine e Ciclo de Vida

### 1.1. Assinatura da função (`estrategia(grafo)`) e perspectiva normalizada (`time` 0, 1, 2)

* A estratégia recebe exclusivamente o objeto `grafo` (`networkx.Graph`) no estado atual da partida e deve retornar o vértice escolhido na rodada.
* Os exemplos da engine usam a assinatura `def estrategia(grafo):` (enquanto o texto da documentação menciona `def NOME_DA_ESTRATEGIA(grafo):`).
* Cada vértice `v` possui os atributos `grafo.nodes[v]["time"]` e `grafo.nodes[v]["peso"]`.
* A convenção de `"time"` na visão entregue ao jogador da rodada é sempre: `0` para vértice livre, `1` para centro próprio e `2` para centro adversário.
* A engine entrega uma cópia espelhada conforme quem está jogando (`1` e `2` invertidos quando é a vez da outra equipe), de modo que a função sempre enxerga `1` como próprio e `2` como adversário, e alterações locais em `grafo` não afetam o tabuleiro real.
* O peso varia de vértice para vértice sem limite fixo, e as distâncias entre pares de vértices são dadas pelo menor caminho no grafo, usando `networkx` como biblioteca externa permitida.

### 1.2. Persistência do módulo em memória entre rodadas e partidas

* Cada partida possui 6 rodadas alternadas com 3 centros para cada equipe (6 centros no total), e cada confronto tem duas partidas (alternando quem começa).
* A engine carrega o módulo da estratégia uma vez e executa chamadas sucessivas ao longo das rodadas e partidas.
* Variáveis globais do módulo permanecem em memória entre as rodadas de uma partida e entre as duas partidas de um confronto sobre o mesmo grafo.
* Isso permite manter estruturas pré-computadas e tabelas de busca em memória entre chamadas, exigindo validação/limpeza caso o grafo mude de um confronto para outro.

## 2. Pré-computação e Cache Estático Global

### 2.1. Assinatura estrutural do grafo e invalidação de cache entre mapas

* Como o módulo permanece carregado em memória entre rodadas e partidas, a estratégia gera uma assinatura estrutural imutável do grafo recebido (por exemplo, tupla ordenada de `(vertice, peso)` e tupla ordenada das arestas canônicas `(u, v)`).
* No início de cada chamada, a assinatura do grafo atual é comparada com a última assinatura armazenada no cache global.
* Se a assinatura coincidir (mesmo mapa nas rodadas seguintes ou na Partida 2 do mesmo confronto), todas as estruturas pré-computadas e a tabela de transposição são reutilizadas diretamente em $O(1)$.
* Se a assinatura divergir (novo mapa em outro confronto), o cache estático e o dicionário de memoização são limpos e reconstruídos para evitar contaminação entre grafos diferentes.

### 2.2. Mapeamento bietivo de rótulos para índices (`0..n-1`) e vetor de pesos ($W$)

* Os rótulos originais presentes em `grafo.nodes` (sejam strings como `'A'` ou inteiros arbitrários) são convertidos em índices inteiros contínuos de `0` a `n - 1` por meio de um mapeamento bietivo (`rotulo_para_idx` e `idx_para_rotulo`).
* Trabalhar com índices inteiros contínuos viabiliza o uso de listas diretas e *bitmasks* durante a busca, eliminando o custo de acesso a dicionários de objetos do `networkx` nos laços internos.
* O vetor de pesos $W$ de tamanho $n$ é extraído uma única vez na ordem dos índices (`W[i] = grafo.nodes[idx_para_rotulo[i]]["peso"]`), garantindo acesso imediato na avaliação terminal.

### 2.3. Cálculo único da matriz de distâncias mínimas ($D$) via `networkx`

* Executar buscas de menor caminho via `networkx` dentro da recursão do Minimax criaria um gargalo computacional severo.
* Por isso, `nx.all_pairs_shortest_path_length(grafo)` é chamado uma única vez por mapa para preencher uma matriz $D$ de dimensão $n \times n$ (lista de listas de inteiros), onde `D[u][v]` armazena o menor número de arestas entre os índices `u` e `v`.
* A matriz $D$ não é multiplicada pelo vetor de pesos $W$; ela é usada exclusivamente em comparações lógicas de menor distância ($d_A(v) < d_B(v)$) que decidem qual equipe recebe a integralidade ou a metade de $W[v]$.

### 2.4. Pré-cálculo da Centralidade de Proximidade Ponderada ($C_w$)

* Ainda na fase de pré-computação, calcula-se o vetor $C_w$ de tamanho $n$, que mede o alcance ponderado de cada vértice $u$ sobre todo o grafo:

$$C_w(u) = \sum_{v \in V} \frac{W[v]}{D[u][v] + 1}$$

* Esse vetor pré-calculado cumpre duas funções sem custo adicional durante a busca: ordenar os vértices livres candidatos antes de expandir a árvore (potencializando cortes precoces na Poda Alfa-Beta) e servir como critério determinístico na cascata de desempate na raiz.

## 3. Leitura do Estado Atual e Representação Canônica

### 3.1. Identificação dos conjuntos atuais ($A$ e $B$) e vértices livres

* A cada chamada da função de estratégia, percorre-se os índices `0..n-1` consultando o atributo `grafo.nodes[rotulo]["time"]` para classificar o estado atual do tabuleiro em três grupos disjuntos:
* **Conjunto $A$ (`time == 1`):** índices dos centros já pertencentes à nossa equipe.
* **Conjunto $B$ (`time == 2`):** índices dos centros já pertencentes ao adversário.
* **Vértices livres (`time == 0`):** lista de índices candidatos disponíveis para alocação na rodada atual e nas rodadas futuras.
* Como a engine sempre entrega a visão normalizada para quem está jogando, essa leitura é idêntica independentemente de a equipe ser $P_1$ ou $P_2$.


### 3.2. Codificação de estados via *bitmasks* (aproveitamento da comutatividade)

* No Jogo de Voronoi, a ordem em que os centros são escolhidos não altera as distâncias nem a pontuação final (por exemplo, escolher `{A, B, C}` gera exatamente o mesmo estado terminal que `{C, A, B}`).
* Para explorar essa comutatividade sem o custo de criar ou ordenar listas/conjuntos a cada passo da recursão, os conjuntos $A$ e $B$ são representados por dois inteiros (*bitmasks*): `mask_A` e `mask_B`, onde o bit na posição `i` vale `1` se o vértice de índice `i` pertence ao respectivo conjunto.
* Adicionar um vértice `i` a um conjunto na descida da recursão resume-se a uma operação bit a bit em $O(1)$ (`mask_A | (1 << i)`), e a chave canônica da Tabela de Transposição torna-se simplesmente a tupla `(mask_A, mask_B)`.
* Essa representação colapsa sequências permutadas equivalentes no mesmo estado, reduzindo o espaço teórico de $2,76 \times 10^9$ sequências ordenadas para no máximo $76,7$ milhões de pares de conjuntos finais únicos em $n = 40$.


### 3.3. Cálculo automático da profundidade restante ($6 - (\vert{}A\vert{} + \vert{}B\vert{})$)

* Como toda partida possui exatamente $6$ rodadas ($3$ centros por equipe), a profundidade restante da árvore de busca a partir do estado atual é determinada automaticamente por:

$$\text{profundidade\_restante} = 6 - (\vert{}A\vert{} + \vert{}B\vert{})$$

* A raiz da busca atual é sempre um nó **`MAX`** (pois a função só é invocada no turno da nossa equipe), alternando para **`MIN`** no nível seguinte até que `profundidade_restante == 0` ($\vert{}A\vert{} = 3$ e $\vert{}B\vert{} = 3$).
* Isso garante que o mesmo motor de busca opere de forma unificada em qualquer rodada e papel ($P_1$ nas profundidades $6, 4, 2$ e $P_2$ nas profundidades $5, 3, 1$), com queda abrupta do custo computacional a cada turno.

## 4. Ordenação de Movimentos Candidatos

### 4.1. Priorização de vértices livres por $C_w$ decrescente para acelerar cortes

* A eficiência da Poda Alfa-Beta depende diretamente da ordem em que os filhos de cada nó são avaliados: se os lances mais promissores forem testados primeiro, os limites $\alpha$ (para `MAX`) e $\beta$ (para `MIN`) convergem rapidamente, permitindo descartar a maior parte dos ramos subsequentes sem explorá-los.
* Antes de iniciar o laço de expansão da árvore (e aproveitando o vetor $C_w$ já pré-computado no cache estático), ordena-se a lista de índices dos vértices livres em ordem decrescente de Centralidade de Proximidade Ponderada ($C_w$).
* Como o vetor $C_w$ é fixo para um mesmo grafo, essa ordenação pode ser pré-calculada uma única vez na forma de uma lista global `ordem_nos` (índices ordenados de maior para menor $C_w$).
* Durante a busca, basta filtrar os vértices livres seguindo `ordem_nos` (verificando `not ((mask_A | mask_B) & (1 << i))`), eliminando o custo de chamar `sort()` dentro dos nós recursivos e garantindo que regiões de alto valor territorial sejam sempre avaliadas primeiro.

## 5. Motor de Busca: Minimax com Poda Alfa-Beta e Tabela de Transposição

### 5.1. Estrutura recursiva (`MAX` / `MIN` por paridade) e indução retroativa

* **Sistema de coordenadas fixo ($P_1$ vs. $P_2$):** Em vez de avaliar a pontuação da perspectiva relativa de quem chamou a função, o motor fixa a utilidade sempre na perspectiva global da partida:

$$U(P_1, P_2) = S_{P_1} - S_{P_2}$$

Assim, $P_1$ busca sempre **maximizar** $U$ (valores mais positivos) e $P_2$ busca sempre **minimizar** $U$ (valores mais negativos). Essa orientação também rege a escolha na raiz e a cascata de desempate (por exemplo, $P_1$ busca a maior margem média, enquanto $P_2$ busca a menor).
* **Mapeamento inicial por paridade:** Ao ler o `grafo` na raiz (onde `time == 1` é sempre nosso e `time == 2` é sempre do adversário), calcula-se `profundidade = 6 - (|A| + |B|)`:
* Se `profundidade` for **par** (`6, 4, 2`), somos $P_1$: `mask_P1 = mask_time_1`, `mask_P2 = mask_time_2` e a raiz busca **`MAX`**.
* Se `profundidade` for **ímpar** (`5, 3, 1`), somos $P_2$: `mask_P1 = mask_time_2`, `mask_P2 = mask_time_1` e a raiz busca **`MIN`**.
* **Assinatura interna da recursão:** Como a paridade da profundidade define unicamente quem joga, o parâmetro booleano `is_max` torna-se dispensável:
`minimax(mask_P1, mask_P2, profundidade, alfa, beta)`
* **Caso base (Folhas):** Quando `profundidade == 0` ($\vert{}P_1\vert{} = 3$ e $\vert{}P_2\vert{} = 3$), a descida é interrompida e a função calcula e retorna diretamente a utilidade terminal exata $U(\text{mask\_P1}, \text{mask\_P2})$.
* **Expansão em profundidade par (`profundidade % 2 == 0`, nó `MAX` — turno de $P_1$):**
* Inicializa `melhor_valor = -inf`.
* Percorre os índices `i` seguindo a lista pré-ordenada `ordem_nos`, ignorando ocupados via `if (mask_P1 | mask_P2) & (1 << i): continue`.
* Chama recursivamente `val = minimax(mask_P1 | (1 << i), mask_P2, profundidade - 1, alfa, beta)`.
* Atualiza `melhor_valor = max(melhor_valor, val)`.
* **Expansão em profundidade ímpar (`profundidade % 2 == 1`, nó `MIN` — turno de $P_2$):**
* Inicializa `melhor_valor = +inf`.
* Percorre os vértices livres em `ordem_nos` da mesma forma.
* Chama recursivamente `val = minimax(mask_P1, mask_P2 | (1 << i), profundidade - 1, alfa, beta)`.
* Atualiza `melhor_valor = min(melhor_valor, val)`.
* **Indução retroativa:** A árvore é percorrida em profundidade (DFS) de cima para baixo, mas os valores sobem das folhas para a raiz — cada nó `MAX` escolhe o maior piso garantido para $P_1$ e cada nó `MIN` escolhe o menor teto garantido para $P_2$.

### 5.2. Consulta e atualização da Tabela de Transposição com flags (`EXATO`, `LOWER`, `UPPER`)

* **Chave canônica minimalista (`(mask_P1, mask_P2)`):** Como $P_1$ joga exclusivamente em profundidades pares e $P_2$ exclusivamente em profundidades ímpares, o par `(mask_P1, mask_P2)` identifica de forma única não apenas os conjuntos de centros, mas também o turno e o papel (`MAX` ou `MIN`) do nó. Não se utiliza espelhamento de chaves intermediárias, pois trocar $P_1$ e $P_2$ em profundidades ímpares alteraria quem tem o próximo lance.
* **Reaproveitamento total entre Partida 1 e Partida 2:** Por usar o mesmo sistema de coordenadas ($P_1$ maximiza, $P_2$ minimiza) nas duas partidas do confronto sobre o mesmo grafo, todo estado, valor e flag calculados quando jogamos como $P_1$ na Partida 1 são **diretamente reutilizáveis** quando jogamos como $P_2$ na Partida 2, sem necessidade de inverter sinais ou trocar flags.
* **Gestão de memória (apenas nós intermediários):** Apenas estados com `profundidade >= 1` são armazenados em `memo`. Folhas (`profundidade == 0`) representam a maior parte dos nós visitados e são recalculadas diretamente em microssegundos, evitando o consumo excessivo de RAM e o custo de *hashing* em dicionários Python. Além disso, `memo.clear()` é executado sempre que a assinatura estrutural do grafo mudar entre confrontos.
* **Preservação da janela original:** Na entrada da função recursiva, salvam-se `alfa_orig = alfa` e `beta_orig = beta` antes de qualquer consulta ou corte.
* **Fase de Consulta (antes do laço de filhos):**
Se `(mask_P1, mask_P2)` estiver em `memo`, recupera-se `(val_salvo, flag)`:
* Se `flag == EXATO`: retorna `val_salvo` imediatamente.
* Se `flag == LOWER` (cota inferior): atualiza `alfa = max(alfa, val_salvo)`.
* Se `flag == UPPER` (cota superior): atualiza `beta = min(beta, val_salvo)`.
* Se, após a atualização, ocorrer `alfa >= beta`: retorna `val_salvo` imediatamente (poda instantânea via cache).
* **Fase de Atualização (após o laço de filhos):**
Antes de retornar `melhor_valor`, classifica-se o resultado frente à janela original:
* Se `melhor_valor <= alfa_orig`: salva `(melhor_valor, UPPER)` (*fail-low*: valor real é $\le \text{melhor\_valor}$).
* Senão, se `melhor_valor >= beta_orig`: salva `(melhor_valor, LOWER)` (*fail-high*: valor real é $\ge \text{melhor\_valor}$).
* Caso contrário ($\text{alfa\_orig} < \text{melhor\_valor} < \text{beta\_orig}$): salva `(melhor_valor, EXATO)`.

### 5.3. Aplicação dos cortes Alfa-Beta ($\alpha \ge \beta$)

* **No nó `MAX` (profundidade par):** Após cada filho retornar `val`, atualiza-se `alfa = max(alfa, melhor_valor)`. Se `alfa >= beta`, executa-se `break` (corte beta: $P_2$ no nível acima já possui uma alternativa que restringe o saldo a $\beta$, logo nunca permitirá que o jogo chegue a este ramo).
* **No nó `MIN` (profundidade ímpar):** Após cada filho retornar `val`, atualiza-se `beta = min(beta, melhor_valor)`. Se `alfa >= beta`, executa-se `break` (corte alfa: $P_1$ no nível acima já possui uma alternativa que garante $\alpha$, logo nunca escolherá este ramo).
* **Relaxamento de janela na raiz (prevenção de falsos empates):** Na raiz, é necessário coletar todos os lances que empatam legitimamente com o valor ótimo $V^*$ para a cascata de desempate. Caso a raiz passasse o limite exato (`alfa = melhor_valor` ou `beta = melhor_valor`), um filho que encontrasse uma resposta igual a `melhor_valor` acionaria `alfa >= beta` e interromperia a busca antes de testar respostas piores, gerando um falso empate. Para evitar isso, a chamada dos filhos diretos da raiz relaxa o limite em um `eps` (ex.: `1e-9`):
* Quando somos $P_1$ (raiz `MAX`): passa `alfa = melhor_valor - eps` e `beta = +inf`.
* Quando somos $P_2$ (raiz `MIN`): passa `alfa = -inf` e `beta = melhor_valor + eps`.
Dessa forma, o nível abaixo só poda se encontrar uma resposta **estritamente pior** que `melhor_valor`, assegurando que todo empate coletado na raiz seja real.
* **Retorno *Fail-Soft*:** A função sempre retorna `melhor_valor` (e não `alfa` ou `beta`), preservando cotas mais apertadas na Tabela de Transposição para consultas futuras.

## 6. Avaliação Terminal nas Folhas ($\vert{}P_1\vert{} = 3$ e $\vert{}P_2\vert{} = 3$)

### 6.1. Cálculo exato da utilidade $U(P_1, P_2) = S_{P_1} - S_{P_2}$

* Quando a recursão atinge `profundidade == 0`, ambos os jogadores posicionaram exatamente $3$ centros ($\vert{}P_1\vert{} = 3$ e $\vert{}P_2\vert{} = 3$).
* Para cada vértice $v \in \{0, \dots, n-1\}$ do grafo, calcula-se a menor distância até os centros de $P_1$ e até os centros de $P_2$ consultando diretamente a matriz pré-computada $D$:

$$d_{P_1}(v) = \min_{a \in P_1} D[a][v] \qquad \text{e} \qquad d_{P_2}(v) = \min_{b \in P_2} D[b][v]$$

* A utilidade terminal é definida como o saldo líquido de pontos na perspectiva fixa de $P_1$ contra $P_2$:

$$U(P_1, P_2) = S_{P_1} - S_{P_2}$$

* Se $d_{P_1}(v) < d_{P_2}(v)$, o vértice pertence a $P_1$, somando $+W[v]$ ao saldo.
* Se $d_{P_2}(v) < d_{P_1}(v)$, o vértice pertence a $P_2$, subtraindo $-W[v]$ do saldo.
* Valores positivos indicam vantagem de $P_1$, $0$ indica empate exato e valores negativos indicam vantagem de $P_2$.

### 6.2. Tratamento de empates de distância ($+0,5 \cdot W[v]$)

* Pela regra do jogo, quando $d_{P_1}(v) = d_{P_2}(v)$, o peso $W[v]$ é dividido igualmente entre as duas equipes ($+0,5 \cdot W[v]$ para $S_{P_1}$ e $+0,5 \cdot W[v]$ para $S_{P_2}$).
* Como a função de utilidade avalia a diferença $S_{P_1} - S_{P_2}$, o termo de empate se anula matematicamente no saldo líquido:

$$(+0,5 \cdot W[v]) - (+0,5 \cdot W[v]) = 0$$

* Na implementação, isso significa que vértices empatados simplesmente não alteram o acumulador `saldo`, eliminando a necessidade de um ramo `else` e evitando operações desnecessárias de ponto flutuante dentro das folhas.

### 6.3. Otimização do laço interno de avaliação em Python

* Como a função terminal é o trecho mais executado de toda a estratégia (potencialmente milhões de vezes em $n = 40$), o laço interno deve evitar qualquer sobrecarga de criação de objetos, chamadas de função ou buscas em dicionários:
1. **Extração direta das linhas da matriz $D$:** Antes do laço sobre os $n$ vértices, extraem-se os $3$ índices inteiros de `mask_P1` (`a1, a2, a3`) e os $3$ índices de `mask_P2` (`b1, b2, b3`), obtendo referências locais diretas para suas respectivas linhas em $D$: `da1, da2, da3 = D[a1], D[a2], D[a3]` e `db1, db2, db3 = D[b1], D[b2], D[b3]`.
2. **Eliminação de `min()` e listas temporárias:** Em Python puro, chamadas repetidas a `min(...)` dentro de um laço apertado são significativamente mais lentas do que comparações ternárias diretas. Para cada `v` em `range(n)`:
* Calcula-se `d1 = da1[v]; if da2[v] < d1: d1 = da2[v]; if da3[v] < d1: d1 = da3[v]` (e analogamente para `d2`).
* Atualiza-se `if d1 < d2: saldo += W[v]` / `elif d2 < d1: saldo -= W[v]`.
3. **Acesso local:** Manter `W` e as linhas de `D` como variáveis locais da função reduz o tempo de resolução de nomes (*bytecode* `LOAD_FAST` em vez de `LOAD_GLOBAL`), acelerando a avaliação de cada folha para poucos microssegundos.

## 7. Decisão na Raiz e Cascata de Desempate Determinística

### 7.1. Coleta dos lances ótimos de mesmo valor garantido ($V^*$)

* Na raiz da busca, o algoritmo percorre todos os vértices livres seguindo `ordem_nos`, mantendo o melhor valor garantido encontrado até o momento (`melhor_valor`) e uma lista `candidatos_otimos` com todos os índices que atingem esse mesmo valor $V^*$.
* **Orientação por paridade e relaxamento de janela (`eps`):**
* **Se `profundidade` é par ($P_1$ — raiz `MAX`):** inicializa `melhor_valor = -inf`. Para cada vértice livre `i`, chama `minimax(mask_P1 | (1 << i), mask_P2, profundidade - 1, melhor_valor - eps, +inf)` (com `eps = 1e-9`). Se `val > melhor_valor + eps`, atualiza `melhor_valor = val` e reinicia `candidatos_otimos = [i]`; se `abs(val - melhor_valor) <= eps`, adiciona `i` a `candidatos_otimos`.
* **Se `profundidade` é ímpar ($P_2$ — raiz `MIN`):** inicializa `melhor_valor = +inf`. Para cada vértice livre `i`, chama `minimax(mask_P1, mask_P2 | (1 << i), profundidade - 1, -inf, melhor_valor + eps)`. Se `val < melhor_valor - eps`, atualiza `melhor_valor = val` e reinicia `candidatos_otimos = [i]`; se `abs(val - melhor_valor) <= eps`, adiciona `i` a `candidatos_otimos`.
* O relaxamento por `eps` garante que o nível imediatamente abaixo só sofra poda se encontrar uma resposta **estritamente pior** que `melhor_valor`, eliminando falsos empates na raiz.
* **Saída imediata:** Se ao final do laço `len(candidatos_otimos) == 1`, o único lance ótimo é selecionado diretamente, sem custo adicional de desempate. Caso haja dois ou mais lances empatados em $V^*$, eles avançam pela cascata abaixo.

### 7.2. Critério 1: Resiliência (Margem Média contra respostas do oponente)

* **Objetivo:** Entre lances que garantem exatamente o mesmo piso $V^*$ contra um oponente perfeito, priorizar aquele que obtém a melhor pontuação média caso o adversário cometa erros (jogadas subótimas), maximizando o saldo acumulado no torneio.
* **Condição de aplicação:** Executado apenas quando `profundidade > 1` (na rodada 6, com `profundidade == 1`, não há mais resposta do adversário, portanto pula-se direto para o Critério 2).
* **Cálculo sem comprometer a busca principal:** Para cada candidato `c` presente em `candidatos_otimos`, simula-se todas as respostas livres possíveis `r` do adversário no próximo nível, obtendo o valor exato de cada subjogo `(c, r)` via `minimax` com janela aberta `(-inf, +inf)` (reaproveitando massivamente os estados já resolvidos na Tabela de Transposição `memo`) e calcula-se a média aritmética desses valores.
* **Direção do desempate conforme o papel:**
* Se `profundidade` é **par ($P_1$)**: mantém apenas os candidatos com a **maior** média (mais positiva).
* Se `profundidade` é **ímpar ($P_2$)**: mantém apenas os candidatos com a **menor** média (mais negativa, equivalente à maior vantagem líquida para $P_2$).

### 7.3. Critério 2: Centralidade de Proximidade Ponderada ($C_w$)

* Se mais de um candidato permanecer empatado após o Critério 1, seleciona-se o vértice $u$ com o **maior** valor pré-computado de Centralidade de Proximidade Ponderada:

$$C_w(u) = \sum_{v \in V} \frac{W[v]}{D[u][v] + 1}$$

* Como $C_w(u)$ mede o alcance territorial ponderado do vértice no grafo, a busca pelo **maior** valor aplica-se igualmente tanto para $P_1$ quanto para $P_2$, com consulta em $O(1)$ no vetor já armazenado em cache.

### 7.4. Critério 3: Máxima Distância Interna (Anti-Canibalização)

* Persistindo o empate e caso a nossa equipe já possua ao menos um centro alocado no tabuleiro (`mask_propria != 0`, onde `mask_propria` é `mask_P1` se somos $P_1$, ou `mask_P2` se somos $P_2$), prioriza-se o candidato $u$ que **maximiza a distância mínima até os nossos próprios centros já posicionados**:

$$\max_{u} \min_{a \in \text{meus\_centros}} D[u][a]$$

* Esse critério evita sobreposição territorial (canibalização de vértices que já estão próximos de um centro próprio), incentivando melhor cobertura espacial do grafo.

### 7.5. Critério 4: Ordem Lexicográfica / Menor Índice

* Caso todos os critérios anteriores resultem em empate exato (cenário típico em grafos altamente simétricos e regulares, como anéis ou grades uniformes), seleciona-se o candidato com o **menor índice inteiro** (ou menor rótulo original em ordem lexicográfica).
* Isso assegura que a estratégia seja **100% determinística** e reproduzível em qualquer execução.

## 8. Conversão do índice escolhido de volta ao rótulo original em `grafo.nodes`

* Ao final da busca na raiz (e eventual passagem pela cascata de desempate), o algoritmo obtém um único índice inteiro `idx_escolhido` no intervalo `0..n-1`.
* Antes de encerrar a execução, desfaz-se o mapeamento interno usando a tabela pré-computada `idx_para_rotulo[idx_escolhido]`, garantindo que o valor retornado corresponda **exatamente** ao rótulo original presente em `grafo.nodes` (seja string, inteiro ou qualquer outro identificador imutável).
* Como salvaguarda final, o vértice retornado é garantidamente um nó existente no grafo e com `time == 0`, evitando qualquer erro de validação na engine durante a partida.