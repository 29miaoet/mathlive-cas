from pathlib import Path
import sys

import sympy as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from latex_parser import parse_latex_to_sympy


def test_fraction_power_and_addition():
    x = sp.Symbol("x")
    assert sp.simplify(parse_latex_to_sympy(r"\frac{x^2 + 1}{\sqrt{x}}") - (x**2 + 1) / sp.sqrt(x)) == 0


def test_implicit_multiplication():
    x, y = sp.symbols("x y")
    assert parse_latex_to_sympy("2xy") == 2 * x * y


def test_trig_and_greek_constant():
    theta = sp.Symbol("theta")
    assert parse_latex_to_sympy(r"\sin(\theta) + \pi") == sp.sin(theta) + sp.pi


def test_indexed_root_and_relation():
    x, y = sp.symbols("x y")
    assert parse_latex_to_sympy(r"\sqrt[3]{x}") == x ** sp.Rational(1, 3)
    assert parse_latex_to_sympy("x = y") == sp.Eq(x, y)


def test_powered_trigonometric_function_from_sympy_latex():
    x = sp.Symbol("x")
    assert parse_latex_to_sympy(r"\sin^{2}{\left(x \right)}") == sp.sin(x) ** 2


def test_uppercase_E_is_sympy_eulers_number():
    assert parse_latex_to_sympy("E") is sp.E
    assert parse_latex_to_sympy("E^x") == sp.E ** sp.Symbol("x")
    # Lowercase e remains an ordinary variable.
    assert parse_latex_to_sympy("e") == sp.Symbol("e")
