import networkx as nx

MEMO = {}
CACHE = {}


def minimax_com_poda_alfa_beta(grafo: nx.Graph): ...


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
              opções de jogada já checadas até o momento. P1 só escolhe algo igual ou acima a isso,
              pulando a checagem de qualquer opção que tenha a possibilidade de estar abaixo.
        beta: Teto de P2 (que procura MIN em suas jogadas). Pior valor já encontrado nas outras
              opções de jogada já checadas até o momento. P2 só escolhe algo igual ou abaixo disso,
              pulando a checagem de qualquer opção que tenha a possibilidade de estar acima.

    Returns:
        O valor da melhor jogada encontrado pelo jogador da vez, MAX se
    """
    if profundidade == 0:  # avaliar valor da folha (profundade 0)
        # TODO: avaliar folhas
        ...

    alfa_orig, beta_orig = alfa, beta
    chave_memo = (mask_p1, mask_p2)
    valor_salvo, flag = MEMO.get(chave_memo, (None, None))

    if valor_salvo is not None:
        if flag == "EXATO":  # valor real da opção, sem poda
            return valor_salvo

        if flag == "INFERIOR":  # valor beta-podado da opção, o valor real está acima
            # max(valor_salvo, alfa), aumenta o piso da busca
            alfa = valor_salvo if alfa < valor_salvo else alfa  # noqa: FURB136
        elif flag == "SUPERIOR":  # valor alfa-podado da opção, o valor real está abaixo
            # min(valor_salvo, beta), abaixa o teto da busca
            beta = valor_salvo if beta > valor_salvo else beta  # noqa: FURB136

        # poda alfa-beta: se alfa passa de beta, a janela de busca de um melhor valor [alfa,beta]
        # fecha, o que significa que o melhor valor já foi encontrado e é o salvo
        if alfa >= beta:
            return valor_salvo

    eh_min = bool(profundidade % 2)  # profundidade ímpar -> MIN, par -> MAX
    melhor_valor = float("+inf") if eh_min else float("-inf")

    for i in CACHE["ordem_nos"]:
        if (mask_p1 | mask_p2) & (1 << i):  # se o i-ésimo bit estiver ocupado
            continue

        next_mask_p1, next_mask_p2 = (
            (mask_p1, mask_p2 | (1 << i))  # p2 joga em i se profundidade ímpar
            if eh_min
            else (mask_p1 | (1 << i), mask_p2)  # p1 joga em i se profundidade par
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

    if melhor_valor <= alfa_orig:  # poda alfa, o valor real da opção é inferior
        MEMO[chave_memo] = (melhor_valor, "SUPERIOR")
    elif melhor_valor >= beta_orig:  # poda beta, o valor real da opção é superior
        MEMO[chave_memo] = (melhor_valor, "INFERIOR")
    else:  # sem corte, guarda o valor real da opção
        MEMO[chave_memo] = (melhor_valor, "EXATO")

    return melhor_valor
