import networkx as nx


def minimax_com_poda_alfa_beta(grafo: nx.Graph): ...


def extrair_tres_centros(mascara: int) -> tuple[int, int, int]:
    lsb = (
        mascara & -mascara
    )  # apaga todos os outros bits e deixa só o mais a direita aceso
    p1 = lsb.bit_length() - 1  # para descobrir a posicao do bit
    mascara ^= lsb  # apaga esse bit da mascara para pegar o próximo
    lsb = mascara & -mascara
    p2 = lsb.bit_length() - 1
    mascara ^= lsb
    lsb = mascara & -mascara
    p3 = lsb.bit_length() - 1
    return p1, p2, p3


def avaliar_folha(mask_p1: int, mask_p2: int) -> float:
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
