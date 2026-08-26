# M0.3 — LaTeX normalisation study

SPEC M0.3: characterise the problem, do not solve it. The normalisation layer is M5; this fixes the number M5 is scoped from.

**Sample:** 30 equations drawn deterministically from 314 structured equations across the two Track A DOCX conversions, stratified over fractions, radicals, logs, powers, systems/piecewise and `\text{}`-wrapped forms. The three cases SPEC and the spike call out are pinned in.

**Naive parse:** `sympy.parsing.latex.parse_latex(raw, backend="lark")`, i.e. the raw pandoc LaTeX fed straight to a parser with no normalisation.

## Headline

**11/30 = 37% of sampled equations do not yield the intended expression from a naive parse.**

| outcome | count | meaning |
|---|---|---|
| OK | 19 | parses to the intended expression (rationalisation / eager eval is value-equal) |
| PARSE_ERROR | 7 | does not parse — loud failure, routes to review |
| AMBIGUOUS | 1 | parser returns an unresolved ambiguity |
| NOT_MACHINE_CHECKABLE | 2 | notation, not an expression (sets, segment lengths) |
| WRONG_SILENT | 1 | parses successfully to a **different** expression — the dangerous class |

The single silent-wrong case is `\log_{8}{4 - \log_{8}32}` (SPEC §2a). It parses without error to `log_8(4 - log_8 32)` when the rendered maths is `log_8 4 - log_8 32`. This is the M5 regression fixture.

## The 30 equations

| # | categories | raw pandoc LaTeX | naive parse | verdict | pattern |
|---|---|---|---|---|---|
| 1 | log | `\log_{8}{4 - \log_{8}32}` | `log(-log(4)/log(8) + 3)/log(8)` | WRONG_SILENT | brace group after \log_b swallowed as the argument: log_8(4 - log_8 32) instead of log_8 4 - log_8 32 |
| 2 | fraction+power+radical+text_wrap | `\sqrt{\frac{25}{\text{8}}} \cdot \sqrt{2} + 2^{- 1}` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | digit wrapped in \text{8} (Word run styling) |
| 3 | system_piecewise+text_wrap | `f(x) = \left\{ \ \begin{matrix}\nx + 2 & \text{dla}\text{ }x \in \lbrack - 4,\ 2\rbrack \\\n - x + 5 & \text{dla}\text{ ` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | piecewise as \left\{ + \begin{matrix}; also NOT_MACHINE_CHECKABLE as a single expression |
| 4 | fraction+power+system_piecewise | `5^{\begin{matrix} \frac{1}{4} \\ \ \end{matrix}}` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | exponent rendered as a 1-cell matrix; intended 5**(1/4) |
| 5 | fraction+power+system_piecewise | `5^{\begin{matrix} \frac{1}{2} \\ \ \end{matrix}}` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | exponent as matrix; intended 5**(1/2) |
| 6 | fraction+power+system_piecewise | `5^{\begin{matrix} \frac{3}{4} \\ \ \end{matrix}}` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | exponent as matrix; intended 5**(3/4) |
| 7 | fraction | `\frac{1}{3}` | `1/3` | OK |  |
| 8 | radical | `\sqrt{5\sqrt{5}}` | `5**(3/4)` | OK | nested radical -> 5**(3/4) |
| 9 | radical | `x = \sqrt{2} - 5` | `Eq(x, -5 + sqrt(2))` | OK |  |
| 10 | radical | `\sqrt{2}` | `sqrt(2)` | OK |  |
| 11 | radical | `2 - 20\sqrt{2}` | `2 - 20*sqrt(2)` | OK |  |
| 12 | log | `\log{K(t)}` | `Tree('_ambig', [log(K(t)), log(K*t)])` | AMBIGUOUS | K(t): function application vs multiplication; parser returns _ambig |
| 13 | log+radical | `a = \log_{2}\left( 3\sqrt{5} + \sqrt{13} \right)` | `Eq(a, log(sqrt(13) + 3*sqrt(5))/log(2))` | OK | parenthesised \left(...\right) argument parses correctly — contrast the brace case |
| 14 | log+radical | `b = \log_{2}\left( 3\sqrt{5} - \sqrt{13} \right)` | `Eq(b, log(-sqrt(13) + 3*sqrt(5))/log(2))` | OK |  |
| 15 | log | `\log_{2}45` | `log(45)/log(2)` | OK |  |
| 16 | log | `\log_{2}30` | `1 + log(15)/log(2)` | OK | auto-simplified to 1 + log_2 15; value-equal |
| 17 | power | `4^{12} \cdot 5^{24}` | `1000000000000000000000000` | OK | eagerly evaluated to 10**24; value-equal |
| 18 | system_piecewise | `X = \left\{ 1,\ 3,\ 5,\ 7,\ 9 \right\}` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | NOT_MACHINE_CHECKABLE | set literal via \left\{; parser errors on \left |
| 19 | system_piecewise+text_wrap | `f(x) = \left\{ \ \begin{matrix} x + 2 & \text{dla}\text{ }x \in \lbrack - 4,\ 2\rbrack \\ - x + 5 & \text{dla}\text{ }x ` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | piecewise as \left\{ + \begin{matrix}; also NOT_MACHINE_CHECKABLE as a single expression |
| 20 | fraction+radical+text_wrap | `\frac{\text{a+}\sqrt{\text{b}}}{\text{c}}` | `UnexpectedCharacters: No terminal matches '\' in the current parser context, at line 1 col` | PARSE_ERROR | variables a,b,c wrapped in \text{}; also '+' inside \text |
| 21 | power | `x^{2} + 10x + 25` | `x**2 + 10*x + 25` | OK |  |
| 22 | radical | `62 - 10\sqrt{2}` | `62 - 10*sqrt(2)` | OK |  |
| 23 | power | `7n^{2} + 21n` | `7*n**2 + 21*n` | OK |  |
| 24 | fraction | `\frac{8}{11}` | `8/11` | OK |  |
| 25 | radical | `\|BC\| = 2\sqrt{10}` | `Eq(Abs(B*C), 2*sqrt(10))` | NOT_MACHINE_CHECKABLE | |BC| is segment length; parsed as Abs(B*C) |
| 26 | fraction+radical | `\frac{1}{\sqrt{10}}` | `sqrt(10)/10` | OK | rationalised to sqrt(10)/10; value-equal |
| 27 | fraction+radical | `\frac{3}{\sqrt{10}}` | `3*sqrt(10)/10` | OK | value-equal |
| 28 | fraction+radical | `\frac{\sqrt{10}}{\sqrt{11}}` | `sqrt(110)/11` | OK | value-equal |
| 29 | fraction | `\frac{a}{b}` | `a/b` | OK |  |
| 30 | radical | `9\sqrt{3}` | `9*sqrt(3)` | OK |  |

## Failure patterns (what M5 normalisation must handle)

1. **`\text{}` wrapping of operands/operators.** Word run styling makes pandoc emit `\text{8}`, `\text{a+}`, `\text{dla}`. The parser rejects the backslash. 48 of 401 structured equations carry `\text{}`. Normalisation: strip `\text{}` around mathematical content, keep it around genuine prose.
2. **Piecewise / sets as `\left\{` + `\begin{matrix}`.** `f(x) = \left\{ \begin{matrix} … \end{matrix} \right.` and `X = \left\{ 1, 3, 5 \right\}`. Not expressions. Map to `Piecewise` / `FiniteSet`, or mark `NOT_MACHINE_CHECKABLE`.
3. **Exponent rendered as a matrix.** `5^{\begin{matrix} \frac{1}{4} \\ \end{matrix}}` for `5**(1/4)`. Recoverable: collapse a 1-cell matrix in an exponent to its content.
4. **Brace group after `\log_b`.** `\log_{8}{X}` binds `{X}` as the whole argument, absorbing following terms. Parenthesised arguments (`\left( … \right)`, rows 13–14) are fine. Normalisation must treat `\log_{b}{…}` grouping explicitly. **Silent — this is the one that matters.**
5. **Juxtaposition: function application vs multiplication.** `\log{K(t)}`, any `f(x)`. `parse_latex` returns an `_ambig` tree. Route to review; do not guess.
6. **Geometry / measure notation.** `|BC|` (segment length), vector bars. Parsed as `Abs(B*C)`. `NOT_MACHINE_CHECKABLE`.

## Storage

`m0/normalisation_sample.jsonl` stores each equation with `latex_raw` (pandoc, for display) and `latex_normalised: null` (M5). A row with raw and no normalised form is valid — it simply cannot be auto-verified (SPEC §5).
