"""A practical, deliberately limited LaTeX-math-to-SymPy parser built with Lark."""
from __future__ import annotations

import re

import sympy as sp
from lark import Lark, Transformer, Token

_GRAMMAR = r"""
?start: relation
?relation: expr REL_OP expr                     -> relation
         | expr
?expr: expr "+" product                         -> add
     | expr "-" product                         -> subtract
     | product
?product: product MUL_OP unary                  -> multiply
        | product "/" unary                     -> divide
        | product unary                         -> implicit_multiply
        | unary
?unary: "+" unary                              -> positive
      | "-" unary                              -> negative
      | power
?power: atom "^" exponent                       -> power
      | atom
?exponent: "{" expr "}"
         | unary
?atom: NUMBER                                   -> number
     | FRAC "{" expr "}" "{" expr "}"         -> fraction
     | SQRT "[" expr "]" "{" expr "}"        -> nth_root
     | SQRT "{" expr "}"                     -> square_root
     | FUNC "^" exponent "{" expr "}"       -> powered_function
     | FUNC "^" exponent "(" expr ")"       -> powered_function
     | FUNC "{" expr "}"                     -> function
     | FUNC "(" expr ")"                     -> function
     | FUNC atom                               -> function_atom
     | GREEK                                    -> greek
     | SYMBOL                                   -> symbol
     | "(" expr ")"
     | "{" expr "}"
     | "|" expr "|"                            -> absolute
REL_OP: "=" | "\\neq" | "<" | ">" | "\\le" | "\\ge"
MUL_OP: "*" | "\\cdot" | "\\times"
FRAC: "\\frac" | "\\dfrac" | "\\tfrac"
SQRT: "\\sqrt"
FUNC: "\\sin" | "\\cos" | "\\tan" | "\\cot" | "\\sec" | "\\csc"
    | "\\arcsin" | "\\arccos" | "\\arctan" | "\\sinh" | "\\cosh" | "\\tanh"
    | "\\ln" | "\\log" | "\\exp" | "\\abs"
GREEK: "\\alpha" | "\\beta" | "\\gamma" | "\\delta" | "\\epsilon" | "\\varepsilon"
     | "\\theta" | "\\lambda" | "\\mu" | "\\nu" | "\\pi" | "\\rho" | "\\sigma"
     | "\\tau" | "\\phi" | "\\varphi" | "\\omega" | "\\infty"
     | "\\Gamma" | "\\Delta" | "\\Theta" | "\\Lambda" | "\\Sigma" | "\\Omega"
SYMBOL: /[a-zA-Z](?:_\{?[a-zA-Z0-9]+\}?)?/
NUMBER: /(?:\d+\.\d+|\d+|\.\d+)/
%ignore /[ \t\r\n]+/
%ignore /\\,|\\;|\\!|\\quad|\\qquad/
"""

_PARSER = Lark(_GRAMMAR, parser="earley", lexer="dynamic", ambiguity="resolve")

_GREEK = {
    r"\alpha": "alpha", r"\beta": "beta", r"\gamma": "gamma", r"\delta": "delta",
    r"\epsilon": "epsilon", r"\varepsilon": "varepsilon", r"\theta": "theta",
    r"\lambda": "lambda", r"\mu": "mu", r"\nu": "nu", r"\rho": "rho",
    r"\sigma": "sigma", r"\tau": "tau", r"\phi": "phi", r"\varphi": "varphi",
    r"\omega": "omega", r"\Gamma": "Gamma", r"\Delta": "Delta", r"\Theta": "Theta",
    r"\Lambda": "Lambda", r"\Sigma": "Sigma", r"\Omega": "Omega",
}
_FUNCTIONS = {
    r"\sin": sp.sin, r"\cos": sp.cos, r"\tan": sp.tan, r"\cot": sp.cot,
    r"\sec": sp.sec, r"\csc": sp.csc, r"\arcsin": sp.asin, r"\arccos": sp.acos,
    r"\arctan": sp.atan, r"\sinh": sp.sinh, r"\cosh": sp.cosh, r"\tanh": sp.tanh,
    r"\ln": sp.log, r"\log": sp.log, r"\exp": sp.exp, r"\abs": sp.Abs,
}
_RELATIONS = {
    "=": sp.Eq, r"\neq": sp.Ne, "<": sp.Lt, ">": sp.Gt, r"\le": sp.Le, r"\ge": sp.Ge,
}


class _ToSympy(Transformer):
    def number(self, values):
        text = str(values[0])
        return sp.Rational(text) if "." in text else sp.Integer(text)

    def symbol(self, values):
        name = str(values[0])
        name = re.sub(r"_\{([^}]+)\}", r"_\1", name)
        # SymPy uses E (uppercase) for Euler's number; lowercase e remains a variable.
        if name == "E":
            return sp.E
        return sp.Symbol(name)

    def greek(self, values):
        name = str(values[0])
        if name == r"\pi":
            return sp.pi
        if name == r"\infty":
            return sp.oo
        return sp.Symbol(_GREEK[name])

    def add(self, values):
        return values[0] + values[1]

    def subtract(self, values):
        return values[0] - values[1]

    def multiply(self, values):
        return values[0] * values[-1]

    def implicit_multiply(self, values):
        return values[0] * values[1]

    def divide(self, values):
        return values[0] / values[1]

    def positive(self, values):
        return values[0]

    def negative(self, values):
        return -values[0]

    def power(self, values):
        return values[0] ** values[1]

    def fraction(self, values):
        return values[-2] / values[-1]

    def square_root(self, values):
        return sp.sqrt(values[-1])

    def nth_root(self, values):
        return values[-1] ** (sp.S.One / values[-2])

    def powered_function(self, values):
        return _FUNCTIONS[str(values[0])](values[-1]) ** values[1]

    def function(self, values):
        return _FUNCTIONS[str(values[0])](values[1])

    def function_atom(self, values):
        return _FUNCTIONS[str(values[0])](values[1])

    def absolute(self, values):
        return sp.Abs(values[0])

    def relation(self, values):
        return _RELATIONS[str(values[1])](values[0], values[2])


def _normalize(source: str) -> str:
    source = source.strip()
    # Remove common MathLive / LaTeX display wrappers and layout-only commands.
    source = re.sub(r"^\s*\$\$?(.*?)\$\$?\s*$", r"\1", source, flags=re.S)
    if source.startswith(r"\(") and source.endswith(r"\)"):
        source = source[2:-2]
    if source.startswith(r"\[") and source.endswith(r"\]"):
        source = source[2:-2]
    source = re.sub(r"\\(?:left|right|displaystyle|textstyle)\s*", "", source)
    source = source.replace("−", "-").replace("×", r"\times").replace("·", r"\cdot")
    source = source.replace("＝", "=")
    return source.strip()


def parse_latex_to_sympy(source: str):
    """Parse supported LaTeX into a SymPy object; unsupported syntax raises an error."""
    normalized = _normalize(source)
    if not normalized:
        raise ValueError("No mathematical expression was provided.")
    tree = _PARSER.parse(normalized)
    return _ToSympy().transform(tree)
