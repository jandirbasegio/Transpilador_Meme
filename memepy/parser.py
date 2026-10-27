"""Análise sintática: parser descendente recursivo que monta a árvore (AST).

Gramática (resumida):

    programa    := Felipe item* Smith
    item        := funcao | comando
    funcao      := Samu [tipo] ID '(' [tipo ID {',' tipo ID}] ')' bloco
    tipo        := TIPO+                          (ex.: Guarapari Red_bull)
    bloco       := '{' comando* '}'
    comando     := bloco | declaracao ';' | se | enquanto | para
                 | Mata_papai ';' | MeuBraço ';' | Ce_é_mo_playboy [expr] ';'
                 | vo_fica_pelado_aqui '(' [args] ')' ';'
                 | Eu_Tenho_Quantos_Anos_Gente? '(' [TEXTO] [ID {',' ID}] ')' ';'
                 | Tô_No_SAMU ID '(' [args] ')' ';'
                 | ID ('=' | '+=' | ...) expr ';' | ID ('++' | '--') ';' | ';'
    se          := MinhaArte '(' expr ')' corpo
                   { Faz_Isso_Comigo_Não_Velho '(' expr ')' corpo } [Romero_Britto corpo]
    enquanto    := Quebro_VéiVai_Me_Dar_Injeção '(' expr ')' corpo
    para        := VocêÉDeLá '(' [decl | atrib] ';' [expr] ';' [passo] ')' corpo

    expr        := ou
    ou          := e { '||' e }
    e           := igualdade { '&&' igualdade }
    igualdade   := relacional { ('==' | '!=') relacional }
    relacional  := soma { ('<' | '<=' | '>' | '>=') soma }
    soma        := produto { ('+' | '-') produto }
    produto     := unaria { ('*' | '/' | '%') unaria }
    unaria      := ('!' | '-' | '+') unaria | '(' tipo ')' unaria | primaria
    primaria    := número | caractere | texto | ID | '(' expr ')'
                 | Tô_No_SAMU ID '(' [args] ')' | Eu_Tenho_Quantos_Anos_Gente? '(' [TEXTO] ')'
"""

from .arvore import (
    Atribuicao, Binaria, Bloco, Caractere, Chamada, ComandoChamada, Continua, Conversao,
    Declaracao, Declarador, Enquanto, Funcao, Imprima, Incremento, Leia, LeiaExpr, Numero,
    Para, Parametro, Pare, Programa, Retorne, Se, Texto, TipoC, Unaria, Variavel, Vazio,
)
from .erros import ErroSintatico
from .lexer import NOME_DO_TOKEN

DESCRICOES = {
    "ID": "um nome",
    "TIPO": "um tipo (Red_bull, Jarbas, Porra...)",
    "NUM_INT": "um número",
    "NUM_REAL": "um número",
    "CHAR": "um caractere",
    "TEXTO": "um texto",
    "EOF": "o fim do arquivo",
}

# Quem vem de C tende a escrever as palavras originais; damos a dica certa.
COLA_DE_C = {
    "int": "Red_bull", "float": "Jarbas", "char": "Porra", "double": "Katrina",
    "unsigned": "Guarapari", "short": "Búzios", "long": "Caralho",
    "if": "MinhaArte", "else": "Romero_Britto", "elif": "Faz_Isso_Comigo_Não_Velho",
    "while": "Quebro_VéiVai_Me_Dar_Injeção", "for": "VocêÉDeLá",
    "return": "Ce_é_mo_playboy", "break": "Mata_papai", "continue": "MeuBraço",
    "print": "vo_fica_pelado_aqui", "printf": "vo_fica_pelado_aqui", "puts": "vo_fica_pelado_aqui",
    "scanf": "Eu_Tenho_Quantos_Anos_Gente?", "input": "Eu_Tenho_Quantos_Anos_Gente?",
    "def": "Samu", "void": "Samu (sem tipo)",
}

OPS_ATRIBUICAO = ("=", "+=", "-=", "*=", "/=", "%=")


def descrever(tipo):
    if tipo in NOME_DO_TOKEN:
        return NOME_DO_TOKEN[tipo]
    return DESCRICOES.get(tipo, f"'{tipo}'")


def descrever_token(tok):
    if tok.tipo == "EOF":
        return "o fim do arquivo"
    return f"'{tok.texto}'"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    # ------------------------------------------------------------ utilidades

    @property
    def atual(self):
        return self.tokens[self.i]

    def _eh(self, *tipos):
        return self.atual.tipo in tipos

    def _consumir(self):
        tok = self.atual
        if tok.tipo != "EOF":
            self.i += 1
        return tok

    def _aceitar(self, tipo):
        return self._consumir() if self._eh(tipo) else None

    def _erro(self, mensagem, tok=None):
        tok = tok or self.atual
        return ErroSintatico(mensagem, tok.linha, tok.coluna)

    def _esperar(self, tipo, o_que=None):
        if self._eh(tipo):
            return self._consumir()
        o_que = o_que or descrever(tipo)
        raise self._erro(f"esperava {o_que}, mas encontrei {descrever_token(self.atual)}")

    def _fim_comando(self):
        if self._eh(";"):
            return self._consumir()
        # Aponta logo depois do último token, que é onde o ';' faltou.
        anterior = self.tokens[self.i - 1]
        raise ErroSintatico(
            f"faltou ';' no fim do comando (encontrei {descrever_token(self.atual)})",
            anterior.linha,
            anterior.coluna + len(anterior.texto),
        )

    @staticmethod
    def _pos(tok):
        return {"linha": tok.linha, "coluna": tok.coluna}

    # ------------------------------------------------------------ programa

    def programa(self):
        if not self._eh("INICIO"):
            raise self._erro(f"todo programa começa com Felipe, mas encontrei {descrever_token(self.atual)}")
        inicio = self._consumir()
        itens = []
        while not self._eh("FIM"):
            if self._eh("EOF"):
                raise self._erro("o programa acabou sem o Smith (fim do código)")
            if self._eh("FUNCAO"):
                itens.append(self.funcao())
            else:
                itens.append(self.comando())
        self._consumir()
        if not self._eh("EOF"):
            raise self._erro(f"nada pode vir depois do Smith, mas encontrei {descrever_token(self.atual)}")
        return Programa(itens, **self._pos(inicio))

    def tipo(self):
        primeiro = self.atual
        toks = []
        while self._eh("TIPO"):
            toks.append(self._consumir())
        if not toks:
            raise self._erro(f"esperava um tipo (Red_bull, Jarbas, Porra...), mas encontrei {descrever_token(primeiro)}")
        partes = [t.valor for t in toks]
        self._validar_tipo(partes, toks, primeiro)
        return TipoC(partes, **self._pos(primeiro))

    def _validar_tipo(self, partes, toks, primeiro):
        bases = [p for p in partes if p in ("INT", "FLOAT", "CHAR", "DOUBLE")]
        uns, sho, lon = partes.count("UNSIGNED"), partes.count("SHORT"), partes.count("LONG")
        base = bases[0] if bases else "INT"
        invalido = (
            len(bases) > 1
            or uns > 1 or sho > 1 or lon > 2
            or (sho and lon)
            or (base == "FLOAT" and (uns or sho or lon))
            or (base == "DOUBLE" and (uns or sho or lon > 1))
            or (base == "CHAR" and (sho or lon))
        )
        if invalido:
            escrito = " ".join(t.texto for t in toks)
            em_c = " ".join(p.lower() for p in partes)
            raise self._erro(f"o tipo '{escrito}' não existe (seria '{em_c}' em C)", primeiro)

    def funcao(self):
        inicio = self._consumir()  # Samu
        retorno = self.tipo() if self._eh("TIPO") else None
        nome = self._esperar("ID", "o nome da função depois de Samu")
        self._esperar("(", f"'(' depois do nome da função '{nome.valor}'")
        params = []
        if not self._eh(")"):
            while True:
                if not self._eh("TIPO"):
                    raise self._erro(
                        f"cada parâmetro precisa de um tipo (ex.: Red_bull x), mas encontrei {descrever_token(self.atual)}"
                    )
                pos = self._pos(self.atual)
                tipo = self.tipo()
                pnome = self._esperar("ID", "o nome do parâmetro")
                params.append(Parametro(tipo, pnome.valor, **pos))
                if not self._aceitar(","):
                    break
        self._esperar(")", "')' para fechar os parâmetros")
        if not self._eh("{"):
            raise self._erro(f"o corpo da função precisa estar entre {{ }}, mas encontrei {descrever_token(self.atual)}")
        corpo = self.bloco()
        return Funcao(retorno, nome.valor, params, corpo, **self._pos(inicio))

    # ------------------------------------------------------------ comandos

    def bloco(self):
        abre = self._esperar("{")
        comandos = []
        while not self._eh("}"):
            if self._eh("EOF", "FIM"):
                raise self._erro(
                    f"faltou '}}' para fechar o bloco aberto na linha {abre.linha} "
                    f"(encontrei {descrever_token(self.atual)})"
                )
            comandos.append(self.comando())
        self._consumir()
        return Bloco(comandos, **self._pos(abre))

    def _corpo(self):
        """Corpo de if/while/for: um bloco { } ou um único comando."""
        cmd = self.comando()
        if isinstance(cmd, Bloco):
            return cmd
        return Bloco([cmd], linha=cmd.linha, coluna=cmd.coluna)

    def comando(self):
        tok = self.atual
        t = tok.tipo
        pos = self._pos(tok)
        if t == "{":
            return self.bloco()
        if t == "TIPO":
            decl = self.declaracao()
            self._fim_comando()
            return decl
        if t == "IF":
            return self.se()
        if t == "WHILE":
            return self.enquanto()
        if t == "FOR":
            return self.para()
        if t == "BREAK":
            self._consumir()
            self._fim_comando()
            return Pare(**pos)
        if t == "CONTINUE":
            self._consumir()
            self._fim_comando()
            return Continua(**pos)
        if t == "RETURN":
            self._consumir()
            valor = None if self._eh(";") else self.expressao()
            self._fim_comando()
            return Retorne(valor, **pos)
        if t == "PRINT":
            return self.imprima()
        if t == "LEIA":
            return self.leia()
        if t == "CHAMADA":
            chamada = self.chamada()
            self._fim_comando()
            return ComandoChamada(chamada, **pos)
        if t == "ID":
            cmd = self.atribuicao()
            self._fim_comando()
            return cmd
        if t in ("++", "--"):
            cmd = self._pre_incremento()
            self._fim_comando()
            return cmd
        if t == ";":
            self._consumir()
            return Vazio(**pos)
        if t == "ELIF":
            raise self._erro("Faz_Isso_Comigo_Não_Velho (else if) sem um MinhaArte (if) antes")
        if t == "ELSE":
            raise self._erro("Romero_Britto (else) sem um MinhaArte (if) antes")
        if t == "FUNCAO":
            raise self._erro("Samu (função) só pode ser declarado fora de outros blocos, direto no programa")
        if t == "INICIO":
            raise self._erro("Felipe só aparece uma vez, no começo do programa")
        raise self._erro(f"esperava um comando, mas encontrei {descrever_token(tok)}")

    def declaracao(self):
        tipo = self.tipo()
        itens = []
        while True:
            nome = self._esperar("ID", "o nome da variável depois do tipo")
            if self._eh("("):
                raise self._erro(
                    f"pra declarar a função '{nome.valor}' use Samu, ex.: Samu Red_bull {nome.valor}(...) {{ }}", nome
                )
            valor = self.expressao() if self._aceitar("=") else None
            itens.append(Declarador(nome.valor, valor, **self._pos(nome)))
            if not self._aceitar(","):
                break
        return Declaracao(tipo, itens, linha=tipo.linha, coluna=tipo.coluna)

    def atribuicao(self):
        nome = self._consumir()
        pos = self._pos(nome)
        t = self.atual.tipo
        if t in OPS_ATRIBUICAO:
            self._consumir()
            return Atribuicao(nome.valor, t, self.expressao(), **pos)
        if t in ("++", "--"):
            self._consumir()
            return Incremento(nome.valor, t, **pos)
        if nome.valor in COLA_DE_C:
            raise self._erro(f"aqui não é C! Em vez de '{nome.valor}' use '{COLA_DE_C[nome.valor]}'", nome)
        if t == "(":
            raise self._erro(f"pra chamar a função '{nome.valor}' use Tô_No_SAMU {nome.valor}(...)", nome)
        if t == "ID":
            raise self._erro(
                f"'{nome.valor}' não é um tipo. Os tipos são: Red_bull (int), Jarbas (float), "
                "Katrina (double), Porra (char), Guarapari (unsigned), Búzios (short), Caralho (long)",
                nome,
            )
        raise self._erro(f"esperava '=', '++' ou '--' depois de '{nome.valor}', mas encontrei {descrever_token(self.atual)}")

    def _pre_incremento(self):
        op = self._consumir()
        nome = self._esperar("ID", f"o nome de uma variável depois de '{op.tipo}'")
        return Incremento(nome.valor, op.tipo, **self._pos(op))

    def _condicao(self):
        palavra = self.tokens[self.i - 1]
        self._esperar("(", f"'(' depois de {palavra.texto}")
        cond = self.expressao()
        if self._eh("="):
            raise self._erro("'=' guarda valor; pra comparar use '=='")
        self._esperar(")", "')' para fechar a condição")
        return cond

    def se(self):
        inicio = self._consumir()  # MinhaArte ou Faz_Isso_Comigo_Não_Velho
        cond = self._condicao()
        entao = self._corpo()
        senao = None
        if self._eh("ELIF"):
            senao = self.se()
        elif self._aceitar("ELSE"):
            senao = self.se() if self._eh("IF") else self._corpo()
        return Se(cond, entao, senao, **self._pos(inicio))

    def enquanto(self):
        inicio = self._consumir()
        cond = self._condicao()
        return Enquanto(cond, self._corpo(), **self._pos(inicio))

    def para(self):
        inicio = self._consumir()
        self._esperar("(", "'(' depois de VocêÉDeLá")
        ini = None
        if self._eh("TIPO"):
            ini = self.declaracao()
        elif self._eh("ID"):
            ini = self.atribuicao()
        elif not self._eh(";"):
            raise self._erro(
                f"o VocêÉDeLá começa com uma declaração ou atribuição (ex.: Red_bull i = 0), "
                f"mas encontrei {descrever_token(self.atual)}"
            )
        self._esperar(";", "';' depois da inicialização do VocêÉDeLá")
        cond = None if self._eh(";") else self.expressao()
        if self._eh("="):
            raise self._erro("'=' guarda valor; pra comparar use '=='")
        self._esperar(";", "';' depois da condição do VocêÉDeLá")
        passo = None
        if self._eh("ID"):
            passo = self.atribuicao()
        elif self._eh("++", "--"):
            passo = self._pre_incremento()
        elif self._eh("CHAMADA"):
            pos = self._pos(self.atual)
            passo = ComandoChamada(self.chamada(), **pos)
        elif not self._eh(")"):
            raise self._erro(f"esperava o passo do VocêÉDeLá (ex.: i++), mas encontrei {descrever_token(self.atual)}")
        self._esperar(")", "')' para fechar o VocêÉDeLá")
        return Para(ini, cond, passo, self._corpo(), **self._pos(inicio))

    def _argumentos(self):
        args = []
        if not self._eh(")"):
            args.append(self.expressao())
            while self._aceitar(","):
                args.append(self.expressao())
        self._esperar(")", "')' ou ',' entre os argumentos")
        return args

    def imprima(self):
        inicio = self._consumir()
        self._esperar("(", "'(' depois de vo_fica_pelado_aqui")
        args = self._argumentos()
        self._fim_comando()
        return Imprima(args, **self._pos(inicio))

    def leia(self):
        inicio = self._consumir()
        self._esperar("(", f"'(' depois de {inicio.texto}")
        prompt = None
        if self._eh("TEXTO"):
            prompt = self._consumir().valor
            if not self._eh(")"):
                self._esperar(",", "',' depois da mensagem")
        alvos = []
        if not self._eh(")"):
            while True:
                nome = self._esperar("ID", "o nome da variável que vai guardar o que for lido")
                alvos.append(Variavel(nome.valor, **self._pos(nome)))
                if not self._aceitar(","):
                    break
        self._esperar(")", "')' para fechar a leitura")
        self._fim_comando()
        return Leia(prompt, alvos, **self._pos(inicio))

    def chamada(self):
        inicio = self._consumir()  # Tô_No_SAMU
        nome = self._esperar("ID", "o nome da função depois de Tô_No_SAMU")
        self._esperar("(", f"'(' depois de '{nome.valor}'")
        return Chamada(nome.valor, self._argumentos(), **self._pos(inicio))

    # ------------------------------------------------------------ expressões

    def expressao(self):
        return self._ou()

    def _binaria(self, proximo, ops):
        esq = proximo()
        while self.atual.tipo in ops:
            op = self._consumir()
            esq = Binaria(op.tipo, esq, proximo(), **self._pos(op))
        return esq

    def _ou(self):
        return self._binaria(self._e, ("||",))

    def _e(self):
        return self._binaria(self._igualdade, ("&&",))

    def _igualdade(self):
        return self._binaria(self._relacional, ("==", "!="))

    def _relacional(self):
        return self._binaria(self._soma, ("<", "<=", ">", ">="))

    def _soma(self):
        return self._binaria(self._produto, ("+", "-"))

    def _produto(self):
        return self._binaria(self._unaria, ("*", "/", "%"))

    def _unaria(self):
        if self._eh("!", "-", "+"):
            op = self._consumir()
            return Unaria(op.tipo, self._unaria(), **self._pos(op))
        if self._eh("++", "--"):
            raise self._erro(f"'{self.atual.tipo}' só pode ser usado como comando sozinho (ex.: x++;)")
        return self._primaria()

    def _primaria(self):
        tok = self.atual
        t = tok.tipo
        pos = self._pos(tok)
        if t == "NUM_INT":
            self._consumir()
            return Numero(tok.valor, False, **pos)
        if t == "NUM_REAL":
            self._consumir()
            return Numero(tok.valor, True, **pos)
        if t == "CHAR":
            self._consumir()
            return Caractere(tok.valor, **pos)
        if t == "TEXTO":
            self._consumir()
            return Texto(tok.valor, **pos)
        if t == "CHAMADA":
            return self.chamada()
        if t == "LEIA":
            self._consumir()
            self._esperar("(", f"'(' depois de {tok.texto}")
            prompt = self._consumir().valor if self._eh("TEXTO") else None
            if self._eh("ID"):
                raise self._erro(
                    "dentro de uma conta o Eu_Tenho_Quantos_Anos_Gente? não recebe variável; "
                    "use x = Eu_Tenho_Quantos_Anos_Gente?(); ou Eu_Tenho_Quantos_Anos_Gente?(x);"
                )
            self._esperar(")", "')' para fechar a leitura")
            return LeiaExpr(prompt, **pos)
        if t == "ID":
            self._consumir()
            if self._eh("("):
                if tok.valor in COLA_DE_C:
                    raise self._erro(f"aqui não é C! Em vez de '{tok.valor}' use '{COLA_DE_C[tok.valor]}'", tok)
                raise self._erro(f"pra chamar a função '{tok.valor}' use Tô_No_SAMU {tok.valor}(...)", tok)
            if self._eh("++", "--"):
                raise self._erro(f"'{self.atual.tipo}' só pode ser usado como comando sozinho (ex.: x++;)")
            return Variavel(tok.valor, **pos)
        if t == "(":
            self._consumir()
            if self._eh("TIPO"):  # conversão: (Red_bull) x
                tipo = self.tipo()
                self._esperar(")", "')' depois do tipo da conversão")
                return Conversao(tipo, self._unaria(), **pos)
            expr = self.expressao()
            self._esperar(")", "')' para fechar o parêntese")
            return expr
        if t == "TIPO":
            raise self._erro(
                f"'{tok.texto}' é um tipo e não pode aparecer no meio de uma conta "
                f"(pra converter use ({tok.texto}) valor)"
            )
        raise self._erro(f"esperava um valor (número, variável, texto...), mas encontrei {descrever_token(tok)}")

