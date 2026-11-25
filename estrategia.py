import networkx as nx

CACHE: dict[
    str,
    tuple  # idx_para_rotulo
    | int  # n
    | dict  # rotulo_para_idx
    | tuple[float, ...]  # pesos, centralidades_ponderadas
    | list[list[int]]  # matriz_distancias
    | tuple[int],  # ordem_nos
] = {}

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
    """
    assinatura_atual = gerar_assinatura(grafo)

    if CACHE.get("assinatura") == assinatura_atual:  # cache válido
        return

    MEMO.clear()

    idx_para_rotulo = gerar_idx_para_rotulo(grafo)
    n = len(idx_para_rotulo)
    rotulo_para_idx = gerar_rotulo_para_idx(idx_para_rotulo, n)
    pesos = gerar_vetor_de_pesos(grafo, idx_para_rotulo, n)
    matriz_distancias = gerar_matriz_de_distancias(grafo, rotulo_para_idx, n)
    centralidades_ponderadas = gerar_vetor_de_centralidades_ponderadas(
        pesos,
        matriz_distancias,
        n,
    )
    ordem_nos = gerar_ordem_nos(centralidades_ponderadas, n)

    CACHE.clear()
    CACHE.update(
        {
            "assinatura": assinatura_atual,
            "n": n,
            "rotulo_para_idx": rotulo_para_idx,
            "idx_para_rotulo": idx_para_rotulo,
            "pesos": pesos,
            "matriz_distancias": matriz_distancias,
            "centralidades_ponderadas": centralidades_ponderadas,
            "ordem_nos": ordem_nos,
        }
    )


def extrair_tres_centros(mascara: int): # mask_p1 e mask_p2
    posicoes = ()

    for i in range(3): 
        lsb = mascara & -mascara # apaga todos os outros bits e deixa só o mais a direita aceso
        posicao = lsb.bit_length() - 1 # para descobrir a posicao do bit
        posicoes = posicoes + (posicao, )
        mascara ^= lsb # apaga esse bit da mascara para pegar o próximo

    return posicoes


def avaliar_folha(mask_P1: int, mask_P2: int):
    n = CACHE["n"]
    pesos = CACHE["pesos"]
    matriz = CACHE["matriz_distancias"]
    c1_p1, c2_p1, c3_p1 = extrair_tres_centros(mask_P1) # extrair os 3 indices 
    c1_p2, c2_p2, c3_p2 = extrair_tres_centros(mask_P2)
    saldo = 0 # acumulador

    linha_p1_1 = matriz[c1_p1] # linhas do time 1
    linha_p1_2 = matriz[c2_p1]
    linha_p1_3 = matriz[c3_p1]

    linha_p2_1 = matriz[c1_p2] # linhas do time 2
    linha_p2_2 = matriz[c2_p2]
    linha_p2_3 = matriz[c3_p2]

    for v in range(n): # procurar a menor distância de d1
        d1 = linha_p1_1[v]
        if linha_p1_2[v] < d1:
            d1 = linha_p1_2[v]
        if linha_p1_3[v] < d1:
            d1 = linha_p1_3[v]

        d2 = linha_p2_1[v] # procurar a menor distância de d2
        if linha_p2_2[v] < d2:
            d2 = linha_p2_2[v]
        if linha_p2_3[v] < d2:
            d2 = linha_p2_3[v]

        if d1 < d2: # comparativo entre d1 e d2 para saber a menor distância
            saldo += pesos[v]
        elif d2 < d1:
            saldo -= pesos[v]
        # se d1 == d2 (incluindo empate de distância finita ou ambos inalcançaveis / inf)
        # o peso do vértice se anula na diferença de saldo (0)

    return saldo


def gerar_assinatura(grafo: nx.Graph) -> tuple[tuple, tuple]:
    """
    Gera a assinatura do grafo (sem times), uma tupla contendo uma tupla ordenada com nós e pesos e
    outra tupla ordenada com as arestas ordenadas
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
    """
    return (type(x).__name__, str(x))


def gerar_idx_para_rotulo(grafo: nx.Graph) -> tuple:
    """
    Gera um vetor que funciona como uma bijeção do tipo (`idx` -> rótulo), sendo `idx` o índice do
    rótulo na lista ordenada de rótulos.
    """
    return tuple(sorted(grafo.nodes, key=gerar_rotulo_de_comparacao))


def gerar_rotulo_para_idx(idx_para_rotulo: tuple, n: int) -> dict:
    """
    Gera um dicionário que espelha o vetor `idx_para_rótulo`.
    """
    return {idx_para_rotulo[i]: i for i in range(n)}


def gerar_vetor_de_pesos(
    grafo: nx.Graph,
    idx_para_rotulo: tuple,
    n: int,
) -> tuple[float, ...]:
    """
    Gera um vetor que funciona como uma função do tipo (`idx` -> peso), sendo `idx` o índice do rótulo
    na lista ordenada de rótulos.
    """
    return tuple(grafo.nodes[idx_para_rotulo[i]]["peso"] for i in range(n))


def gerar_matriz_de_distancias(
    grafo: nx.Graph,
    rotulo_para_idx: dict,
    n: int,
) -> list[list[int]]:
    """
    Gera uma matriz das menores distâncias entre `u` e `v`, sendo `u` e `v` qualquer par de `idx` no grafo.
    """
    matriz = [[0 for _ in range(n)] for _ in range(n)]

    distancias_raw = nx.all_pairs_shortest_path_length(grafo)

    for origem, distancias in distancias_raw:
        u = rotulo_para_idx[origem]
        for destino, distancia in distancias.items():
            v = rotulo_para_idx[destino]
            matriz[u][v] = distancia

    return matriz


def calcular_centralidade_ponderada(
    u: int,
    pesos: tuple[float, ...],
    matriz_distancias: list[list[int]],
    n: int,
) -> float:
    """
    Calcula a centralidade de Proximidade Ponderada de `u`, que mede seu alcance territorial
    ponderado sobre todo o grafo, indicando o quão bem posicionado `u` está em relação a regiões
    de pesos altos.
    """
    return sum(pesos[v] / (matriz_distancias[u][v] + 1) for v in range(n))


def gerar_vetor_de_centralidades_ponderadas(
    pesos: tuple[float, ...],
    matriz_distancias: list[list[int]],
    n: int,
) -> tuple[float, ...]:
    """
    Gera o vetor da imagem da função que calcula a centralidade ponderada que conta com domínio os
    `idx` do grafo.
    """
    return tuple(
        calcular_centralidade_ponderada(u, pesos, matriz_distancias, n)
        for u in range(n)
    )


def gerar_ordem_nos(
    centralidades_ponderadas: tuple[float, ...],
    n: int,
) -> tuple[int, ...]:
    """
    Gera um vetor ordenado dos `idx` daquele com a maior centralidade ponderada até aquele com a
    menor.
    """
    return tuple(
        sorted(
            range(n),
            key=lambda u: centralidades_ponderadas[u],
            reverse=True,
        )
    )