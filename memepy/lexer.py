"""Análise léxica: transforma o texto do programa em uma lista de tokens."""

import math
import unicodedata
from dataclasses import dataclass

from .erros import ErroLexico

# Palavra memética -> categoria do token
PALAVRAS_CHAVE = {
    "Felipe": "INICIO",
    "Smith": "FIM",
    "MinhaArte": "IF",
    "Romero_Britto": "ELSE",
    "Faz_Isso_Comigo_Não_Velho": "ELIF",
    "Quebro_VéiVai_Me_Dar_Injeção": "WHILE",
    "VocêÉDeLá": "FOR",
    "Samu": "FUNCAO",
    "Tô_No_SAMU": "CHAMADA",
    "Eu_Tenho_Quantos_Anos_Gente?": "LEIA",
    "MeuBraço": "CONTINUE",
    "Mata_papai": "BREAK",
    "Ce_é_mo_playboy": "RETURN",
    "vo_fica_pelado_aqui": "PRINT",
}

# Palavra memética -> tipo de C que ela representa (token "TIPO")
TIPOS = {
    "Jarbas": "FLOAT",
    "Red_bull": "INT",
    "Porra": "CHAR",
    "Katrina": "DOUBLE",
    "Guarapari": "UNSIGNED",
    "Búzios": "SHORT",
    "Caralho": "LONG",
}

# Caminho inverso, usado nas mensagens de erro
NOME_DO_TOKEN = {v: k for k, v in PALAVRAS_CHAVE.items()}
NOME_DO_TIPO = {v: k for k, v in TIPOS.items()}


def sem_acento(texto):
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


# As palavras-chave são reconhecidas com ou sem acento (Tô_No_SAMU ou To_No_SAMU).
_BUSCA_CHAVE = {sem_acento(k.rstrip("?")): v for k, v in PALAVRAS_CHAVE.items()}
_BUSCA_TIPO = {sem_acento(k): v for k, v in TIPOS.items()}

OPERADORES_DUPLOS = ("==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=", "%=")
OPERADORES_SIMPLES = "+-*/%=<>!(){},;"
DIGITOS = "0123456789"
ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}


def preparar_fonte(texto):
    """Remove BOM, padroniza quebras de linha e acentos (é composto vs. e + ´)."""
    if texto.startswith("﻿"):
        texto = texto[1:]
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", texto)


@dataclass
class Token:
    tipo: str  # categoria: ID, NUM_INT, NUM_REAL, CHAR, TEXTO, TIPO, palavra-chave, operador ou EOF
    valor: object  # valor já interpretado (número, texto sem aspas, nome do tipo...)
    texto: str  # como apareceu no código
    linha: int
    coluna: int

    def __str__(self):
        return f"{self.linha:>4}:{self.coluna:<4} {self.tipo:<10} {self.texto}"


def _eh_digito(c):
    return c != "" and c in DIGITOS


def _continua_nome(c):
    return c != "" and (c.isalnum() or c == "_" or unicodedata.category(c).startswith("M"))


class Lexer:
    def __init__(self, fonte):
        self.fonte = fonte
        self.pos = 0
        self.linha = 1
        self.coluna = 1

    def _atual(self, desloc=0):
        i = self.pos + desloc
        return self.fonte[i] if i < len(self.fonte) else ""

    def _avancar(self, n=1):
        for _ in range(n):
            if self.pos >= len(self.fonte):
                return
            if self.fonte[self.pos] == "\n":
                self.linha += 1
                self.coluna = 1
            else:
                self.coluna += 1
            self.pos += 1

    def tokens(self):
        lista = []
        while True:
            self._pular_espacos_e_comentarios()
            if self.pos >= len(self.fonte):
                lista.append(Token("EOF", None, "", self.linha, self.coluna))
                return lista
            lista.append(self._proximo())

    def _pular_espacos_e_comentarios(self):
        while True:
            c = self._atual()
            if c.isspace():
                self._avancar()
            elif c == "/" and self._atual(1) == "/":
                while self._atual() not in ("", "\n"):
                    self._avancar()
            elif c == "/" and self._atual(1) == "*":
                linha, coluna = self.linha, self.coluna
                self._avancar(2)
                while not (self._atual() == "*" and self._atual(1) == "/"):
                    if self._atual() == "":
                        raise ErroLexico("comentário /* aberto e nunca fechado com */", linha, coluna)
                    self._avancar()
                self._avancar(2)
            else:
                return

    def _proximo(self):
        c = self._atual()
        linha, coluna = self.linha, self.coluna
        if c.isalpha() or c == "_":
            return self._palavra(linha, coluna)
        if _eh_digito(c):
            return self._numero(linha, coluna)
        if c == '"':
            return self._texto(linha, coluna)
        if c == "'":
            return self._caractere(linha, coluna)
        dois = self.fonte[self.pos:self.pos + 2]
        if dois in OPERADORES_DUPLOS:
            self._avancar(2)
            return Token(dois, dois, dois, linha, coluna)
        if c in OPERADORES_SIMPLES:
            self._avancar()
            return Token(c, c, c, linha, coluna)
        if c in "&|":
            raise ErroLexico(f"'{c}' sozinho não existe; você quis dizer '{c * 2}'?", linha, coluna)
        raise ErroLexico(f"caractere inesperado {c!r}", linha, coluna)

    def _palavra(self, linha, coluna):
        inicio = self.pos
        while _continua_nome(self._atual()):
            self._avancar()
        palavra = self.fonte[inicio:self.pos]
        chave = sem_acento(palavra)
        if chave in _BUSCA_CHAVE:
            tipo = _BUSCA_CHAVE[chave]
            if tipo == "LEIA" and self._atual() == "?":
                self._avancar()
                palavra += "?"
            return Token(tipo, palavra, palavra, linha, coluna)
        if chave in _BUSCA_TIPO:
            return Token("TIPO", _BUSCA_TIPO[chave], palavra, linha, coluna)
        if not palavra.isidentifier():
            raise ErroLexico(f"nome inválido {palavra!r}", linha, coluna)
        return Token("ID", palavra, palavra, linha, coluna)

    def _numero(self, linha, coluna):
        inicio = self.pos
        real = False
        while _eh_digito(self._atual()):
            self._avancar()
        if self._atual() == "." and _eh_digito(self._atual(1)):
            real = True
            self._avancar()
            while _eh_digito(self._atual()):
                self._avancar()
        if self._atual() in ("e", "E") and (
            _eh_digito(self._atual(1)) or (self._atual(1) in ("+", "-") and _eh_digito(self._atual(2)))
        ):
            real = True
            self._avancar(2)
            while _eh_digito(self._atual()):
                self._avancar()
        texto = self.fonte[inicio:self.pos]
        if _continua_nome(self._atual()) or self._atual() == ".":
            raise ErroLexico(f"número mal formado '{texto}{self._atual()}'", linha, coluna)
        if real:
            valor = float(texto)
            if math.isinf(valor):
                raise ErroLexico(f"número grande demais: {texto}", linha, coluna)
            return Token("NUM_REAL", valor, texto, linha, coluna)
        return Token("NUM_INT", int(texto), texto, linha, coluna)

    def _escape(self):
        linha, coluna = self.linha, self.coluna
        self._avancar()  # a barra
        c = self._atual()
        if c in ("", "\n"):
            raise ErroLexico("barra invertida no fim do texto", linha, coluna)
        if c not in ESCAPES:
            raise ErroLexico(f"sequência de escape desconhecida '\\{c}'", linha, coluna)
        self._avancar()
        return ESCAPES[c]

    def _texto(self, linha, coluna):
        inicio = self.pos
        self._avancar()  # aspas de abertura
        partes = []
        while True:
            c = self._atual()
            if c in ("", "\n"):
                raise ErroLexico("texto aberto com \" e nunca fechado", linha, coluna)
            if c == '"':
                self._avancar()
                break
            if c == "\\":
                partes.append(self._escape())
            else:
                partes.append(c)
                self._avancar()
        return Token("TEXTO", "".join(partes), self.fonte[inicio:self.pos], linha, coluna)

    def _caractere(self, linha, coluna):
        inicio = self.pos
        self._avancar()  # aspas simples de abertura
        c = self._atual()
        if c == "'":
            raise ErroLexico("caractere vazio ''", linha, coluna)
        if c in ("", "\n"):
            raise ErroLexico("caractere aberto com ' e nunca fechado", linha, coluna)
        if c == "\\":
            valor = self._escape()
        else:
            valor = c
            self._avancar()
        if self._atual() != "'":
            raise ErroLexico(
                "entre aspas simples só cabe um caractere (Porra); para texto use aspas duplas", linha, coluna
            )
        self._avancar()
        return Token("CHAR", valor, self.fonte[inicio:self.pos], linha, coluna)
