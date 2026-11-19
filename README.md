# Math Console — Local SymPy + MathLive CAS

A local Flask application with an editable MathLive equation field and a persistent SymPy/Python console. The UI uses separate HTML, CSS, and JavaScript files; Python lives in `app.py` and `latex_parser.py`.

## Features

- **Visual editing and LaTeX source editing:** both editors stay synchronized.
- **Render:** takes the most recent value-producing console expression and displays it in MathLive. If the value is already a string (for example, from `latex(expr)`), it is treated as LaTeX source; otherwise it is converted with `sympy.latex()`.
- **Read button and `read()` command:** parse the equation currently displayed in MathLive into a SymPy object using the Lark grammar. In the terminal, `read()` returns that object, so it can be used immediately in the next expression (for example, `diff(read(), x)`).
- **Terminal history:** press Up/Down to navigate previously submitted commands.
- **Euler constant:** uppercase `E` in parsed LaTeX maps to `sympy.E`; lowercase `e` remains a variable.
- **Persistent console:** variables and imports persist for the current browser session until the Flask process restarts.
- **SymPy preloaded:** common names such as `x`, `y`, `z`, `integrate`, `diff`, `solve`, and `latex` are available immediately.

## Run locally

Python 3.10+ is recommended.

### Windows PowerShell

```powershell
cd path\to\mathlive-cas
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
cd mathlive-cas
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. MathLive is loaded from jsDelivr, so the browser needs network access to load that CDN resource.

## Examples

Enter any of these in the terminal and press **Run**:

```python
integrate(sin(x), x)
diff(sin(x)**2, x)
solve(x**2 - 5*x + 6, x)
latex(integrate(x**2, x))
```

Use **Render** after a command to move its result to the equation editor. The **Read** button parses the equation currently shown. You can also call `read()` from the terminal and compose it with another command, for example `diff(read(), x)` or `simplify(read())`. Press Up/Down in the terminal to recall previous commands.

## LaTeX parser scope

The Lark-based reader is intentionally a practical subset parser, not a complete LaTeX engine. It supports arithmetic, implicit multiplication, powers, subscripted symbols, fractions, square and indexed roots, absolute values, common trig/hyperbolic/logarithmic functions, common Greek symbols, constants `\pi` and `\infty`, and simple relations. Unsupported constructs (such as arbitrary environments, aligned equations, matrices, and general integral/differential notation) return a parse error in the terminal. Use the SymPy console for those operations.

## Local-execution note

The terminal executes Python in the Flask process and is **not sandboxed**. The app binds to `127.0.0.1` only. Do not expose it on a public interface or run untrusted code through it. Console variables are stored in memory and reset when the server restarts.
