"""Geração de código: percorre a árvore já analisada e escreve o Python."""

from .arvore import Funcao, Numero, Se, Unaria

# Precedência dos operadores no Python (maior = gruda mais forte).
OU, E, NAO, CMP, SOMA, MULT, UNARIO, ATOMO = range(1, 9)

OPERADORES = {
    "||": ("or", OU),
    "&&": ("and", E),
    "==": ("==", CMP), "!=": ("!=", CMP),
    "<": ("<", CMP), "<=": ("<=", CMP), ">": (">", CMP), ">=": (">=", CMP),
    "+": ("+", SOMA), "-": ("-", SOMA),
    "*": ("*", MULT), "/": ("/", MULT), "%": ("%", MULT),
}

TIPO_PY = {"int": "int", "float": "float", "char": "str"}
VALOR_PADRAO = {"int": "0", "float": "0.0", "char": '""'}


def texto_py(s):
    """Literal de texto em Python, preferindo aspas duplas."""
    r = repr(s)
    if r[0] == "'" and '"' not in s:
        r = '"' + r[1:-1] + '"'
    return r


class Gerador:
    def __init__(self):
        self.linhas = []
        self.nivel = 0
        # Pilha de laços abertos. Para VocêÉDeLá que virou while, guarda o passo
        # (i++), que precisa rodar antes de cada MeuBraço (continue).
        self.lacos = []

    def gerar(self, programa, nome_arquivo=None):
        origem = f" a partir de {nome_arquivo}" if nome_arquivo else ""
        self._emitir(f"# Gerado pelo memepy{origem}. Edite o código memético, não este arquivo.")
        funcoes = [i for i in programa.itens if isinstance(i, Funcao)]
        comandos = [i for i in programa.itens if not isinstance(i, Funcao)]
        # As funções vão para o topo: assim dá pra chamar uma função declarada mais abaixo.
        for f in funcoes:
            self._emitir("")
            self._emitir("")
            self._funcao(f)
        if comandos:
            self._emitir("")
            if funcoes:
                self._emitir("")
            self._comandos(comandos)
        return "\n".join(self.linhas) + "\n"

    # ------------------------------------------------------------ utilidades

    def _emitir(self, texto):
        self.linhas.append("    " * self.nivel + texto if texto else "")

    def _comandos(self, comandos):
        for cmd in comandos:
            getattr(self, "_cmd_" + type(cmd).__name__)(cmd)

    def _corpo(self, comandos, depois=None):
        """Escreve um bloco indentado; Python não aceita bloco vazio, então usa pass."""
        self.nivel += 1
        antes = len(self.linhas)
        self._comandos(comandos)
        if depois is not None:
            self._comandos([depois])
        if len(self.linhas) == antes:
            self._emitir("pass")
        self.nivel -= 1

    # ------------------------------------------------------------ funções

    def _funcao(self, f):
        params = ", ".join(f"{p.simbolo.nome_py}: {TIPO_PY[p.tipo.categoria]}" for p in f.params)
        retorno = f" -> {TIPO_PY[f.retorno.categoria]}" if f.retorno is not None else ""
        self._emitir(f"def {f.simbolo.nome_py}({params}){retorno}:")
        self.nivel += 1
        antes = len(self.linhas)
        if f.globais:
            self._emitir("global " + ", ".join(sorted(f.globais)))
        self._comandos(f.corpo.comandos)
        if len(self.linhas) == antes:
            self._emitir("pass")
        self.nivel -= 1

    # ------------------------------------------------------------ comandos

    def _cmd_Bloco(self, bloco):
        # Python não tem escopo de bloco; os nomes já foram ajustados na análise semântica.
        self._comandos(bloco.comandos)

    def _cmd_Vazio(self, cmd):
        pass

    def _cmd_Declaracao(self, cmd):
        categoria = cmd.tipo.categoria
        for d in cmd.itens:
            valor = VALOR_PADRAO[categoria] if d.valor is None else self._valor_para(d.valor, categoria)
            self._emitir(f"{d.simbolo.nome_py}: {TIPO_PY[categoria]} = {valor}")

    def _cmd_Atribuicao(self, cmd):
        if cmd.op == "=":
            valor = self._valor_para(cmd.valor, cmd.simbolo.categoria)
            self._emitir(f"{cmd.simbolo.nome_py} = {valor}")
        else:
            self._atualizar(cmd.simbolo, cmd.conta)

    def _cmd_Incremento(self, cmd):
        self._atualizar(cmd.simbolo, cmd.conta)

    def _atualizar(self, sym, conta):
        """x += 1, x /= 2 ... Usa a forma curta quando o tipo não muda."""
        destino = sym.categoria
        if self._sem_conversao(conta.tipo_expr, destino):
            op = "//" if conta.div_inteira else OPERADORES[conta.op][0]
            direita, _ = self._expr(conta.dir)
            if conta.ord_dir:
                direita = f"ord({direita})"
            self._emitir(f"{sym.nome_py} {op}= {direita}")
        else:
            self._emitir(f"{sym.nome_py} = {self._valor_para(conta, destino)}")

    def _cmd_Se(self, cmd):
        self._emitir(f"if {self._cond(cmd.condicao)}:")
        self._corpo(cmd.entao.comandos)
        senao = cmd.senao
        while isinstance(senao, Se):
            self._emitir(f"elif {self._cond(senao.condicao)}:")
            self._corpo(senao.entao.comandos)
            senao = senao.senao
        if senao is not None:
            self._emitir("else:")
            self._corpo(senao.comandos)

    def _cmd_Enquanto(self, cmd):
        self._emitir(f"while {self._cond(cmd.condicao)}:")
        self.lacos.append(None)
        self._corpo(cmd.corpo.comandos)
        self.lacos.pop()

    def _cmd_Para(self, cmd):
        r = cmd.range
        if r is not None:
            inicio = self._valor_para(r["inicio"], "int")
            limite, prec = self._expr(r["limite"])
            if r["inclusivo"]:
                limite = self._somar(r["limite"], limite, prec, 1 if r["passo"] > 0 else -1)
            if r["passo"] != 1:
                args = [inicio, limite, str(r["passo"])]
            elif inicio == "0":
                args = [limite]
            else:
                args = [inicio, limite]
            self._emitir(f"for {r['var'].nome_py} in range({', '.join(args)}):")
            self.lacos.append(None)
            self._corpo(cmd.corpo.comandos)
            self.lacos.pop()
            return
        # Tradução geral: inicialização; while condição: corpo; passo
        if cmd.inicio is not None:
            self._comandos([cmd.inicio])
        cond = self._cond(cmd.condicao) if cmd.condicao is not None else "True"
        self._emitir(f"while {cond}:")
        self.lacos.append(cmd.passo)
        self._corpo(cmd.corpo.comandos, depois=cmd.passo)
        self.lacos.pop()

    @staticmethod
    def _somar(no, codigo, prec, n):
        if isinstance(no, Numero):
            return str(no.valor + n)
        if prec < SOMA:
            codigo = f"({codigo})"
        return f"{codigo} + {n}" if n > 0 else f"{codigo} - {-n}"

    def _cmd_Pare(self, cmd):
        self._emitir("break")

    def _cmd_Continua(self, cmd):
        passo = self.lacos[-1]
        if passo is not None:
            self._comandos([passo])
        self._emitir("continue")

    def _cmd_Retorne(self, cmd):
        if cmd.valor is None:
            self._emitir("return")
        else:
            self._emitir(f"return {self._valor_para(cmd.valor, cmd.tipo_destino)}")

    def _cmd_Imprima(self, cmd):
        partes = []
        for arg in cmd.args:
            codigo, _ = self._expr(arg)
            if arg.tipo_expr == "bool":
                codigo = f"int({codigo})"  # em C, condição vale 1 ou 0
            partes.append(codigo)
        self._emitir(f"print({', '.join(partes)})")

    def _cmd_Leia(self, cmd):
        prompt = texto_py(cmd.prompt) if cmd.prompt is not None else ""
        if not cmd.alvos:
            self._emitir(f"input({prompt})")
            return
        for i, var in enumerate(cmd.alvos):
            leitura = f"input({prompt if i == 0 else ''})"
            categoria = var.simbolo.categoria
            if categoria in ("int", "float"):
                leitura = f"{categoria}({leitura})"
            self._emitir(f"{var.simbolo.nome_py} = {leitura}")

    def _cmd_ComandoChamada(self, cmd):
        self._emitir(self._expr(cmd.chamada)[0])

    # ------------------------------------------------------------ conversões

    @staticmethod
    def _sem_conversao(origem, destino):
        return origem == destino or (destino == "char" and origem in ("str", "entrada"))

    def _valor_para(self, e, destino):
        return self._converter(e, destino)[0]

    def _converter(self, e, destino):
        """Gera a expressão já convertida para o tipo de quem vai recebê-la."""
        origem = e.tipo_expr
        if destino == "float" and origem == "int":
            if isinstance(e, Numero):
                return f"{e.valor}.0", ATOMO
            if isinstance(e, Unaria) and e.op == "-" and isinstance(e.operando, Numero):
                return f"-{e.operando.valor}.0", UNARIO
        codigo, prec = self._expr(e)
        if self._sem_conversao(origem, destino):
            return codigo, prec
        if destino == "int":
            return (f"ord({codigo})" if origem == "char" else f"int({codigo})"), ATOMO
        if destino == "float":
            return (f"float(ord({codigo}))" if origem == "char" else f"float({codigo})"), ATOMO
        if destino == "char":
            return (f"chr(int({codigo}))" if origem == "float" else f"chr({codigo})"), ATOMO
        return codigo, prec

    # ------------------------------------------------------------ expressões

    def _cond(self, e):
        return self._expr(e, condicao=True)[0]

    def _expr(self, e, condicao=False):
        """Devolve (código, precedência) para decidir onde precisa de parênteses."""
        return getattr(self, "_e_" + type(e).__name__)(e, condicao)

    def _e_Numero(self, e, condicao):
        return (repr(e.valor) if e.real else str(e.valor)), ATOMO

    def _e_Caractere(self, e, condicao):
        return texto_py(e.valor), ATOMO

    def _e_Texto(self, e, condicao):
        return texto_py(e.valor), ATOMO

    def _e_Variavel(self, e, condicao):
        return e.simbolo.nome_py, ATOMO

    def _e_LeiaExpr(self, e, condicao):
        prompt = texto_py(e.prompt) if e.prompt is not None else ""
        return f"input({prompt})", ATOMO

    def _e_Chamada(self, e, condicao):
        params = e.simbolo.no.params
        args = [self._valor_para(a, p.tipo.categoria) for a, p in zip(e.args, params)]
        return f"{e.simbolo.nome_py}({', '.join(args)})", ATOMO

    def _e_Conversao(self, e, condicao):
        return self._converter(e.valor, e.para.categoria)

    def _e_Unaria(self, e, condicao):
        if e.op == "!":
            codigo, prec = self._expr(e.operando, condicao=True)
            if prec < NAO:
                codigo = f"({codigo})"
            return f"not {codigo}", NAO
        codigo, prec = self._expr(e.operando)
        if e.ord:
            codigo, prec = f"ord({codigo})", ATOMO
        if prec < UNARIO:
            codigo = f"({codigo})"
        return f"{e.op}{codigo}", UNARIO

    def _e_Binaria(self, e, condicao):
        op, prec = OPERADORES[e.op]
        logico = e.op in ("&&", "||")
        # Dentro de if/while basta o valor "verdadeiro/falso"; fora, && e || de C
        # sempre dão 1 ou 0, então os lados viram bool.
        esq, pe = self._expr(e.esq, condicao and logico)
        dir_, pd = self._expr(e.dir, condicao and logico)
        if logico and not condicao:
            if e.esq.tipo_expr != "bool":
                esq, pe = f"bool({esq})", ATOMO
            if e.dir.tipo_expr != "bool":
                dir_, pd = f"bool({dir_})", ATOMO
        if e.op == "/" and e.div_inteira:
            op = "//"
        if getattr(e, "ord_esq", False):
            esq, pe = f"ord({esq})", ATOMO
        if getattr(e, "ord_dir", False):
            dir_, pd = f"ord({dir_})", ATOMO
        # Comparações em Python encadeiam (1 < x < 3); em C não, então isola com parênteses.
        if pe < prec or (prec == CMP and pe == CMP):
            esq = f"({esq})"
        if pd <= prec:
            dir_ = f"({dir_})"
        return f"{esq} {op} {dir_}", prec
