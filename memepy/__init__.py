"""memepy: transpilador da linguagem memética (Felipe ... Smith) para Python.

Fases:  texto --lexer--> tokens --parser--> árvore --semântico--> árvore anotada --gerador--> Python
"""

from .erros import Aviso, ErroLexico, ErroMeme, ErroSemantico, ErroSintatico
from .gerador import Gerador
from .lexer import Lexer, preparar_fonte
from .parser import Parser
from .semantico import Analisador

__version__ = "1.0.0"


def transpilar(fonte, nome_arquivo=None):
    """Recebe o código memético e devolve (codigo_python, lista_de_avisos).

    Levanta ErroLexico, ErroSintatico ou ErroSemantico se o programa tiver erro.
    """
    fonte = preparar_fonte(fonte)
    tokens = Lexer(fonte).tokens()
    programa = Parser(tokens).programa()
    avisos = Analisador().analisar(programa)
    codigo = Gerador().gerar(programa, nome_arquivo)
    return codigo, avisos


__all__ = [
    "transpilar", "preparar_fonte", "Lexer", "Parser", "Analisador", "Gerador",
    "ErroMeme", "ErroLexico", "ErroSintatico", "ErroSemantico", "Aviso",
]
