"""Análise semântica.

Confere o que a gramática sozinha não pega (variável não declarada, Mata_papai
fora de laço, número errado de argumentos...) e anota a árvore com o que o
gerador precisa saber:

* ``no.simbolo``    – a variável/função a que um nome se refere;
* ``no.tipo_expr``  – o tipo de cada expressão ('int', 'float', 'char', 'str',
                      'entrada', 'bool' ou 'void');
* nomes em Python sem conflito (C tem escopo de bloco, Python não: uma variável
  que esconde outra de fora ganha um nome novo, ex.: ``x_2``);
* quais globais cada função altera (vira ``global x`` no Python);
* quais VocêÉDeLá (for) podem virar ``for ... in range(...)``.
"""

import keyword

from .arvore import (
    Atribuicao, Binaria, Chamada, Declaracao, Funcao, Incremento, Leia, LeiaExpr,
    Numero, Variavel, percorrer,
)
from .erros import Aviso, ErroSemantico

# Nomes que não podem ser usados como estão no Python gerado.
RESERVADOS_PY = (
    set(keyword.kwlist)
    | set(keyword.softkwlist)
    | {"print", "input", "int", "float", "str", "chr", "ord", "bool", "range"}
)

TEXTOS = ("str", "entrada")

NOME_TIPO = {
    "int": "Red_bull",
    "float": "Jarbas/Katrina",
    "char": "Porra",
    "str": "texto",
    "entrada": "texto lido",
    "bool": "condição",
    "void": "nada",
}


class Simbolo:
    def __init__(self, nome, nome_py, classe, tipo, eh_global, no):
        self.nome = nome
        self.nome_py = nome_py
        self.classe = classe  # 'variavel', 'parametro' ou 'funcao'
        self.tipo = tipo  # TipoC (ou None para função sem retorno)
        self.eh_global = eh_global
        self.no = no

    @property
    def categoria(self):
        return self.tipo.categoria if self.tipo is not None else "void"


class Analisador:
    def __init__(self):
        self.escopos = []
        self.funcao_atual = None
        self.lacos = 0
        self.avisos = []
        self.globais_alterados_por_funcoes = set()
        self.ranges_a_confirmar = []

    # ------------------------------------------------------------ entrada

    def analisar(self, programa):
        self.escopos = [{}]
        # 1ª passada: registra todas as funções, para poder chamar antes de declarar.
        for item in programa.itens:
            if isinstance(item, Funcao):
                if item.nome in self.escopos[0]:
                    anterior = self.escopos[0][item.nome].no
                    raise ErroSemantico(
                        f"a função '{item.nome}' já foi declarada na linha {anterior.linha}", item.linha, item.coluna
                    )
                sym = Simbolo(item.nome, self._nome_livre(item.nome), "funcao", item.retorno, True, item)
                self.escopos[0][item.nome] = sym
                item.simbolo = sym
        # 2ª passada: analisa tudo na ordem do código.
        for item in programa.itens:
            if isinstance(item, Funcao):
                self._funcao(item)
            else:
                self._comando(item)
        # Só agora sabemos quais globais as funções alteram.
        for para, limite in self.ranges_a_confirmar:
            if limite & self.globais_alterados_por_funcoes:
                para.range = None
        return self.avisos

    # ------------------------------------------------------------ escopos

    def _abrir(self):
        self.escopos.append({})

    def _fechar(self):
        self.escopos.pop()

    def _buscar(self, nome):
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        return None

    def _nome_livre(self, nome, usados=None):
        if usados is None:
            usados = {s.nome_py for escopo in self.escopos for s in escopo.values()}
        base = nome + "_" if nome in RESERVADOS_PY else nome
        candidato, n = base, 2
        while candidato in usados or candidato in RESERVADOS_PY:
            candidato = f"{base}_{n}"
            n += 1
        return candidato

    def _declarar(self, nome, classe, tipo, no):
        escopo = self.escopos[-1]
        if nome in escopo:
            anterior = escopo[nome]
            if anterior.classe == "funcao":
                msg = f"'{nome}' já é o nome de uma função"
            else:
                msg = f"'{nome}' já foi declarada neste bloco (linha {anterior.no.linha})"
            raise ErroSemantico(msg, no.linha, no.coluna)
        if classe == "parametro":
            # Parâmetro esconde qualquer coisa de fora durante a função inteira, então
            # pode manter o nome; só não pode bater com outro parâmetro.
            nome_py = self._nome_livre(nome, {s.nome_py for s in escopo.values()})
        else:
            nome_py = self._nome_livre(nome)
        eh_global = self.funcao_atual is None and len(self.escopos) == 1
        sym = Simbolo(nome, nome_py, classe, tipo, eh_global, no)
        escopo[nome] = sym
        return sym

    def _aviso(self, mensagem, no):
        self.avisos.append(Aviso(mensagem, no.linha, no.coluna))

    # ------------------------------------------------------------ funções

    def _funcao(self, f):
        self.funcao_atual = f
        f.globais = set()
        f.tem_retorno = False
        self._abrir()
        for p in f.params:
            p.simbolo = self._declarar(p.nome, "parametro", p.tipo, p)
        for cmd in f.corpo.comandos:  # o corpo divide o escopo com os parâmetros, como em C
            self._comando(cmd)
        self._fechar()
        if f.retorno is not None and not f.tem_retorno:
            self._aviso(f"a função '{f.nome}' tem tipo de retorno mas nunca usa Ce_é_mo_playboy", f)
        self.funcao_atual = None

    # ------------------------------------------------------------ comandos

    def _comando(self, cmd):
        getattr(self, "_cmd_" + type(cmd).__name__)(cmd)

    def _cmd_Bloco(self, bloco):
        self._abrir()
        for cmd in bloco.comandos:
            self._comando(cmd)
        self._fechar()

    def _cmd_Vazio(self, cmd):
        pass

    def _cmd_Declaracao(self, cmd):
        categoria = cmd.tipo.categoria
        for d in cmd.itens:
            if d.valor is not None:
                tipo = self._expr(d.valor)
                self._checar_conversao(tipo, categoria, d.valor, f"guardar isso em '{d.nome}'")
            d.simbolo = self._declarar(d.nome, "variavel", cmd.tipo, d)

    def _variavel_alvo(self, nome, no):
        """Busca a variável que vai receber um valor e registra a alteração."""
        sym = self._buscar(nome)
        if sym is None:
            raise ErroSemantico(
                f"a variável '{nome}' não foi declarada (declare antes, ex.: Red_bull {nome} = 0;)", no.linha, no.coluna
            )
        if sym.classe == "funcao":
            raise ErroSemantico(f"'{nome}' é uma função, não dá pra guardar valor nela", no.linha, no.coluna)
        if self.funcao_atual is not None and sym.eh_global:
            self.funcao_atual.globais.add(sym.nome_py)
            self.globais_alterados_por_funcoes.add(sym)
        return sym

    def _operacao_sobre(self, sym, op, valor, no):
        """Monta 'x op valor' para x += valor, x++ etc., e confere os tipos."""
        var = Variavel(sym.nome, linha=no.linha, coluna=no.coluna)
        var.simbolo = sym
        var.tipo_expr = sym.categoria
        conta = Binaria(op, var, valor, linha=no.linha, coluna=no.coluna)
        conta.tipo_expr = self._tipar_binaria(conta, sym.categoria, valor.tipo_expr)
        self._checar_conversao(conta.tipo_expr, sym.categoria, conta, f"guardar isso em '{sym.nome}'")
        return conta

    def _cmd_Atribuicao(self, cmd):
        cmd.simbolo = self._variavel_alvo(cmd.alvo, cmd)
        tipo = self._expr(cmd.valor)
        if cmd.op == "=":
            self._checar_conversao(tipo, cmd.simbolo.categoria, cmd.valor, f"guardar isso em '{cmd.alvo}'")
        else:
            cmd.conta = self._operacao_sobre(cmd.simbolo, cmd.op[0], cmd.valor, cmd)

    def _cmd_Incremento(self, cmd):
        cmd.simbolo = self._variavel_alvo(cmd.alvo, cmd)
        um = Numero(1, False, linha=cmd.linha, coluna=cmd.coluna)
        um.tipo_expr = "int"
        cmd.conta = self._operacao_sobre(cmd.simbolo, "+" if cmd.op == "++" else "-", um, cmd)

    def _condicao(self, expr):
        self._expr(expr)

    def _cmd_Se(self, cmd):
        self._condicao(cmd.condicao)
        self._cmd_Bloco(cmd.entao)
        if cmd.senao is not None:
            self._comando(cmd.senao)

    def _cmd_Enquanto(self, cmd):
        self._condicao(cmd.condicao)
        self.lacos += 1
        self._cmd_Bloco(cmd.corpo)
        self.lacos -= 1

    def _cmd_Para(self, cmd):
        self._abrir()  # a variável declarada no VocêÉDeLá só existe dentro dele
        if cmd.inicio is not None:
            self._comando(cmd.inicio)
        if cmd.condicao is not None:
            self._condicao(cmd.condicao)
        if cmd.passo is not None:
            self._comando(cmd.passo)
        self.lacos += 1
        self._cmd_Bloco(cmd.corpo)
        self.lacos -= 1
        self._fechar()
        cmd.range = self._avaliar_range(cmd)

    def _cmd_Pare(self, cmd):
        if self.lacos == 0:
            raise ErroSemantico("Mata_papai (break) só pode ser usado dentro de um laço", cmd.linha, cmd.coluna)

    def _cmd_Continua(self, cmd):
        if self.lacos == 0:
            raise ErroSemantico("MeuBraço (continue) só pode ser usado dentro de um laço", cmd.linha, cmd.coluna)

    def _cmd_Retorne(self, cmd):
        f = self.funcao_atual
        if f is None:
            raise ErroSemantico(
                "Ce_é_mo_playboy (return) só pode ser usado dentro de uma função (Samu)", cmd.linha, cmd.coluna
            )
        f.tem_retorno = True
        cmd.tipo_destino = f.retorno.categoria if f.retorno is not None else None
        if cmd.valor is None:
            if f.retorno is not None:
                raise ErroSemantico(
                    f"a função '{f.nome}' precisa retornar um valor do tipo {NOME_TIPO[f.retorno.categoria]}",
                    cmd.linha, cmd.coluna,
                )
            return
        tipo = self._expr(cmd.valor)
        if f.retorno is None:
            raise ErroSemantico(
                f"a função '{f.nome}' não tem tipo de retorno, então não pode retornar valor "
                f"(declare com tipo, ex.: Samu Red_bull {f.nome}(...))",
                cmd.linha, cmd.coluna,
            )
        self._checar_conversao(tipo, f.retorno.categoria, cmd.valor, f"retornar isso de '{f.nome}'")

    def _cmd_Imprima(self, cmd):
        for arg in cmd.args:
            self._expr(arg)

    def _cmd_Leia(self, cmd):
        for var in cmd.alvos:
            var.simbolo = self._variavel_alvo(var.nome, var)
            var.tipo_expr = var.simbolo.categoria

    def _cmd_ComandoChamada(self, cmd):
        self._expr(cmd.chamada, pode_ser_void=True)

    # ------------------------------------------------------------ expressões

    def _expr(self, e, pode_ser_void=False):
        e.tipo_expr = getattr(self, "_expr_" + type(e).__name__)(e)
        if e.tipo_expr == "void" and not pode_ser_void:
            raise ErroSemantico(
                f"a função '{e.nome}' não retorna nada (Samu sem tipo), então não dá pra usar o resultado dela",
                e.linha, e.coluna,
            )
        return e.tipo_expr

    def _expr_Numero(self, e):
        return "float" if e.real else "int"

    def _expr_Caractere(self, e):
        return "char"

    def _expr_Texto(self, e):
        return "str"

    def _expr_LeiaExpr(self, e):
        return "entrada"

    def _expr_Variavel(self, e):
        sym = self._buscar(e.nome)
        if sym is None:
            raise ErroSemantico(
                f"a variável '{e.nome}' não foi declarada (declare antes, ex.: Red_bull {e.nome} = 0;)",
                e.linha, e.coluna,
            )
        if sym.classe == "funcao":
            raise ErroSemantico(
                f"'{e.nome}' é uma função; pra chamar use Tô_No_SAMU {e.nome}(...)", e.linha, e.coluna
            )
        e.simbolo = sym
        return sym.categoria

    def _expr_Chamada(self, e):
        sym = self._buscar(e.nome)
        if sym is None:
            raise ErroSemantico(f"a função '{e.nome}' não existe", e.linha, e.coluna)
        if sym.classe != "funcao":
            raise ErroSemantico(f"'{e.nome}' é uma variável, não uma função", e.linha, e.coluna)
        f = sym.no
        if len(e.args) != len(f.params):
            raise ErroSemantico(
                f"a função '{e.nome}' espera {len(f.params)} argumento(s), mas recebeu {len(e.args)}",
                e.linha, e.coluna,
            )
        for arg, p in zip(e.args, f.params):
            tipo = self._expr(arg)
            self._checar_conversao(tipo, p.tipo.categoria, arg, f"passar isso como '{p.nome}' para '{e.nome}'")
        e.simbolo = sym
        return sym.categoria

    def _expr_Conversao(self, e):
        tipo = self._expr(e.valor)
        destino = e.para.categoria
        self._checar_conversao(tipo, destino, e.valor, f"converter isso para {NOME_TIPO[destino]}")
        return destino

    def _expr_Unaria(self, e):
        tipo = self._expr(e.operando)
        e.ord = False
        if e.op == "!":
            return "bool"
        if tipo in TEXTOS:
            raise ErroSemantico(f"não dá pra usar '{e.op}' em texto", e.linha, e.coluna)
        e.ord = tipo == "char"  # em C, char em conta vira número
        return "int" if tipo in ("char", "bool") else tipo

    def _expr_Binaria(self, e):
        return self._tipar_binaria(e, self._expr(e.esq), self._expr(e.dir))

    def _tipar_binaria(self, e, te, td):
        e.ord_esq = e.ord_dir = e.div_inteira = False
        op = e.op
        if op in ("&&", "||"):
            return "bool"
        texto_e, texto_d = te in TEXTOS, td in TEXTOS
        if op == "+" and (texto_e or texto_d or (te == "char" and td == "char")):
            if not ((texto_e or te == "char") and (texto_d or td == "char")):
                raise ErroSemantico(
                    "não dá pra somar texto com número; no vo_fica_pelado_aqui separe com vírgula",
                    e.linha, e.coluna,
                )
            return "str"  # concatenação
        if op in ("==", "!=", "<", "<=", ">", ">="):
            if (texto_e or te == "char") and (texto_d or td == "char"):
                return "bool"
            if texto_e or texto_d:
                raise ErroSemantico(
                    "não dá pra comparar texto com número (guarde o texto lido numa variável Red_bull antes)",
                    e.linha, e.coluna,
                )
            e.ord_esq, e.ord_dir = te == "char", td == "char"
            return "bool"
        # contas: + - * / %
        if texto_e or texto_d:
            raise ErroSemantico(f"não dá pra usar '{op}' com texto", e.linha, e.coluna)
        e.ord_esq, e.ord_dir = te == "char", td == "char"
        num_e = "int" if te in ("char", "bool") else te
        num_d = "int" if td in ("char", "bool") else td
        resultado = "float" if "float" in (num_e, num_d) else "int"
        if op == "/" and resultado == "int":
            e.div_inteira = True  # em C, 7 / 2 == 3
        if op in ("/", "%") and isinstance(e.dir, Numero) and e.dir.valor == 0:
            self._aviso("divisão por zero", e)
        return resultado

    def _checar_conversao(self, origem, destino, no, contexto):
        if destino in ("int", "float") and origem == "str":
            raise ErroSemantico(
                f"não dá pra {contexto}: é texto, mas o tipo é {NOME_TIPO[destino]}", no.linha, no.coluna
            )

    # ------------------------------------------------------------ for -> range

    def _avaliar_range(self, cmd):
        """Decide se o VocêÉDeLá pode virar ``for i in range(...)``.

        Só vale para o formato clássico (Red_bull i = a; i < b; i++), quando
        nada dentro do laço mexe em i nem no limite. Se não der, o gerador usa
        a tradução geral com while, que funciona sempre.
        """
        ini, cond = cmd.inicio, cmd.condicao
        if not (isinstance(ini, Declaracao) and len(ini.itens) == 1):
            return None
        decl = ini.itens[0]
        var = decl.simbolo
        if var.categoria != "int" or decl.valor is None or decl.valor.tipo_expr != "int":
            return None
        if not (
            isinstance(cond, Binaria) and cond.op in ("<", "<=", ">", ">=")
            and isinstance(cond.esq, Variavel) and cond.esq.simbolo is var
            and cond.dir.tipo_expr == "int"
        ):
            return None
        passo = self._passo_constante(cmd.passo, var)
        if passo is None or (passo > 0) != (cond.op in ("<", "<=")):
            return None
        limite = set()
        for n in percorrer(cond.dir):
            if isinstance(n, (Chamada, LeiaExpr)):
                return None
            if isinstance(n, Variavel):
                limite.add(n.simbolo)
        alterados, tem_chamada = set(), False
        for n in percorrer(cmd.corpo):
            if isinstance(n, (Atribuicao, Incremento)):
                alterados.add(n.simbolo)
            elif isinstance(n, Leia):
                alterados.update(v.simbolo for v in n.alvos)
            elif isinstance(n, Chamada):
                tem_chamada = True
        if var in alterados or limite & alterados:
            return None
        if tem_chamada and any(s.eh_global for s in limite):
            # Uma função chamada no laço pode alterar o limite; confere no fim.
            self.ranges_a_confirmar.append((cmd, limite))
        return {
            "var": var,
            "inicio": decl.valor,
            "limite": cond.dir,
            "passo": passo,
            "inclusivo": cond.op in ("<=", ">="),
        }

    @staticmethod
    def _passo_constante(passo, var):
        def inteiro_positivo(n):
            return isinstance(n, Numero) and not n.real and n.valor > 0

        def eh_var(n):
            return isinstance(n, Variavel) and n.simbolo is var

        if isinstance(passo, Incremento) and passo.simbolo is var:
            return 1 if passo.op == "++" else -1
        if isinstance(passo, Atribuicao) and passo.simbolo is var:
            v = passo.valor
            if passo.op in ("+=", "-=") and inteiro_positivo(v):
                return v.valor if passo.op == "+=" else -v.valor
            if passo.op == "=" and isinstance(v, Binaria) and v.op in ("+", "-"):
                if eh_var(v.esq) and inteiro_positivo(v.dir):
                    return v.dir.valor if v.op == "+" else -v.dir.valor
                if v.op == "+" and eh_var(v.dir) and inteiro_positivo(v.esq):
                    return v.esq.valor
        return None

