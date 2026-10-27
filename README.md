# memepy — transpilador da linguagem memética para Python

Uma linguagem no estilo C, com palavras-chave de meme, que é traduzida para Python.

```
Felipe
    Red_bull idade;
    Eu_Tenho_Quantos_Anos_Gente?("Quantos anos você tem? ", idade);
    MinhaArte (idade >= 18) {
        vo_fica_pelado_aqui("Maior de idade");
    } Romero_Britto {
        vo_fica_pelado_aqui("Menor de idade");
    }
Smith
```

vira:

```python
idade: int = 0
idade = int(input("Quantos anos você tem? "))
if idade >= 18:
    print("Maior de idade")
else:
    print("Menor de idade")
```

Precisa de Python 3.10 ou mais novo. Não tem dependências.

## Como usar

Na pasta do projeto (`C:\Compilador`):

| Comando | O que faz |
|---|---|
| `python -m memepy programa.meme` | gera `programa.py` ao lado |
| `python -m memepy programa.meme -r` | gera e já roda |
| `python -m memepy programa.meme -m` | só mostra o Python gerado, sem salvar |
| `python -m memepy programa.meme -o saida.py` | escolhe o nome do arquivo gerado |
| `python -m memepy programa.meme --tokens` | mostra os tokens (análise léxica) |
| `python -m memepy programa.meme --arvore` | mostra a árvore sintática (AST) |

Testes: `python -m unittest -v`

Exemplos prontos em [exemplos/](exemplos/): `ola_mundo`, `fatorial`, `fizzbuzz`, `primos`, `calculadora`, `tipos`.

## Palavras-chave

| Memética | Equivale a | Vira em Python |
|---|---|---|
| `Felipe` | início do código | — |
| `Smith` | fim do código | — |
| `Jarbas` | `float` | `float` |
| `Red_bull` | `int` | `int` |
| `Porra` | `char` | `str` |
| `Katrina` | `double` | `float` |
| `Guarapari` | `unsigned` | `int` |
| `Búzios` | `short` | `int` |
| `Caralho` | `long` | `int` |
| `MinhaArte` | `if` | `if` |
| `Romero_Britto` | `else` | `else` |
| `Faz_Isso_Comigo_Não_Velho` | `else if` | `elif` |
| `Quebro_VéiVai_Me_Dar_Injeção` | `while` | `while` |
| `VocêÉDeLá` | `for` | `for ... in range(...)` ou `while` |
| `Samu` | declarar função | `def` |
| `Tô_No_SAMU` | chamar função | `nome(...)` |
| `Eu_Tenho_Quantos_Anos_Gente?` | ler da tela | `input()` |
| `MeuBraço` | `continue` | `continue` |
| `Mata_papai` | `break` | `break` |
| `Ce_é_mo_playboy` | `return` | `return` |
| `vo_fica_pelado_aqui` | `print` | `print` |

As palavras-chave funcionam **com ou sem acento** (`Tô_No_SAMU` ou `To_No_SAMU`, `VocêÉDeLá` ou `VoceEDeLa`), mas maiúsculas e minúsculas contam. O `?` do `Eu_Tenho_Quantos_Anos_Gente?` é opcional.

## A linguagem

A sintaxe é a de C: comandos terminam em `;`, blocos ficam entre `{ }` e comentários são `// ...` ou `/* ... */`.

### Variáveis e tipos

```
Red_bull idade = 20;
Jarbas altura = 1.75;
Porra letra = 'a';
Porra nome = "Felipe";               // Porra também guarda texto
Guarapari Red_bull positivo = 10;    // unsigned int
Caralho Caralho Red_bull grande;     // long long int (começa com 0)
Red_bull a = 1, b, c = 3;            // várias de uma vez
```

Os modificadores (`Guarapari`, `Búzios`, `Caralho`) podem vir sozinhos ou antes do tipo. Combinações que não existem em C, como `Guarapari Jarbas` (unsigned float), dão erro.

### Contas e comparações

`+ - * / %`, `== != < <= > >=`, `&& || !`, `= += -= *= /= %=`, `x++`, `x--`, `++x`, `--x`.

Conversão explícita como em C: `(Red_bull) 2.9` dá `2`, `(Porra) 66` dá `'B'`.

### Condições

```
MinhaArte (nota >= 7) {
    vo_fica_pelado_aqui("Passou");
} Faz_Isso_Comigo_Não_Velho (nota >= 5) {
    vo_fica_pelado_aqui("Recuperação");
} Romero_Britto {
    vo_fica_pelado_aqui("Reprovou");
}
```

`Romero_Britto MinhaArte (...)` também funciona como else if. Com um comando só, as chaves são opcionais.

### Laços

```
Quebro_VéiVai_Me_Dar_Injeção (x > 0) {
    x--;
}

VocêÉDeLá (Red_bull i = 0; i < 10; i++) {
    MinhaArte (i == 3) MeuBraço;     // continue
    MinhaArte (i == 8) Mata_papai;   // break
    vo_fica_pelado_aqui(i);
}
```

### Funções

```
Samu Red_bull soma(Red_bull a, Red_bull b) {
    Ce_é_mo_playboy a + b;
}

Samu cumprimenta(Porra nome) {          // sem tipo = não retorna nada (void)
    vo_fica_pelado_aqui("Oi,", nome);
}

Red_bull total = Tô_No_SAMU soma(2, 3);
Tô_No_SAMU cumprimenta("Smith");
```

Funções são declaradas fora de outros blocos e podem ser chamadas antes de aparecer no código. Toda chamada usa `Tô_No_SAMU`.

### Mostrar e ler

```
vo_fica_pelado_aqui("Total:", total);        // separa com espaço e pula linha

Red_bull idade;
Eu_Tenho_Quantos_Anos_Gente?(idade);                     // lê e converte para Red_bull
Eu_Tenho_Quantos_Anos_Gente?("Digite dois: ", a, b);     // mensagem + uma linha por variável
Jarbas peso = Eu_Tenho_Quantos_Anos_Gente?("Peso: ");    // também funciona como valor
```

O valor lido é convertido para o tipo da variável que recebe (`int(input())`, `float(input())` ou texto puro para `Porra`).

## Como o C vira Python

O transpilador tenta fazer o Python se comportar igual ao programa em C:

- **Divisão inteira:** `7 / 2` entre `Red_bull` vira `7 // 2` (dá `3`). Se um dos lados for `Jarbas`/`Katrina`, fica `/`.
- **Tipos na atribuição:** `Red_bull x = 3.9;` vira `x = int(3.9)` (dá `3`), e `Jarbas y = 3;` vira `y = 3.0`.
- **`Porra` em conta vira número:** `letra + 1` vira `ord(letra) + 1`; guardar um número numa `Porra` usa `chr(...)`.
- **Lógicos dão 1 ou 0:** fora de `if`/`while`, `a && b` vira `bool(a) and bool(b)`, e o `vo_fica_pelado_aqui` mostra comparações como `1`/`0`.
- **Comparações não encadeiam:** `3 > 2 > 1` vira `(3 > 2) > 1`, que dá `0` como em C (em Python, `3 > 2 > 1` daria `True`).
- **Escopo de bloco:** Python não tem. Uma variável declarada num bloco interno que esconde outra de fora ganha outro nome (`x` vira `x_2`).
- **Globais:** função que altera variável global ganha `global x` no começo.
- **`VocêÉDeLá`:** no formato clássico (`Red_bull i = a; i < b; i++`, sem mexer em `i` nem no limite dentro do laço) vira `for i in range(...)`. Nos outros casos vira `while`, e o `MeuBraço` (continue) roda o passo antes de pular, como em C.
- **Nomes proibidos no Python** (`lambda`, `print`, `None`...) ganham um `_` no fim.
- **Funções** vão para o topo do arquivo, para poderem ser chamadas antes da declaração.

## Mensagens de erro

Os erros dizem a fase, a linha e a coluna, e apontam o lugar:

```
Erro semântico em teste.meme:3:12: a variável 'idad' não foi declarada (declare antes, ex.: Red_bull idad = 0;)
  3 | MinhaArte (idad == 18) {
    |            ^
```

Também há dicas para erros comuns: `=` em vez de `==` na condição, chamar função sem `Tô_No_SAMU`, usar palavras de C (`int`, `printf`...), `Mata_papai` fora de laço, `Ce_é_mo_playboy` fora de função, número errado de argumentos, `}` faltando.

## Como funciona por dentro

```
código .meme → [lexer] → tokens → [parser] → árvore (AST) → [semântico] → árvore anotada → [gerador] → código .py
```

| Arquivo | Fase |
|---|---|
| [memepy/lexer.py](memepy/lexer.py) | análise léxica: texto → tokens |
| [memepy/parser.py](memepy/parser.py) | análise sintática: parser descendente recursivo; a gramática está no topo do arquivo |
| [memepy/arvore.py](memepy/arvore.py) | os nós da árvore sintática |
| [memepy/semantico.py](memepy/semantico.py) | tabela de símbolos, escopos, tipos e checagens |
| [memepy/gerador.py](memepy/gerador.py) | geração do Python, com parênteses só onde precisa |
| [memepy/erros.py](memepy/erros.py) | erros e avisos com posição |
| [memepy/\_\_main\_\_.py](memepy/__main__.py) | linha de comando |

Para usar dentro de outro programa Python:

```python
from memepy import transpilar
codigo_python, avisos = transpilar(open("programa.meme", encoding="utf-8").read())
```

## Limitações

- Não tem vetores (arrays), ponteiros, structs nem `do-while`.
- `Guarapari`, `Búzios` e `Caralho` não limitam o tamanho do número: inteiros em Python não estouram.
- Com números negativos, `/` e `%` entre inteiros seguem o Python (`-7 / 2` dá `-4`, em C daria `-3`).
- `++` e `--` só como comando sozinho (`x++;`), não no meio de uma conta.
- Cada variável lida pelo `Eu_Tenho_Quantos_Anos_Gente?` ocupa uma linha da entrada.
