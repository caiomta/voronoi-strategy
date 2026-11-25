import networkx as nx


def minimax_com_poda_alfa_beta(grafo: nx.Graph): ...
  

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
        # TODO: avaliar folhas
        ...

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



