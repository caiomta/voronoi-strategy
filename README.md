# Jogo de Voronoi — Estratégia CLEMENTE-V (Minimax com Poda Alfa-Beta)

Implementação em Python da estratégia **CLEMENTE-V** para o Jogo de Voronoi em Grafos, baseada em busca exata via **Minimax com Poda Alfa-Beta *fail-soft***, **Tabela de Transposição com *bitmasks***, **pré-computação estática em cache** e uma **cascata determinística de desempate** em quatro níveis.

---

## Visão Geral do Jogo

* Uma partida possui **6 rodadas alternadas** com **3 centros por equipe** (6 centros ao todo no tabuleiro).
* Cada vértice $v$ do grafo (`networkx.Graph`) possui os atributos `"peso"` e `"time"`, onde `"time"` representa:
  * `0`: vértice livre;
  * `1`: centro pertencente à equipe da vez;
  * `2`: centro pertencente à equipe adversária.
* A distância entre dois vértices é o menor caminho em número de arestas no grafo.
* Ao final das 6 rodadas, cada vértice $v$ tem seu peso atribuído à equipe cujo centro estiver mais próximo; em caso de empate de distância entre as duas equipes, o peso é dividido igualmente ($+0{,}5 \cdot W[v]$ para cada lado).

---

## Interface, Requisitos e Execução

### Ponto de Entrada

A função principal da estratégia é [`estrategia_clemente_v(grafo: nx.Graph)`](estrategia.py) em [estrategia.py](estrategia.py):

* Recebe o objeto `grafo` (`networkx.Graph`) na perspectiva normalizada da equipe da vez (`time == 1` próprio, `time == 2` adversário).
* Atualiza/valida o cache estático global e retorna o **rótulo original** do vértice escolhido em `grafo.nodes`.

### Validações de Segurança (`ValueError`)

A função `estrategia_clemente_v` valida explicitamente tanto o estado recebido quanto o lance escolhido:

* **Entrada:** exige `n >= 6` (mínimo de vértices para 6 centros) e `1 <= profundidade <= 6`.
* **Saída:** garante `0 <= idx_escolhido < n`, existência do `rotulo_escolhido` em `grafo` e disponibilidade do vértice (`grafo.nodes[rotulo_escolhido]["time"] == 0`).

### Requisitos e Instalação

* **Python 3.10+** (utiliza `int.bit_count()` e anotações de união `| None`).
* **Dependência externa única:** `networkx` (especificado em [requirements.txt](requirements.txt) como `networkx==3.7`), além da biblioteca padrão do Python.

```bash
pip install -r requirements.txt
```

Exemplo mínimo de chamada:

```python
from estrategia import estrategia_clemente_v

rotulo_escolhido = estrategia_clemente_v(grafo)
```

---

## Arquitetura e Fluxo do Algoritmo

### 1. Pré-computação e Cache Estático Global (`CACHE` e `atualizar_cache`)

Como o módulo permanece carregado em memória entre as rodadas de uma partida e entre as duas partidas de um confronto no mesmo mapa, os dados estruturais do grafo são armazenados no objeto global `CACHE` (instância da classe `Cache`) e a memoização da busca no dicionário global `MEMO`:

* **Assinatura estrutural (`gerar_assinatura` e `gerar_rotulo_de_comparacao`):** gera uma tupla imutável `(nos_e_pesos, arestas)` com nós ordenados e arestas não direcionadas normalizadas, ignorando o atributo `"time"`. A função `gerar_rotulo_de_comparacao(x)` retorna `(type(x).__name__, str(x))`, garantindo ordenação determinística mesmo em grafos com rótulos de tipos heterogêneos.
* **Reuso e invalidação:** ao iniciar `atualizar_cache(grafo)`, se `CACHE.assinatura == assinatura_atual`, nenhum recálculo é feito ($O(1)$) e `MEMO` é preservado. Se o mapa mudar, `MEMO.clear()` é executado e `CACHE.update(...)` reconstrói as estruturas.
* **Mapeamento bijetivo e pesos:** `gerar_idx_para_rotulo` e `gerar_rotulo_para_idx` convertem rótulos arbitrários para índices inteiros contínuos `0..n-1`; `gerar_tupla_de_pesos` extrai a tupla imutável de pesos na mesma indexação.
* **Matriz de distâncias mínimas (`gerar_matriz_de_distancias`):** executa `nx.all_pairs_shortest_path_length(grafo)` uma única vez por mapa, gerando uma matriz imutável $n \times n$ (tupla de tuplas de inteiros) usando a sentinela `inalcancavel = n + 1` para pares sem caminho.
* **Centralidade de Proximidade Ponderada — CPP (`calcular_cpp` e `gerar_tupla_de_cpp`):** pré-calcula para cada vértice $u$:

$$C_w(u) = \sum_{v \in V} \frac{W[v]}{D[u][v] + 1}$$

* **Ordenação estática de candidatos (`gerar_ordem_nos`):** ordena `0..n-1` em ordem decrescente de `cpp[u]` (preservando o menor `idx` em empates devido à estabilidade do `sorted`), acelerando os cortes Alfa-Beta sem reordenar listas dentro da recursão.

---

### 2. Representação Canônica por *Bitmasks* e Paridade (`extrair_bitmasks`)

Como a ordem em que os centros são escolhidos não altera as distâncias finais, os conjuntos de centros são codificados como inteiros (*bitmasks*), onde o bit `1 << idx` indica que o vértice de índice `idx` pertence ao conjunto:

* `extrair_bitmasks(grafo, idx_para_rotulo)` retorna `(mask_t1, mask_t2)` correspondentes aos vértices com `time == 1` e `time == 2`.
* A profundidade restante é calculada automaticamente por:

$$\text{profundidade} = 6 - \text{qtd\_centros\_escolhidos}$$

onde `qtd_centros_escolhidos = (mask_p1 | mask_p2).bit_count()`.
* **Sistema de coordenadas fixo ($P_1$ vs. $P_2$):** $P_1$ é sempre quem inicia a partida (nó **MAX**, `profundidade` par: $6, 4, 2$) e $P_2$ é sempre o segundo jogador (nó **MIN**, `profundidade` ímpar: $5, 3, 1$). Quando `profundidade % 2` é ímpar, `estrategia_clemente_v` inverte `mask_p1, mask_p2 = mask_p2, mask_p1` para manter a perspectiva global fixa durante toda a busca e entre as duas partidas do confronto.

---

### 3. Motor de Busca (`minimax`) e Tabela de Transposição (`MEMO`)

A função recursiva `minimax(mask_p1, mask_p2, profundidade, alfa, beta) -> float` calcula a utilidade garantida na perspectiva global fixa $U(P_1, P_2) = S_{P_1} - S_{P_2}$:

* **Paridade automática:** `eh_min = bool(profundidade % 2)` define o turno sem parâmetro booleano adicional — nós de $P_1$ (profundidade par) maximizam e atualizam `alfa`, enquanto nós de $P_2$ (profundidade ímpar) minimizam e atualizam `beta`.
* **Expansão:** percorre `CACHE.ordem_nos`, ignorando vértices ocupados via `mask_jogo & mask_no_atual` (`mask_jogo = mask_p1 | mask_p2`), e interrompe o laço quando `alfa >= beta` (corte Alfa-Beta).
* **Tabela de Transposição (`MEMO`):** armazena apenas estados intermediários (`profundidade >= 1`) com chave canônica `(mask_p1, mask_p2)` e valor `(melhor_valor, flag)`:
  * `"EXATO"`: valor real dentro da janela `(alfa_orig, beta_orig)`.
  * `"INFERIOR"`: *fail-high* (`melhor_valor >= beta_orig`), ajusta `alfa = max(alfa, valor_salvo)`.
  * `"SUPERIOR"`: *fail-low* (`melhor_valor <= alfa_orig`), ajusta `beta = min(beta, valor_salvo)`.
  * Caso o ajuste feche a janela (`alfa >= beta`), retorna `valor_salvo` imediatamente.
* **Retorno *fail-soft*:** retorna sempre `melhor_valor` (e não `alfa` ou `beta`), permitindo reaproveitamento direto e sem inversão de sinal entre a Partida 1 ($P_1$) e a Partida 2 ($P_2$).

---

### 4. Avaliação Terminal Otimizada (`avaliar_folha` e `extrair_tres_centros`)

Quando `profundidade == 0`, ambos os jogadores já possuem exatamente 3 centros:

* `extrair_tres_centros` isola os 3 índices de cada *bitmask* em $O(1)$ usando `bitmask & -bitmask` e `bit_length() - 1`.
* `avaliar_folha` acessa diretamente as 6 linhas correspondentes em `CACHE.matriz_distancias` e compara as distâncias sem chamadas a `min()` ou alocação de listas no laço sobre `range(n)`.
* Se `d1 < d2`, soma `pesos[v]` ao `saldo`; se `d2 < d1`, subtrai `pesos[v]`; quando `d1 == d2` (incluindo empate em vértices inalcançáveis com sentinela `n + 1`), os termos $+0{,}5 \cdot W[v]$ e $-0{,}5 \cdot W[v]$ se anulam matematicamente e nenhuma operação é feita.

---

### 5. Decisão na Raiz e Cascata Determinística de Desempate (`decidir_jogada`)

Na raiz, `decidir_jogada(mask_p1, mask_p2, profundidade) -> int` coleta todos os lances livres que atingem o valor ótimo $V^*$ e resolve eventuais empates em sequência:

1. **Coleta de candidatos ótimos com relaxamento (`EPS = 1e-9`):**
   * Percorre `CACHE.ordem_nos` chamando `minimax` com janela relaxada por `EPS` (`(-inf, melhor_valor + EPS)` para $P_2$; `(melhor_valor - EPS, +inf)` para $P_1$) para impedir que a poda no nível seguinte gere falsos empates.
   * Compara usando tolerância estrita `abs(valor - melhor_valor) < EPS` para agrupar empates (evitando colisão de fronteira com o corte inclusivo `alfa >= beta`), e atualiza `melhor_valor` quando encontra valor estritamente melhor.
   * Se `len(candidatos_otimos) == 1`, retorna imediatamente.

2. **Critério 1 — Melhor Média de Resposta / Resiliência (`liberar_c1`, `GUARDA_C1`, `filtrar_candidatos_por_melhor_media_de_resposta`):**
   * A guarda `liberar_c1(profundidade, len_candidatos_otimos, n)` retorna `False` se `profundidade <= 1`, `True` se `n <= 15`, verifica `len_candidatos_otimos <= GUARDA_C1[profundidade]` quando `profundidade in GUARDA_C1` (`{5: 6, 6: 2}`), e retorna `True` nos demais casos (`1 < profundidade <= 4`).
   * Quando liberado, para cada candidato `c`, avalia todas as `total_respostas = n - 7 + profundidade` respostas livres `r` do oponente via `minimax(..., profundidade - 2, -inf, +inf)` (reaproveitando `MEMO`) e mantém os candidatos a menos de `EPS` da **maior** média ($P_1$) ou da **menor** média ($P_2$).

3. **Critério 2 — Maior CPP (`filtrar_candidatos_por_maior_cpp`):**
   * Mantém os candidatos cujo `CACHE.cpp[c]` está a menos de `EPS` do máximo entre os empatados (tanto para $P_1$ quanto para $P_2$).

4. **Critério 3 — Máxima Distância Mínima dos Centros / Anti-Canibalização (`filtrar_candidatos_por_maxima_distancia_minima_dos_centros` e `extrair_centros`):**
   * Define `mask_propria = mask_p2 if eh_min else mask_p1`. Se `mask_propria == 0`, retorna os candidatos inalterados; caso contrário, extrai os centros próprios já posicionados e mantém os candidatos que maximizam:

$$\max_{u} \min_{a \in \text{meus\_centros}} D[u][a]$$

5. **Critério 4 — Menor `idx`:**
   * Persistindo o empate, retorna `min(candidatos_otimos)`, assegurando determinismo total.

---

## Visão Geral das Funções em `estrategia.py`

| Símbolo | Responsabilidade |
| :--- | :--- |
| `Cache` / `CACHE` | Armazena os dados estáticos pré-computados do mapa atual. |
| `MEMO` | Tabela de transposição `(mask_p1, mask_p2) -> (valor, flag)`. |
| `estrategia_clemente_v` | Ponto de entrada: validações, cache, paridade $P_1$/$P_2$ e retorno do rótulo. |
| `atualizar_cache` | Verifica assinatura estrutural, limpa `MEMO` se necessário e atualiza `CACHE`. |
| `gerar_assinatura` / `gerar_rotulo_de_comparacao` | Assinatura canônica do grafo (sem `"time"`) com ordenação segura entre tipos. |
| `gerar_idx_para_rotulo` / `gerar_rotulo_para_idx` | Bijeção entre rótulos originais e índices `0..n-1`. |
| `gerar_tupla_de_pesos` / `gerar_matriz_de_distancias` | Tupla de pesos e matriz $n \times n$ de menores caminhos (`inalcancavel = n + 1`). |
| `calcular_cpp` / `gerar_tupla_de_cpp` / `gerar_ordem_nos` | Cálculo da CPP e ordenação decrescente dos vértices. |
| `extrair_bitmasks` / `extrair_centros` / `extrair_tres_centros` | Conversão entre atributos `"time"` / *bitmasks* e índices inteiros. |
| `avaliar_folha` | Avaliação terminal exata $S_{P_1} - S_{P_2}$ em nós folha (`profundidade == 0`). |
| `minimax` | Motor recursivo Minimax com poda Alfa-Beta *fail-soft* e `MEMO`. |
| `decidir_jogada` | Coleta de ótimos na raiz e orquestração da cascata de desempate. |
| `liberar_c1` / `filtrar_candidatos_por_melhor_media_de_resposta` | Guarda de custo e Critério 1 (resiliência / margem média). |
| `filtrar_candidatos_por_maior_cpp` | Critério 2 (maior CPP). |
| `filtrar_candidatos_por_maxima_distancia_minima_dos_centros` | Critério 3 (anti-canibalização). |

---

## Estrutura do Repositório

* [estrategia.py](estrategia.py) — Implementação completa da estratégia **CLEMENTE-V**.
* [docs/estrategia.md](docs/estrategia.md) — Especificação conceitual e detalhamento teórico do algoritmo.
* [requirements.txt](requirements.txt) — Dependência (`networkx==3.7`).
* [ruff.toml](ruff.toml) — Configuração de formatação e lint (`ruff`, `target-version = "py315"`).

---

## Autores

* Caio Tenório
* Lucas de Oliveira
* Matheus do Carmo
* Natália Bourbon
* Thiago Ramalho
* Vinicius da Fonseca
