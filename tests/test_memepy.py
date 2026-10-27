"""Testes do transpilador. Rode com:  python -m unittest -v"""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from memepy import ErroLexico, ErroSemantico, ErroSintatico, transpilar

EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"


def gerar(corpo, envolver=True):
    fonte = f"Felipe\n{corpo}\nSmith\n" if envolver else corpo
    return transpilar(fonte)[0]


def rodar(corpo, entrada="", envolver=True):
    """Transpila, executa o Python gerado e devolve o que foi impresso."""
    codigo = gerar(corpo, envolver)
    saida = io.StringIO()
    with redirect_stdout(saida), mock.patch("sys.stdin", io.StringIO(entrada)):
        exec(compile(codigo, "<gerado>", "exec"), {"__name__": "__main__"})
    return saida.getvalue()


class TestBasico(unittest.TestCase):
    def test_ola_mundo(self):
        self.assertEqual(rodar('vo_fica_pelado_aqui("Olá, mundo!");'), "Olá, mundo!\n")

    def test_programa_vazio(self):
        self.assertEqual(rodar(""), "")

    def test_varios_argumentos_no_print(self):
        self.assertEqual(rodar('Red_bull x = 2; vo_fica_pelado_aqui("x =", x, x * 3);'), "x = 2 6\n")

    def test_print_vazio_pula_linha(self):
        self.assertEqual(rodar("vo_fica_pelado_aqui();"), "\n")

    def test_comentarios(self):
        self.assertEqual(rodar("// linha\n/* bloco\n longo */ vo_fica_pelado_aqui(1); // fim"), "1\n")

    def test_escapes(self):
        self.assertEqual(rodar(r'vo_fica_pelado_aqui("a\tb\n\"c\"");'), 'a\tb\n"c"\n')

    def test_palavras_sem_acento(self):
        self.assertEqual(
            rodar("Samu Red_bull dobro(Red_bull x) { Ce_e_mo_playboy x * 2; }"
                  "Buzios Red_bull y = To_No_SAMU dobro(21); vo_fica_pelado_aqui(y);"),
            "42\n",
        )


class TestTipos(unittest.TestCase):
    def test_divisao_inteira_como_em_c(self):
        self.assertEqual(rodar("Red_bull a = 7; vo_fica_pelado_aqui(a / 2);"), "3\n")

    def test_divisao_real(self):
        self.assertEqual(rodar("Jarbas a = 7; vo_fica_pelado_aqui(a / 2);"), "3.5\n")

    def test_divide_e_atribui_inteiro(self):
        codigo = gerar("Red_bull a = 9; a /= 2;")
        self.assertIn("a //= 2", codigo)

    def test_real_em_inteiro_trunca(self):
        self.assertEqual(rodar("Red_bull a = 3.9; vo_fica_pelado_aqui(a);"), "3\n")

    def test_soma_real_em_variavel_inteira(self):
        self.assertEqual(rodar("Red_bull a = 1; a += 1.5; vo_fica_pelado_aqui(a);"), "2\n")

    def test_inteiro_em_real(self):
        codigo = gerar("Jarbas x = 3; Katrina y = -2;")
        self.assertIn("x: float = 3.0", codigo)
        self.assertIn("y: float = -2.0", codigo)

    def test_char_em_conta(self):
        self.assertEqual(rodar("Porra c = 'a'; c++; vo_fica_pelado_aqui(c, c + 1);"), "b 99\n")

    def test_char_comparado_com_numero(self):
        self.assertEqual(rodar("Porra c = 'A'; MinhaArte (c == 65) { vo_fica_pelado_aqui(1); }"), "1\n")

    def test_conversao_explicita(self):
        self.assertEqual(rodar("vo_fica_pelado_aqui((Red_bull) 2.9, (Porra) 66, (Jarbas) 1);"), "2 B 1.0\n")

    def test_concatenar_textos(self):
        self.assertEqual(rodar('Porra nome = "Felipe"; vo_fica_pelado_aqui("Oi, " + nome);'), "Oi, Felipe\n")

    def test_modificadores_validos(self):
        gerar("Guarapari Red_bull a; Guarapari b; Caralho Caralho c; Caralho Katrina d; Búzios Red_bull e;")

    def test_modificadores_invalidos(self):
        for tipo in ("Guarapari Jarbas", "Búzios Caralho", "Red_bull Jarbas", "Caralho Porra"):
            with self.subTest(tipo=tipo), self.assertRaises(ErroSintatico):
                gerar(f"{tipo} x;")

    def test_texto_em_variavel_numerica(self):
        with self.assertRaises(ErroSemantico):
            gerar('Red_bull x = "dez";')

    def test_somar_texto_com_numero(self):
        with self.assertRaises(ErroSemantico):
            gerar('vo_fica_pelado_aqui("a" + 1);')


class TestExpressoes(unittest.TestCase):
    def test_precedencia(self):
        self.assertEqual(rodar("vo_fica_pelado_aqui(2 + 3 * 4, (2 + 3) * 4, 10 - 4 - 3);"), "14 20 3\n")

    def test_comparacao_nao_encadeia(self):
        # Em C, 3 > 2 > 1 é (3 > 2) > 1 → 1 > 1 → 0. Em Python sem parênteses daria True.
        self.assertEqual(rodar("vo_fica_pelado_aqui(3 > 2 > 1);"), "0\n")

    def test_not_com_comparacao(self):
        # !a == b em C é (!a) == b
        self.assertEqual(rodar("Red_bull a = 0; Red_bull b = 1; vo_fica_pelado_aqui(!a == b);"), "1\n")

    def test_logicos_viram_0_ou_1(self):
        self.assertEqual(rodar("Red_bull a = 5; Red_bull b = 7; Red_bull r = a && b; vo_fica_pelado_aqui(r, a || 0);"),
                         "1 1\n")

    def test_logicos_na_condicao_ficam_limpos(self):
        codigo = gerar("Red_bull a = 1; MinhaArte (a && !a || a > 0) { }")
        self.assertIn("if a and not a or a > 0:", codigo)

    def test_menos_unario(self):
        self.assertEqual(rodar("Red_bull a = 3; vo_fica_pelado_aqui(-a, - -a, -(a + 1));"), "-3 3 -4\n")


class TestControle(unittest.TestCase):
    def test_if_elif_else(self):
        fonte = """
        VocêÉDeLá (Red_bull i = 0; i < 4; i++) {
            MinhaArte (i == 0) vo_fica_pelado_aqui("zero");
            Faz_Isso_Comigo_Não_Velho (i == 1) { vo_fica_pelado_aqui("um"); }
            Romero_Britto MinhaArte (i == 2) { vo_fica_pelado_aqui("dois"); }
            Romero_Britto { vo_fica_pelado_aqui("muitos"); }
        }
        """
        self.assertEqual(rodar(fonte), "zero\num\ndois\nmuitos\n")

    def test_while_break_continue(self):
        fonte = """
        Red_bull i = 0;
        Quebro_VéiVai_Me_Dar_Injeção (1) {
            i++;
            MinhaArte (i % 2 == 0) { MeuBraço; }
            MinhaArte (i > 7) { Mata_papai; }
            vo_fica_pelado_aqui(i);
        }
        """
        self.assertEqual(rodar(fonte), "1\n3\n5\n7\n")

    def test_for_simples_vira_range(self):
        codigo = gerar("VocêÉDeLá (Red_bull i = 0; i < 10; i++) { vo_fica_pelado_aqui(i); }")
        self.assertIn("for i in range(10):", codigo)

    def test_for_decrescente(self):
        codigo = gerar("VocêÉDeLá (Red_bull i = 10; i >= 0; i -= 2) { vo_fica_pelado_aqui(i); }")
        self.assertIn("for i in range(10, -1, -2):", codigo)
        self.assertEqual(rodar("VocêÉDeLá (Red_bull i = 10; i >= 0; i -= 2) { vo_fica_pelado_aqui(i); }"),
                         "10\n8\n6\n4\n2\n0\n")

    def test_for_que_mexe_no_contador_vira_while(self):
        fonte = "VocêÉDeLá (Red_bull i = 0; i < 10; i++) { vo_fica_pelado_aqui(i); i = i + 3; }"
        self.assertIn("while i < 10:", gerar(fonte))
        self.assertEqual(rodar(fonte), "0\n4\n8\n")

    def test_continue_em_for_executa_o_passo(self):
        # O laço vira while; o MeuBraço precisa rodar o passo antes, senão fica infinito.
        fonte = """
        Red_bull i;
        VocêÉDeLá (i = 0; i < 5; i++) {
            MinhaArte (i == 2) { MeuBraço; }
            vo_fica_pelado_aqui(i);
        }
        """
        self.assertEqual(rodar(fonte), "0\n1\n3\n4\n")

    def test_for_infinito_com_break(self):
        self.assertEqual(rodar("Red_bull n = 0; VocêÉDeLá (;;) { n++; MinhaArte (n == 3) Mata_papai; } vo_fica_pelado_aqui(n);"),
                         "3\n")

    def test_limite_alterado_por_funcao_nao_vira_range(self):
        fonte = """
        Red_bull limite = 3;
        VocêÉDeLá (Red_bull i = 0; i < limite; i++) { Tô_No_SAMU encolhe(); vo_fica_pelado_aqui(i); }
        Samu encolhe() { limite = 1; }
        """
        self.assertNotIn("range", gerar(fonte))
        self.assertEqual(rodar(fonte), "0\n")

    def test_bloco_vazio_vira_pass(self):
        codigo = gerar("Red_bull a = 1; MinhaArte (a) { } Romero_Britto { ; }")
        self.assertIn("pass", codigo)
        compile(codigo, "<teste>", "exec")


class TestFuncoes(unittest.TestCase):
    def test_recursao(self):
        fonte = """
        Samu Red_bull fib(Red_bull n) {
            MinhaArte (n < 2) Ce_é_mo_playboy n;
            Ce_é_mo_playboy Tô_No_SAMU fib(n - 1) + Tô_No_SAMU fib(n - 2);
        }
        vo_fica_pelado_aqui(Tô_No_SAMU fib(10));
        """
        self.assertEqual(rodar(fonte), "55\n")

    def test_chamar_antes_de_declarar(self):
        self.assertEqual(rodar("Tô_No_SAMU oi(); Samu oi() { vo_fica_pelado_aqui(\"oi\"); }"), "oi\n")

    def test_global_alterada_na_funcao(self):
        fonte = "Red_bull total = 0; Samu soma(Red_bull x) { total += x; } Tô_No_SAMU soma(2); Tô_No_SAMU soma(3); vo_fica_pelado_aqui(total);"
        self.assertIn("global total", gerar(fonte))
        self.assertEqual(rodar(fonte), "5\n")

    def test_retorno_convertido(self):
        self.assertEqual(rodar("Samu Red_bull metade(Jarbas x) { Ce_é_mo_playboy x / 2; } vo_fica_pelado_aqui(Tô_No_SAMU metade(5));"),
                         "2\n")

    def test_argumento_convertido(self):
        self.assertEqual(rodar("Samu Jarbas f(Jarbas x) { Ce_é_mo_playboy x / 2; } vo_fica_pelado_aqui(Tô_No_SAMU f(5));"),
                         "2.5\n")

    def test_numero_de_argumentos(self):
        with self.assertRaises(ErroSemantico):
            gerar("Samu f(Red_bull a) { } Tô_No_SAMU f(1, 2);")

    def test_funcao_sem_retorno_em_conta(self):
        with self.assertRaises(ErroSemantico):
            gerar("Samu f() { } Red_bull x = Tô_No_SAMU f();")

    def test_chamada_sem_to_no_samu(self):
        with self.assertRaises(ErroSintatico) as ctx:
            gerar("Samu f() { } f();")
        self.assertIn("Tô_No_SAMU", ctx.exception.mensagem)


class TestEscopo(unittest.TestCase):
    def test_variavel_escondida_ganha_outro_nome(self):
        fonte = """
        Red_bull x = 1;
        MinhaArte (1) {
            Red_bull x = 2;
            vo_fica_pelado_aqui(x);
        }
        vo_fica_pelado_aqui(x);
        """
        self.assertIn("x_2", gerar(fonte))
        self.assertEqual(rodar(fonte), "2\n1\n")

    def test_local_com_nome_de_global(self):
        fonte = """
        Red_bull x = 10;
        Samu mostra() {
            vo_fica_pelado_aqui(x);
            MinhaArte (1) { Red_bull x = 5; vo_fica_pelado_aqui(x); }
        }
        Tô_No_SAMU mostra();
        """
        self.assertEqual(rodar(fonte), "10\n5\n")

    def test_variavel_do_for_some_depois(self):
        with self.assertRaises(ErroSemantico):
            gerar("VocêÉDeLá (Red_bull i = 0; i < 3; i++) { } vo_fica_pelado_aqui(i);")

    def test_nomes_reservados_do_python(self):
        fonte = "Red_bull lambda = 1; Red_bull print = 2; Red_bull None = 3; vo_fica_pelado_aqui(lambda + print + None);"
        self.assertEqual(rodar(fonte), "6\n")

    def test_declarar_duas_vezes(self):
        with self.assertRaises(ErroSemantico):
            gerar("Red_bull a; Jarbas a;")


class TestLeitura(unittest.TestCase):
    def test_ler_em_variaveis(self):
        fonte = 'Red_bull a; Jarbas b; Porra c; Eu_Tenho_Quantos_Anos_Gente?("> ", a, b, c); vo_fica_pelado_aqui(a + 1, b * 2, c);'
        self.assertEqual(rodar(fonte, "41\n1.25\nzé\n"), "> 42 2.5 zé\n")

    def test_ler_como_valor(self):
        self.assertEqual(rodar("Red_bull idade = Eu_Tenho_Quantos_Anos_Gente?(); vo_fica_pelado_aqui(idade * 2);", "21\n"),
                         "42\n")

    def test_ler_sem_interrogacao(self):
        self.assertEqual(rodar("Red_bull a; Eu_Tenho_Quantos_Anos_Gente(a); vo_fica_pelado_aqui(a);", "7\n"), "7\n")

    def test_comparar_leitura_com_numero(self):
        with self.assertRaises(ErroSemantico):
            gerar("MinhaArte (Eu_Tenho_Quantos_Anos_Gente?() > 18) { }")


class TestErros(unittest.TestCase):
    def assertErro(self, classe, fonte, trecho=None, envolver=True):
        with self.assertRaises(classe) as ctx:
            gerar(fonte, envolver)
        if trecho:
            self.assertIn(trecho, ctx.exception.mensagem)
        return ctx.exception

    def test_sem_felipe(self):
        self.assertErro(ErroSintatico, 'vo_fica_pelado_aqui(1); Smith', "Felipe", envolver=False)

    def test_sem_smith(self):
        self.assertErro(ErroSintatico, 'Felipe vo_fica_pelado_aqui(1);', "Smith", envolver=False)

    def test_algo_depois_do_smith(self):
        self.assertErro(ErroSintatico, 'Felipe Smith vo_fica_pelado_aqui(1);', "depois do Smith", envolver=False)

    def test_falta_ponto_e_virgula(self):
        erro = self.assertErro(ErroSintatico, "Red_bull x = 1\nvo_fica_pelado_aqui(x);", "';'")
        self.assertEqual((erro.linha, erro.coluna), (2, 15))

    def test_bloco_sem_fechar(self):
        self.assertErro(ErroSintatico, "MinhaArte (1) { vo_fica_pelado_aqui(1);", "'}'")

    def test_igual_na_condicao(self):
        self.assertErro(ErroSintatico, "Red_bull x; MinhaArte (x = 1) { }", "==")

    def test_variavel_nao_declarada(self):
        self.assertErro(ErroSemantico, "x = 1;", "não foi declarada")

    def test_break_fora_de_laco(self):
        self.assertErro(ErroSemantico, "Mata_papai;", "laço")

    def test_continue_fora_de_laco(self):
        self.assertErro(ErroSemantico, "MeuBraço;", "laço")

    def test_return_fora_de_funcao(self):
        self.assertErro(ErroSemantico, "Ce_é_mo_playboy 1;", "função")

    def test_funcao_dentro_de_bloco(self):
        self.assertErro(ErroSintatico, "MinhaArte (1) { Samu f() { } }", "Samu")

    def test_palavra_de_c(self):
        self.assertErro(ErroSintatico, "int x = 1;", "Red_bull")

    def test_texto_sem_fechar(self):
        self.assertErro(ErroLexico, 'vo_fica_pelado_aqui("oi);')

    def test_char_com_varias_letras(self):
        self.assertErro(ErroLexico, "Porra c = 'ab';", "aspas duplas")

    def test_caractere_estranho(self):
        self.assertErro(ErroLexico, "Red_bull x = 1 @ 2;")

    def test_incremento_no_meio_da_conta(self):
        self.assertErro(ErroSintatico, "Red_bull x; Red_bull y = x++ + 1;", "comando")

    def test_mensagem_formatada_com_setinha(self):
        fonte = "Felipe\nRed_bull x = y;\nSmith"
        with self.assertRaises(ErroSemantico) as ctx:
            transpilar(fonte)
        texto = ctx.exception.formatar(fonte, "teste.meme")
        self.assertIn("teste.meme:2:14", texto)
        self.assertIn("Red_bull x = y;", texto)
        self.assertTrue(texto.endswith("|              ^"))


class TestExemplos(unittest.TestCase):
    CASOS = {
        "ola_mundo": ("", "Olá, mundo!\n"),
        "fatorial": ("5\n", "Digite um número: Fatorial de 5 = 120\n"),
        "fizzbuzz": ("", "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n"),
        "primos": ("", "2 é primo\n3 é primo\n5 é primo\n7 é primo\n11 é primo\nJá deu, chega de primo\n"),
        "calculadora": ("7\n/\n2\n", "Primeiro número: Operação (+ - * /): Segundo número: Resultado: 3.5\n"),
    }

    def test_todos_os_exemplos_transpilam(self):
        arquivos = sorted(EXEMPLOS.glob("*.meme"))
        self.assertTrue(arquivos)
        for arquivo in arquivos:
            with self.subTest(arquivo=arquivo.name):
                codigo = gerar(arquivo.read_text(encoding="utf-8"), envolver=False)
                compile(codigo, arquivo.name, "exec")

    def test_saida_dos_exemplos(self):
        for nome, (entrada, esperado) in self.CASOS.items():
            with self.subTest(exemplo=nome):
                fonte = (EXEMPLOS / f"{nome}.meme").read_text(encoding="utf-8")
                self.assertEqual(rodar(fonte, entrada, envolver=False), esperado)


if __name__ == "__main__":
    unittest.main()
