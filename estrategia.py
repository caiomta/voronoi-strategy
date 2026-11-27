import networkx as nx

EPS = 1e-9
GUARDA_C1 = {5: 6, 6: 2}


class Cache:
    """Armazena os dados estáticos pré-computados do grafo atual do jogo para evitar recálculos
    entre rodadas e partidas disputadas no mesmo mapa.

    Attributes:
        assinatura: Assinatura estrutural imutável do grafo (nós com pesos e arestas ordenadas),
            ou `None` caso o cache ainda não tenha sido inicializado.
        n: Quantidade total de nós do grafo.
        idx_para_rotulo: Tupla ordenada dos rótulos dos nós, onde o índice é o `idx` do nó.
        rotulo_para_idx: Dicionário que mapeia cada rótulo de nó ao seu respectivo `idx`.
        pesos: Tupla dos pesos dos nós, indexada pelo `idx` do respectivo nó.
        matriz_distancias: Matriz das distâncias mínimas entre todos os pares de `idx`.
        cpp: Tupla da Centralidade de Proximidade Ponderada (CPP) de cada nó, indexada por `idx`.
        ordem_nos: Tupla dos `idx` ordenada decrescentemente pela CPP de cada nó.
    """

    assinatura: tuple[tuple, tuple] | None = None
    n: int
    idx_para_rotulo: tuple
    rotulo_para_idx: dict
    pesos: tuple[float, ...]
    matriz_distancias: tuple[tuple[int, ...], ...]
    cpp: tuple[float, ...]
    ordem_nos: tuple[int, ...]

    def update(
        self,
        assinatura: tuple[tuple, tuple],
        n: int,
        idx_para_rotulo: tuple,
        rotulo_para_idx: dict,
        pesos: tuple[float, ...],
        matriz_distancias: tuple[tuple[int, ...], ...],
        cpp: tuple[float, ...],
        ordem_nos: tuple[int, ...],
    ) -> None:
        """
        Atualiza todos os atributos do cache com os dados pré-computados de um novo grafo.

        Args:
            assinatura: Assinatura estrutural imutável do novo grafo.
            n: Quantidade total de nós do grafo.
            idx_para_rotulo: Tupla ordenada dos rótulos dos nós, onde o índice é o `idx` do nó.
            rotulo_para_idx: Dicionário que mapeia cada rótulo de nó ao seu respectivo `idx`.
            pesos: Tupla dos pesos dos nós, indexada pelo `idx` do respectivo nó.
            matriz_distancias: Matriz das distâncias mínimas entre todos os pares de `idx`.
            cpp: Tupla da Centralidade de Proximidade Ponderada (CPP) de cada nó, indexada por `idx`.
            ordem_nos: Tupla dos `idx` ordenada decrescentemente pela CPP de cada nó.
        """
        self.assinatura = assinatura
        self.n = n
        self.idx_para_rotulo = idx_para_rotulo
        self.rotulo_para_idx = rotulo_para_idx
        self.pesos = pesos
        self.matriz_distancias = matriz_distancias
        self.cpp = cpp
        self.ordem_nos = ordem_nos


# Cache e memoização de estados intermediários
CACHE = Cache()
MEMO: dict[tuple[int, int], tuple[float, str]] = {}
"""
Estrutura:
* chaves: dupla do bitmask do P_1 e do P_2
* valores: dupla do melhor valor e a flag da poda (`EXATO`, `SUPERIOR`, `INFERIOR`)
"""


def minimax_com_poda_alfa_beta(grafo: nx.Graph): ...


def atualizar_cache(grafo: nx.Graph) -> None:
    """
    Valida o cache e o atualiza caso o grafo tenha mudado.

    Args:
        grafo: Grafo atual do jogo.
    """
    assinatura_atual = gerar_assinatura(grafo)

    if CACHE.assinatura == assinatura_atual:  # cache válido
        return

    MEMO.clear()

    idx_para_rotulo = gerar_idx_para_rotulo(grafo)
    n = len(idx_para_rotulo)
    rotulo_para_idx = gerar_rotulo_para_idx(idx_para_rotulo, n)
    pesos = gerar_tupla_de_pesos(grafo, idx_para_rotulo, n)
    matriz_distancias = gerar_matriz_de_distancias(grafo, rotulo_para_idx, n)
    cpp = gerar_tupla_de_cpp(pesos, matriz_distancias, n)
    ordem_nos = gerar_ordem_nos(cpp, n)

    CACHE.update(
        assinatura_atual,
        n,
        idx_para_rotulo,
        rotulo_para_idx,
        pesos,
        matriz_distancias,
        cpp,
        ordem_nos,
    )


def gerar_assinatura(grafo: nx.Graph) -> tuple[tuple, tuple]:
    """
    Gera a assinatura do grafo (sem times), uma tupla contendo uma tupla ordenada com nós e pesos e
    outra tupla ordenada com as arestas ordenadas, usada como assinatura única do grafo do jogo.

    Args:
        grafo: Grafo atual do jogo.

    Returns:
        Dupla da tupla ordenada de nós e pesos e da tupla ordenada de arestas.
    """
    nos_e_pesos = tuple(
        sorted(
            ((no, grafo.nodes[no]["peso"]) for no in grafo),
            key=lambda x: gerar_rotulo_de_comparacao(x[0]),
        )
    )
    arestas = tuple(
        sorted(
            (
                (u, v) if gerar_rotulo_de_comparacao(u) < gerar_rotulo_de_comparacao(v) else (v, u)
                for u, v in grafo.edges()
            ),
            key=lambda x: (gerar_rotulo_de_comparacao(x[0]), gerar_rotulo_de_comparacao(x[1])),
        )
    )
    return (nos_e_pesos, arestas)


def gerar_rotulo_de_comparacao(x) -> tuple[str, str]:
    """
    Gera um rótulo para realizar comparação entre objetos de tipos distintos.

    Args:
        x: Objeto a ser comparado.

    Returns:
        Dupla do nome do tipo de `x` e o valor em `str` de `x`.
    """
    return (type(x).__name__, str(x))


def gerar_idx_para_rotulo(grafo: nx.Graph) -> tuple:
    """
    Gera uma tupla que funciona como uma bijeção do tipo `idx -> rótulo`, sendo `idx` do nó o
    índice do rótulo na tupla.

    Args:
        grafo: Grafo atual do jogo.

    Returns:
        Tupla ordenada dos rótulos dos nós, onde o índice de um rótulo é o `idx` daquele nó.
    """
    return tuple(sorted(grafo.nodes, key=gerar_rotulo_de_comparacao))


def gerar_rotulo_para_idx(idx_para_rotulo: tuple, n: int) -> dict:
    """
    Gera um dicionário que espelha o vetor `idx_para_rotulo`.

    Args:
        idx_para_rotulo: Tupla ordenada dos rótulos dos nós, onde o índice de um rótulo é o `idx`
            daquele nó.
        n: Quantidade total de nós.

    Returns:
        Dicionário em que a chave é um rótulo de um nó e o valor é seu `idx`.
    """
    return {idx_para_rotulo[i]: i for i in range(n)}


def gerar_tupla_de_pesos(grafo: nx.Graph, idx_para_rotulo: tuple, n: int) -> tuple[float, ...]:
    """
    Gera uma tupla que funciona como um mapeamento do `idx` do nó para seu peso.

    Args:
        grafo: Grafo atual do jogo.
        idx_para_rotulo: Tupla ordenada dos rótulos dos nós, onde o índice de um rótulo é o `idx`
            daquele nó.
        n: Quantidade total de nós.

    Returns:
        Tupla dos pesos dos nós, onde o índice de um peso é o `idx` do respectivo nó.
    """
    return tuple(grafo.nodes[idx_para_rotulo[i]]["peso"] for i in range(n))


def gerar_matriz_de_distancias(
    grafo: nx.Graph,
    rotulo_para_idx: dict,
    n: int,
) -> tuple[tuple[int, ...], ...]:
    """
    Gera uma matriz das distâncias mínimas entre todos os pares de nós.

    Args:
        grafo: Grafo atual do jogo.
        rotulo_para_idx: Dicionário em que a chave é um rótulo de um nó e o valor é seu `idx`.
        n: Quantidade total de nós.

    Returns:
        Matriz onde o valor da posição `(u,v)`, sendo esta uma dupla dos `idx` de dois nós
        quaisquer, é o tamanho do menor caminho entre esses nós.
    """
    inalcancavel = n + 1
    matriz = [[inalcancavel for _ in range(n)] for _ in range(n)]

    distancias_raw = nx.all_pairs_shortest_path_length(grafo)

    for origem, distancias in distancias_raw:
        u = rotulo_para_idx[origem]
        for destino, distancia in distancias.items():
            v = rotulo_para_idx[destino]
            matriz[u][v] = distancia

    return tuple(tuple(linha) for linha in matriz)


def calcular_cpp(
    u: int,
    pesos: tuple[float, ...],
    matriz_distancias: tuple[tuple[int, ...], ...],
    n: int,
) -> float:
    """
    Calcula a Centralidade de Proximidade Ponderada (CPP) do nó `u`, que mede seu alcance
    territorial ponderado sobre todo o grafo, indicando o quão bem posicionado `u` está em relação
    a regiões de pesos altos.

    Args:
        u: `idx` do nó a calcular a centralidade de proximidade ponderada.
        pesos: Tupla de pesos.
        matriz_distancias: Matriz das distâncias mínimas entre todos os pares de nós.
        n: Quantidade total de nós.

    Returns:
        CPP do nó `u`.
    """
    return sum(pesos[v] / (matriz_distancias[u][v] + 1) for v in range(n))


def gerar_tupla_de_cpp(
    pesos: tuple[float, ...],
    matriz_distancias: tuple[tuple[int, ...], ...],
    n: int,
) -> tuple[float, ...]:
    """
    Gera uma tupla da imagem da função que calcula a CPP que conta com domínio os `idx` do grafo.

    Args:
        pesos: Tupla de pesos.
        matriz_distancias: Matriz das distâncias mínimas entre todos os pares de nós.
        n: Quantidade total de nós.

    Returns:
        Tupla das CPP, onde o índice é o `idx` do respectivo nó.
    """
    return tuple(calcular_cpp(u, pesos, matriz_distancias, n) for u in range(n))


def gerar_ordem_nos(cpp: tuple[float, ...], n: int) -> tuple[int, ...]:
    """
    Gera uma tupla dos `idx` ordenada decrescentemente pelo CPP do respectivo nó, a fim de decidir
    a ordem de checagem dos nós (aqueles com maior CPP são mais estratégicos na pontuação, pois
    compreendem uma área ponderada maior).

    Args:
        cpp: Tupla das CPP, onde o índice é o `idx` do respectivo nó.
        n: Quantidade total de nós.

    Returns:
        Tupla dos `idx` ordenada decrescentemente pelo CPP do respectivo nó.
    """
    return tuple(
        sorted(
            range(n),
            key=lambda u: cpp[u],
            reverse=True,
        )
    )


def avaliar_folha(mask_p1: int, mask_p2: int) -> float:
    """
    Avalia uma folha da árvore de estados do jogo por meio dos bitmasks de P1 e P2 e retorna a
    diferença entre as pontuações deles. Uma diferença maior é vantajosa para P1, o contrário,
    para P2. Esta função só deve ser utilizada no cenário em que ambos os jogadores já escolheram
    todos os seus centros.

    Args:
        mask_p1: Bitmask dos centros escolhidos por P1.
        mask_p2: Bitmask dos centros escolhidos por P2.

    Returns:
        Diferença entre as pontuações de P1 e P2 no estado atual.
    """
    n, pesos, matriz_distancias = CACHE.n, CACHE.pesos, CACHE.matriz_distancias
    c1_p1, c2_p1, c3_p1 = extrair_tres_centros(mask_p1)  # extrair os 3 indices
    c1_p2, c2_p2, c3_p2 = extrair_tres_centros(mask_p2)
    saldo = 0.0  # acumulador

    linha_p1_1 = matriz_distancias[c1_p1]  # linhas do time 1
    linha_p1_2 = matriz_distancias[c2_p1]
    linha_p1_3 = matriz_distancias[c3_p1]

    linha_p2_1 = matriz_distancias[c1_p2]  # linhas do time 2
    linha_p2_2 = matriz_distancias[c2_p2]
    linha_p2_3 = matriz_distancias[c3_p2]

    for v in range(n):  # procurar a menor distância de d1
        d1 = linha_p1_1[v]
        if linha_p1_2[v] < d1:
            d1 = linha_p1_2[v]
        if linha_p1_3[v] < d1:
            d1 = linha_p1_3[v]

        d2 = linha_p2_1[v]  # procurar a menor distância de d2
        if linha_p2_2[v] < d2:
            d2 = linha_p2_2[v]
        if linha_p2_3[v] < d2:
            d2 = linha_p2_3[v]

        if d1 < d2:  # comparativo entre d1 e d2 para saber a menor distância
            saldo += pesos[v]
        elif d2 < d1:
            saldo -= pesos[v]
        # se d1 == d2 (incluindo empate de distância finita ou ambos inalcançaveis / inf)
        # o peso do vértice se anula na diferença de saldo (0)
    return saldo


def extrair_centros(bitmask: int) -> list[int]:
    """
    Extrai todos os `idx` dos centros escolhidos registrados na bitmask, independentemente da
    quantidade.

    Args:
        bitmask: Bitmask dos centros escolhidos.

    Returns:
        Lista contendo todos os `idx` dos centros escolhidos registrados na bitmask.
    """
    centros = []
    while bitmask:
        lsb = bitmask & -bitmask
        centros.append(lsb.bit_length() - 1)
        bitmask ^= lsb
    return centros


def extrair_tres_centros(bitmask: int) -> tuple[int, int, int]:
    """
    Extrai os três `idx` dos centros escolhidos registrados na bitmask. Esta função só deve ser
    utilizada se os 3 centros tiverem sido escolhidos.

    Args:
        bitmask: Bitmask dos centros escolhidos.

    Returns:
        Tripla contendo os três `idx` dos centros escolhidos registrados na bitmask.
    """
    lsb = bitmask & -bitmask  # apaga todos os outros bits e deixa só o mais a direita aceso
    p1 = lsb.bit_length() - 1  # para descobrir a posicao do bit
    bitmask ^= lsb  # apaga esse bit da bitmask para pegar o próximo
    lsb = bitmask & -bitmask
    p2 = lsb.bit_length() - 1
    bitmask ^= lsb
    lsb = bitmask & -bitmask
    p3 = lsb.bit_length() - 1
    return p1, p2, p3


def minimax(mask_p1: int, mask_p2: int, profundidade: int, alfa: float, beta: float) -> float:
    """
    Recursivamente busca o jogo perfeito (onde ambos os jogadores fazem a melhor jogada) a partir
    do estado atual do grafo. Também registra os valores encontrados nas jogadas intermediárias
    (que não são folhas) em `MEMO`.

    Args:
        mask_p1: Bitmask dos centros já escolhidos por P1, sendo o i-ésimo bit 1 caso ele possuir
                 um centro no i-ésimo nó.
        mask_p2: Bitmask dos centros já escolhidos por P2, sendo o i-ésimo bit 1 caso ele possuir
                 um centro no i-ésimo nó.
        profundidade: Quantidade de centros restantes a se posicionar no jogo.
        alfa: Piso de P1 (que procura MAX em suas jogadas). Maior valor já encontrado nas outras
              opções de jogada já checadas até o momento. P1 só escolhe algo igual ou acima a isso.
        beta: Teto de P2 (que procura MIN em suas jogadas). Menor valor já encontrado nas outras
              opções de jogada já checadas até o momento. P2 só escolhe algo igual ou abaixo disso.

    Returns:
        A utilidade ótima garantida a partir do estado atual, ou uma cota fail-soft caso ocorra
        poda.
    """
    if profundidade == 0:  # avaliar valor da folha (profundidade 0)
        return avaliar_folha(mask_p1, mask_p2)

    alfa_orig, beta_orig = alfa, beta
    chave_memo = (mask_p1, mask_p2)
    valor_salvo, flag = MEMO.get(chave_memo, (None, None))

    if valor_salvo is not None:
        if flag == "EXATO":  # valor real da opção, sem poda
            return valor_salvo

        if flag == "INFERIOR":  # valor beta-podado da opção, o valor real é >=
            # max(valor_salvo, alfa), aumenta o piso da busca
            alfa = valor_salvo if alfa < valor_salvo else alfa
        elif flag == "SUPERIOR":  # valor alfa-podado da opção, o valor real é <=
            # min(valor_salvo, beta), abaixa o teto da busca
            beta = valor_salvo if beta > valor_salvo else beta

        # poda alfa-beta: se alfa alcança ou passa de beta, a janela de busca de um melhor valor
        # [alfa,beta] fecha, o que significa que o valor real está fora dela, pois um dos jogadores
        # já tem uma opção melhor
        if alfa >= beta:
            return valor_salvo

    eh_min = bool(profundidade % 2)  # profundidade ímpar -> MIN, par -> MAX
    melhor_valor = float("+inf") if eh_min else float("-inf")
    mask_jogo = mask_p1 | mask_p2  # bitwise or gerando o bitmask geral do jogo
    ordem_nos = CACHE.ordem_nos

    for i in ordem_nos:
        mask_no_atual = 1 << i

        if mask_jogo & mask_no_atual:  # se o i-ésimo bit estiver ocupado
            continue

        p1_apos_i, p2_apos_i = (
            (mask_p1, mask_p2 | mask_no_atual)  # p2 joga em i se profundidade ímpar
            if eh_min
            else (mask_p1 | mask_no_atual, mask_p2)  # p1 joga em i se profundidade par
        )

        valor = minimax(p1_apos_i, p2_apos_i, profundidade - 1, alfa, beta)

        if eh_min:
            # min(melhor_valor, valor)
            melhor_valor = valor if valor < melhor_valor else melhor_valor
            # se o valor encontrado está abaixo do beta (teto), reduz o teto
            beta = melhor_valor if melhor_valor < beta else beta
        else:
            # max(melhor_valor, valor)
            melhor_valor = valor if valor > melhor_valor else melhor_valor
            # se o valor encontrado está acima do alfa (piso), aumenta o piso
            alfa = melhor_valor if melhor_valor > alfa else alfa

        # poda alfa-beta
        if alfa >= beta:
            break

    if melhor_valor <= alfa_orig:  # poda alfa, valor real da opção <= melhor_valor (fail-low)
        MEMO[chave_memo] = (melhor_valor, "SUPERIOR")
    elif melhor_valor >= beta_orig:  # poda beta, valor real da opção >= melhor_valor (fail-high)
        MEMO[chave_memo] = (melhor_valor, "INFERIOR")
    else:  # sem corte, guarda o valor real da opção
        MEMO[chave_memo] = (melhor_valor, "EXATO")

    return melhor_valor


def decidir_jogada(mask_p1: int, mask_p2: int, profundidade: int) -> int:
    """
    Executa o processo de decisão do centro escolhido na rodada atual do jogo, retornando o nó com
    a valoração mais favorável considerando uma constante de relaxamento `EPS` (para o jogador da
    rodada atual) no retorno da execução do `minimax` com poda, caso ele seja o único com tal
    valoração. Senão, aplica uma série de critérios de desempate, com relaxamento, na tentativa de
    selecionar um único nó, retornando-o se possível. Se não for possível, retorna o candidato com
    o menor `idx`.

    Os critérios são:
    1. Melhor média de resposta;
    2. Maior CPP;
    3. Máxima Distância Mínima dos Centros.

    Args:
        mask_p1: Bitmask do P1.
        mask_p2: Bitmask do P2.
        profundidade: Quantidade de centros restantes a se posicionar no jogo.

    Returns:
        `idx` do centro escolhido.
    """
    n = CACHE.n
    eh_min = bool(profundidade % 2)
    mask_jogo = mask_p1 | mask_p2
    melhor_valor = float("+inf") if eh_min else float("-inf")
    candidatos_otimos = []
    ordem_nos = CACHE.ordem_nos

    for i in ordem_nos:
        mask_i = 1 << i

        if mask_jogo & mask_i:
            continue

        if eh_min:
            valor = minimax(
                mask_p1,
                mask_p2 | mask_i,
                profundidade - 1,
                float("-inf"),
                melhor_valor + EPS,
            )
        else:
            valor = minimax(
                mask_p1 | mask_i,
                mask_p2,
                profundidade - 1,
                melhor_valor - EPS,
                float("+inf"),
            )

        if abs(valor - melhor_valor) <= EPS:
            candidatos_otimos.append(i)
        elif (eh_min and valor < melhor_valor) or (not eh_min and valor > melhor_valor):
            melhor_valor = valor
            candidatos_otimos = [i]

    if len(candidatos_otimos) == 1:
        return candidatos_otimos[0]

    # Critério 1: Melhor Média de Resposta
    if liberar_c1(profundidade, len(candidatos_otimos), n):
        candidatos_otimos = filtrar_candidatos_por_melhor_media_de_resposta(
            candidatos_otimos,
            mask_p1,
            mask_p2,
            mask_jogo,
            profundidade,
            eh_min,
        )

        if len(candidatos_otimos) == 1:
            return candidatos_otimos[0]

    # Critério 2: Maior CPP
    candidatos_otimos = filtrar_candidatos_por_maior_cpp(candidatos_otimos)
    if len(candidatos_otimos) == 1:
        return candidatos_otimos[0]

    # Critério 3: Maior Distância Mínima dos Centros
    mask_propria = mask_p2 if eh_min else mask_p1
    candidatos_otimos = filtrar_candidatos_por_maxima_distancia_minima_dos_centros(
        candidatos_otimos,
        mask_propria,
    )
    if len(candidatos_otimos) == 1:
        return candidatos_otimos[0]

    # Critério 4: Menor `idx`
    return min(candidatos_otimos)


def liberar_c1(profundidade: int, len_candidatos_otimos: int, n: int) -> bool:
    """
    Checa se é possível utilizar o Critério 1 de desempate e se seu custo vale a pena. Caso a
    profundidade seja <= 1, não há resposta possível, não sendo possível usar a média de valoração
    das respostas como desempate. Usar o C1 em profundidade >4 tira muito da performance da poda
    alfa beta devido a diversas checagens em galhos podados da árvore de estados, por isso o C1 é
    aplicado somente quando há pouquíssimos candidatos neste caso, ou quando há <= 15 nós no grafo
    do jogo. O número exato de candidatos máximos aceitos é estabelecido pela constante
    `GUARDA_C1`. Caso haja 1 < profundidade <= 4, não há empecilho algum para o uso do C1.

    Args:
        profundidade: Quantidade de centros restantes a se posicionar no jogo.
        len_candidatos_otimos: Quantidade de candidatos ótimos.
        n: Quantidade total de nós no grafo do jogo.

    Returns:
        `True` se for possível e valer a pena utilizar o Critério 1 de desempate, senão `False`.
    """
    if profundidade <= 1:
        return False
    if n <= 15:
        return True
    if profundidade in GUARDA_C1:
        return len_candidatos_otimos <= GUARDA_C1[profundidade]
    return True


def filtrar_candidatos_por_melhor_media_de_resposta(
    candidatos_otimos: list[int],
    mask_p1: int,
    mask_p2: int,
    mask_jogo: int,
    profundidade: int,
    eh_min: bool,
) -> list[int]:
    """
    Filtra os candidatos ótimos, mantendo apenas aqueles cuja média de valoração de resposta
    se encontra na janela da mais favorável entre os candidatos, relaxada por ±`EPS`.

    Args:
        candidatos_otimos: Lista dos melhores candidatos a centro escolhido.
        mask_p1: Bitmask do P1.
        mask_p2: Bitmask do P2.
        mask_jogo: Bitmask geral do jogo (bitwise or das bitmasks dos dois jogadores).
        profundidade: Quantidade de centros restantes a se posicionar no jogo.
        eh_min: Se o jogador atual busca a menor valoração.

    Returns:
        Lista de candidatos ótimos filtrada.
    """
    ordem_nos, n = CACHE.ordem_nos, CACHE.n
    total_respostas = (
        n - 7 + profundidade
    )  # quantidade de respostas possíveis a qualquer jogada candidata
    melhor_media = float("+inf") if eh_min else float("-inf")
    melhores_candidatos = []

    for c in candidatos_otimos:
        mask_c = 1 << c

        p1_apos_c, p2_apos_c = (
            (mask_p1, mask_p2 | mask_c) if eh_min else (mask_p1 | mask_c, mask_p2)
        )
        prox_mask_jogo = mask_jogo | mask_c

        soma = 0.0
        for r in ordem_nos:
            mask_r = 1 << r

            if prox_mask_jogo & mask_r:
                continue

            p1_apos_r, p2_apos_r = (
                (p1_apos_c | mask_r, p2_apos_c) if eh_min else (p1_apos_c, p2_apos_c | mask_r)
            )

            soma += minimax(p1_apos_r, p2_apos_r, profundidade - 2, float("-inf"), float("+inf"))

        media = soma / total_respostas

        if abs(media - melhor_media) <= EPS:
            melhores_candidatos.append(c)
        elif (eh_min and media < melhor_media) or (not eh_min and media > melhor_media):
            melhor_media = media
            melhores_candidatos = [c]

    return melhores_candidatos


def filtrar_candidatos_por_maior_cpp(candidatos_otimos: list[int]) -> list[int]:
    """
    Filtra os candidatos ótimos, mantendo apenas aqueles cuja CPP se encontra na janela da maior
    entre os candidatos, relaxada por ±`EPS`.

    Args:
        candidatos_otimos: Lista dos melhores candidatos a centro escolhido.

    Returns:
        Lista de candidatos ótimos filtrada.
    """
    cpp = CACHE.cpp
    melhor_cpp = max(cpp[c] for c in candidatos_otimos)
    return [c for c in candidatos_otimos if abs(cpp[c] - melhor_cpp) <= EPS]


def filtrar_candidatos_por_maxima_distancia_minima_dos_centros(
    candidatos_otimos: list[int],
    mask_propria: int,
) -> list[int]:
    """
    Filtra os candidatos ótimos, mantendo apenas aqueles cuja distância até o centro próprio mais
    próximo é a máxima entre os candidatos. Quando `mask_propria == 0`, retorna a lista de
    candidatos inalterada.

    Args:
        candidatos_otimos: Lista dos melhores candidatos a centro escolhido.
        mask_propria: Bitmask do jogador atual.

    Returns:
        Lista de candidatos ótimos filtrada.
    """
    if not mask_propria:
        return candidatos_otimos

    matriz_distancias = CACHE.matriz_distancias
    centros = extrair_centros(mask_propria)
    maxima_distancia_minima_dos_centros = -1
    melhores_candidatos = []

    for candidato in candidatos_otimos:
        distancia_minima_candidato = min(matriz_distancias[candidato][centro] for centro in centros)

        if distancia_minima_candidato > maxima_distancia_minima_dos_centros:
            maxima_distancia_minima_dos_centros = distancia_minima_candidato
            melhores_candidatos = [candidato]
        elif distancia_minima_candidato == maxima_distancia_minima_dos_centros:
            melhores_candidatos.append(candidato)

    return melhores_candidatos
