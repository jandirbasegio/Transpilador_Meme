"""Linha de comando:  python -m memepy programa.meme [opções]"""

import argparse
import subprocess
import sys
from pathlib import Path

from . import ErroMeme, Lexer, Parser, preparar_fonte, transpilar
from .arvore import despejar


def ler_arquivo(caminho):
    dados = caminho.read_bytes()
    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Editores antigos no Windows salvam em ANSI (cp1252).
        return dados.decode("cp1252", errors="replace")


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(
        prog="python -m memepy",
        description="Transpilador da linguagem memética (Felipe ... Smith) para Python.",
    )
    ap.add_argument("arquivo", help="arquivo com o código memético (ex.: programa.meme)")
    ap.add_argument("-o", "--saida", help="arquivo .py de saída (padrão: mesmo nome, com .py)")
    ap.add_argument("-r", "--rodar", action="store_true", help="roda o programa depois de transpilar")
    ap.add_argument("-m", "--mostrar", action="store_true", help="mostra o Python gerado em vez de salvar")
    ap.add_argument("--tokens", action="store_true", help="mostra só os tokens (análise léxica)")
    ap.add_argument("--arvore", action="store_true", help="mostra só a árvore sintática (AST)")
    args = ap.parse_args(argv)

    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
        return 2
    fonte = preparar_fonte(ler_arquivo(caminho))

    try:
        if args.tokens:
            for tok in Lexer(fonte).tokens():
                print(tok)
            return 0
        if args.arvore:
            print(despejar(Parser(Lexer(fonte).tokens()).programa()))
            return 0
        codigo, avisos = transpilar(fonte, caminho.name)
    except ErroMeme as erro:
        print(erro.formatar(fonte, str(caminho)), file=sys.stderr)
        return 1

    for aviso in avisos:
        print(aviso.formatar(fonte, str(caminho)), file=sys.stderr)

    if args.mostrar:
        print(codigo, end="")
        if not args.rodar:
            return 0
        comando = [sys.executable, "-c", codigo]
    else:
        saida = Path(args.saida) if args.saida else caminho.with_suffix(".py")
        if saida.resolve() == caminho.resolve():
            print("O arquivo de saída não pode ser o próprio código memético.", file=sys.stderr)
            return 2
        saida.write_text(codigo, encoding="utf-8")
        print(f"Transpilado: {caminho} -> {saida}", file=sys.stderr)
        comando = [sys.executable, str(saida)]

    if args.rodar:
        print("-" * 40, file=sys.stderr)
        try:
            return subprocess.run(comando).returncode
        except KeyboardInterrupt:
            return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
