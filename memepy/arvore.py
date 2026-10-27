"""Nós da árvore sintática (AST).

Os campos declarados aqui vêm do parser. A análise semântica pendura
informações extras nos nós como atributos comuns (simbolo, tipo_expr, ...).
"""

from dataclasses import dataclass, fields


@dataclass(eq=False, kw_only=True)
class No:
    linha: int = 0
    coluna: int = 0


def no(cls):
    return dataclass(eq=False)(cls)


# ---------------------------------------------------------------- estrutura

@no
class TipoC(No):
    partes: list  # ex.: ["UNSIGNED", "INT"]

    @property
    def categoria(self):
        """Como o tipo se comporta: 'int', 'float' ou 'char'."""
        if "FLOAT" in self.partes or "DOUBLE" in self.partes:
            return "float"
        if "CHAR" in self.partes:
            return "char"
        return "int"


@no
class Programa(No):
    itens: list


@no
class Funcao(No):
    retorno: object  # TipoC ou None (função sem retorno)
    nome: str
    params: list
    corpo: object


@no
class Parametro(No):
    tipo: TipoC
    nome: str


# ---------------------------------------------------------------- comandos

@no
class Bloco(No):
    comandos: list


@no
class Declaracao(No):
    tipo: TipoC
    itens: list  # de Declarador


@no
class Declarador(No):
    nome: str
    valor: object  # expressão ou None


@no
class Atribuicao(No):
    alvo: str
    op: str  # =, +=, -=, *=, /=, %=
    valor: object


@no
class Incremento(No):
    alvo: str
    op: str  # ++ ou --


@no
class Se(No):
    condicao: object
    entao: Bloco
    senao: object  # Bloco, Se (para Faz_Isso_Comigo_Não_Velho) ou None


@no
class Enquanto(No):
    condicao: object
    corpo: Bloco


@no
class Para(No):
    inicio: object
    condicao: object
    passo: object
    corpo: Bloco


@no
class Pare(No):
    pass


@no
class Continua(No):
    pass


@no
class Retorne(No):
    valor: object


@no
class Imprima(No):
    args: list


@no
class Leia(No):
    prompt: object  # texto ou None
    alvos: list  # de Variavel


@no
class ComandoChamada(No):
    chamada: object


@no
class Vazio(No):
    pass


# ---------------------------------------------------------------- expressões

@no
class Numero(No):
    valor: object
    real: bool


@no
class Caractere(No):
    valor: str


@no
class Texto(No):
    valor: str


@no
class Variavel(No):
    nome: str


@no
class Binaria(No):
    op: str
    esq: object
    dir: object


@no
class Unaria(No):
    op: str
    operando: object


@no
class Chamada(No):
    nome: str
    args: list


@no
class LeiaExpr(No):
    prompt: object


@no
class Conversao(No):
    para: TipoC
    valor: object


# ---------------------------------------------------------------- utilidades

def percorrer(valor):
    """Visita o nó e todos os seus descendentes."""
    if isinstance(valor, list):
        for item in valor:
            yield from percorrer(item)
    elif isinstance(valor, No):
        yield valor
        for campo in fields(valor):
            yield from percorrer(getattr(valor, campo.name))


def despejar(valor, nivel=0):
    """Desenha a árvore em texto, para a opção --arvore."""
    pad = "  " * nivel
    if isinstance(valor, TipoC):
        return f"{pad}Tipo {' '.join(valor.partes)}"
    if not isinstance(valor, No):
        return f"{pad}{valor!r}"
    simples, filhos = [], []
    for campo in fields(valor):
        if campo.name in ("linha", "coluna"):
            continue
        v = getattr(valor, campo.name)
        if isinstance(v, (No, list)):
            filhos.append((campo.name, v))
        elif v is not None:
            simples.append(f"{campo.name}={v!r}")
    cabeca = type(valor).__name__
    if simples:
        cabeca += f"({', '.join(simples)})"
    linhas = [f"{pad}{cabeca}  [linha {valor.linha}]"]
    for nome, v in filhos:
        if isinstance(v, list) and not v:
            continue
        linhas.append(f"{pad}  {nome}:")
        for item in v if isinstance(v, list) else [v]:
            linhas.append(despejar(item, nivel + 2))
    return "\n".join(linhas)
