import networkx as nx


class Cache:
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
        self.assinatura = assinatura
        self.n = n
        self.idx_para_rotulo = idx_para_rotulo
        self.rotulo_para_idx = rotulo_para_idx
        self.pesos = pesos
        self.matriz_distancias = matriz_distancias
        self.cpp = cpp
        self.ordem_nos = ordem_nos


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
    cpp = gerar_tupla_de_cpp(
        pesos,
        matriz_distancias,
        n,
    )
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
    outra tupla ordenada com as arestas ordenadas.

    Args:
        grafo: Grafo atual do jogo.
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
                (u, v)
                if gerar_rotulo_de_comparacao(u) < gerar_rotulo_de_comparacao(v)
                else (v, u)
                for u, v in grafo.edges()
            ),
            key=lambda x: (
                gerar_rotulo_de_comparacao(x[0]),
                gerar_rotulo_de_comparacao(x[1]),
            ),
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
    Gera um dicionário que espelha o vetor `idx_para_rótulo`.

    Args:
        idx_para_rotulo: Tupla ordenada dos rótulos dos nós, onde o índice de um rótulo é o `idx`
            daquele nó.
        n: Quantidade total de nós.

    Returns:
        Dicionário em que a chave é um rótulo de um nó e o valor é seu `idx`.
    """
    return {idx_para_rotulo[i]: i for i in range(n)}


def gerar_tupla_de_pesos(
    grafo: nx.Graph,
    idx_para_rotulo: tuple,
    n: int,
) -> tuple[float, ...]:
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
    matriz = [[0 for _ in range(n)] for _ in range(n)]

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


def gerar_ordem_nos(
    cpp: tuple[float, ...],
    n: int,
) -> tuple[int, ...]:
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
    saldo = 0  # acumulador

    linha_p1_1 = matriz_distancias[c1_p1]  # linhas do time 1
    linha_p1_2 = matriz_distancias[c2_p1]
    linha_p1_3 = matriz_distancias[c3_p1]

    linha_p2_1 = matriz_distancias[c1_p2]  # linhas do time 2
    linha_p2_2 = matriz_distancias[c2_p2]
    linha_p2_3 = matriz_distancias[c3_p2]

    for v in range(n):  # procurar a menor distância de d1
        d1 = linha_p1_1[v]
        if linha_p1_2[v] < d1:  # noqa: PLR1730
            d1 = linha_p1_2[v]
        if linha_p1_3[v] < d1:  # noqa: PLR1730
            d1 = linha_p1_3[v]

        d2 = linha_p2_1[v]  # procurar a menor distância de d2
        if linha_p2_2[v] < d2:  # noqa: PLR1730
            d2 = linha_p2_2[v]
        if linha_p2_3[v] < d2:  # noqa: PLR1730
            d2 = linha_p2_3[v]

        if d1 < d2:  # comparativo entre d1 e d2 para saber a menor distância
            saldo += pesos[v]
        elif d2 < d1:
            saldo -= pesos[v]
        # se d1 == d2 (incluindo empate de distância finita ou ambos inalcançaveis / inf)
        # o peso do vértice se anula na diferença de saldo (0)
    return saldo


def extrair_tres_centros(bitmask: int) -> tuple[int, int, int]:
    """
    Extrai os três `idx` dos centros escolhidos registrados na bitmask. Esta função só deve ser
    utilizada se os 3 centros tiverem sido escolhidos.

    Args:
        bitmask: Bitmask dos centros escolhidos.

    Returns:
        Tripla contendo os três `idx` dos centros escolhidos registrados na bitmask.
    """
    lsb = (
        bitmask & -bitmask
    )  # apaga todos os outros bits e deixa só o mais a direita aceso
    p1 = lsb.bit_length() - 1  # para descobrir a posicao do bit
    bitmask ^= lsb  # apaga esse bit da bitmask para pegar o próximo
    lsb = bitmask & -bitmask
    p2 = lsb.bit_length() - 1
    bitmask ^= lsb
    lsb = bitmask & -bitmask
    p3 = lsb.bit_length() - 1
    return p1, p2, p3


def minimax(
    mask_p1: int,
    mask_p2: int,
    profundidade: int,
    alfa: float,
    beta: float,
) -> float:
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
        alfa: Piso de P1 (que procura MAX em suas jogadas). Melhor valor já encontrado nas outras
              opções de jogada já checadas até o momento. P1 só escolhe algo igual ou acima a isso.
        beta: Teto de P2 (que procura MIN em suas jogadas). Pior valor já encontrado nas outras
              opções de jogada já checadas até o momento. P2 só escolhe algo igual ou abaixo disso.

    Returns:
        O valor da melhor jogada encontrado pelo jogador da vez com base no estado atual.
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
            alfa = valor_salvo if alfa < valor_salvo else alfa  # noqa: FURB136
        elif flag == "SUPERIOR":  # valor alfa-podado da opção, o valor real é <=
            # min(valor_salvo, beta), abaixa o teto da busca
            beta = valor_salvo if beta > valor_salvo else beta  # noqa: FURB136

        # poda alfa-beta: se alfa alcança ou passa de beta, a janela de busca de um melhor valor
        # [alfa,beta] fecha, o que significa que o valor real está fora dela, pois um dos jogadores
        # já tem uma opção melhor
        if alfa >= beta:
            return valor_salvo

    eh_min = bool(profundidade % 2)  # profundidade ímpar -> MIN, par -> MAX
    melhor_valor = float("+inf") if eh_min else float("-inf")
    mask_jogo = mask_p1 | mask_p2  # bitwise or gerando o bitmask geral do jogo
    for i in CACHE.ordem_nos:
        mask_no_atual = 1 << i
        if mask_jogo & mask_no_atual:  # se o i-ésimo bit estiver ocupado
            continue

        next_mask_p1, next_mask_p2 = (
            (mask_p1, mask_p2 | mask_no_atual)  # p2 joga em i se profundidade ímpar
            if eh_min
            else (mask_p1 | mask_no_atual, mask_p2)  # p1 joga em i se profundidade par
        )

        valor = minimax(next_mask_p1, next_mask_p2, profundidade - 1, alfa, beta)

        if eh_min:
            # min(melhor_valor, valor)
            melhor_valor = valor if valor < melhor_valor else melhor_valor  # noqa: FURB136
            # se o valor encontrado está abaixo do beta (teto), reduz o teto
            beta = melhor_valor if melhor_valor < beta else beta  # noqa: FURB136
        else:
            # max(melhor_valor, valor)
            melhor_valor = valor if valor > melhor_valor else melhor_valor  # noqa: FURB136
            # se o valor encontrado está acima do alfa (piso), aumenta o piso
            alfa = melhor_valor if melhor_valor > alfa else alfa  # noqa: FURB136

        # poda alfa-beta
        if alfa >= beta:
            break

    if (
        melhor_valor <= alfa_orig
    ):  # poda alfa, valor real da opção <= melhor_valor (fail-low)
        MEMO[chave_memo] = (melhor_valor, "SUPERIOR")
    elif (
        melhor_valor >= beta_orig
    ):  # poda beta, valor real da opção >= melhor_valor (fail-high)
        MEMO[chave_memo] = (melhor_valor, "INFERIOR")
    else:  # sem corte, guarda o valor real da opção
        MEMO[chave_memo] = (melhor_valor, "EXATO")

    return melhor_valor
