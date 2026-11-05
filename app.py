"""Local-first Flask interface for a persistent SymPy console and MathLive editor."""

from __future__ import annotations

import ast
import contextlib
import io
import os
import secrets
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

import sympy as sp
from flask import Flask, jsonify, render_template, request, session

from latex_parser import parse_latex_to_sympy

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


# This is intentionally an in-process REPL for a local application. Its variables
# persist per browser session until the server restarts. It is not a sandbox.
@dataclass
class ConsoleState:
    namespace: dict[str, Any] = field(default_factory=dict)
    last_result: Any = None
    has_result: bool = False
    current_latex: str = ""


_states: dict[str, ConsoleState] = {}
_states_lock = threading.RLock()


def _new_namespace(state: ConsoleState) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__builtins__": __builtins__, "sympy": sp}
    namespace.update({name: getattr(sp, name) for name in sp.__all__})
    namespace.update({name: getattr(sp, name) for name in ("latex", "pprint")})
    default_symbols = ("x", "y", "z", "t", "a", "b", "c", "n", "r", "theta")
    namespace.update(dict(zip(default_symbols, sp.symbols(" ".join(default_symbols)))))

    def read():
        """Parse the equation currently shown in the browser's MathLive editor."""
        if not state.current_latex.strip():
            raise ValueError("There is no rendered equation to read.")
        return parse_latex_to_sympy(state.current_latex)

    namespace["read"] = read
    namespace["_"] = None
    return namespace


def _state() -> ConsoleState:
    state_id = session.get("console_id")
    if not state_id:
        state_id = str(uuid.uuid4())
        session["console_id"] = state_id
    with _states_lock:
        if state_id not in _states:
            state = ConsoleState()
            state.namespace = _new_namespace(state)
            _states[state_id] = state
        return _states[state_id]


def _display_value(value: Any) -> str:
    try:
        return repr(value)
    except Exception:
        return f"<{type(value).__name__}>"


def _run_console_code(code: str, state: ConsoleState) -> tuple[str, Any, bool]:
    """Execute Python like a small REPL, evaluating a final expression if present."""
    tree = ast.parse(code, mode="exec")
    stdout = io.StringIO()
    stderr = io.StringIO()
    value: Any = None
    has_value = False
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            prefix = ast.Module(body=tree.body[:-1], type_ignores=tree.type_ignores)
            if prefix.body:
                exec(
                    compile(prefix, "<console>", "exec"),
                    state.namespace,
                    state.namespace,
                )
            expression = ast.Expression(body=tree.body[-1].value)
            value = eval(
                compile(expression, "<console>", "eval"),
                state.namespace,
                state.namespace,
            )
            has_value = True
            state.last_result = value
            state.has_result = True
            state.namespace["_"] = value
        else:
            exec(compile(tree, "<console>", "exec"), state.namespace, state.namespace)

    chunks = []
    out_text = stdout.getvalue().rstrip()
    err_text = stderr.getvalue().rstrip()
    if out_text:
        chunks.append(out_text)
    if err_text:
        chunks.append(err_text)
    if has_value:
        chunks.append(_display_value(value))
    if not chunks:
        chunks.append("(executed; no expression value)")
    return "\n".join(chunks), value, has_value


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/session")
def session_info():
    state = _state()
    return jsonify({"ready": True, "has_result": state.has_result})


@app.post("/api/execute")
def execute():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "")
    if not isinstance(code, str) or not code.strip():
        return jsonify(
            {"ok": False, "output": "Enter a Python/SymPy expression first."}
        ), 400
    if len(code) > 50_000:
        return jsonify(
            {"ok": False, "output": "Input is too long (limit: 50,000 characters)."}
        ), 413

    state = _state()
    current_latex = payload.get("latex", "")
    if isinstance(current_latex, str):
        state.current_latex = current_latex
    try:
        with _states_lock:
            output, _, _ = _run_console_code(code, state)
        return jsonify({"ok": True, "output": output})
    except Exception as exc:
        return jsonify({"ok": False, "output": f"{type(exc).__name__}: {exc}"}), 400


@app.post("/api/render")
def render_last_result():
    state = _state()
    if not state.has_result:
        return jsonify({"ok": False, "latex": None})
    try:
        value = state.last_result
        # SymPy's latex() function itself returns a string, so preserve that source.
        latex_source = value if isinstance(value, str) else sp.latex(value)
        return jsonify({"ok": True, "latex": latex_source})
    except Exception:
        # Rendering failures are intentionally silent in the UI.
        return jsonify({"ok": False, "latex": None})


@app.post("/api/read")
def read_latex():
    payload = request.get_json(silent=True) or {}
    source = payload.get("latex", "")
    if not isinstance(source, str) or not source.strip():
        return jsonify({"ok": False, "error": "The LaTeX editor is empty."}), 400
    if len(source) > 20_000:
        return jsonify(
            {
                "ok": False,
                "error": "LaTeX input is too long (limit: 20,000 characters).",
            }
        ), 413
    try:
        expression = parse_latex_to_sympy(source)
        state = _state()
        with _states_lock:
            state.last_result = expression
            state.has_result = True
            state.namespace["_"] = expression
        return jsonify(
            {
                "ok": True,
                "sympy": str(expression),
                "latex": sp.latex(expression),
            }
        )
    except Exception as exc:
        return jsonify(
            {"ok": False, "error": f"Could not parse this LaTeX: {exc}"}
        ), 400


@app.post("/shutdown")
def shutdown():
    threading.Thread(target=lambda: os._exit(0), daemon=True).start()

    return "", 200


if __name__ == "__main__":
    # Bind only to loopback; the console executes submitted Python directly.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
