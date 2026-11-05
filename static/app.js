(() => {
  const mathField = document.getElementById("math-field");
  const latexSource = document.getElementById("latex-source");
  const terminalOutput = document.getElementById("terminal-output");
  const commandInput = document.getElementById("command-input");
  const terminalForm = document.getElementById("terminal-form");
  const readButton = document.getElementById("read-button");
  const renderButton = document.getElementById("render-button");
  const clearButton = document.getElementById("clear-button");
  const editorStatus = document.getElementById("editor-status");
  const runButton = document.getElementById("run-button");

  let sourceIsBeingApplied = false;
  let busy = false;
  const commandHistory = [];
  let historyIndex = 0;
  let draftCommand = "";

  const getLatex = () =>
    typeof mathField.getValue === "function"
      ? mathField.getValue("latex")
      : mathField.value;

  function appendEntry(command, result, isError = false) {
    const entry = document.createElement("div");
    entry.className = "terminal-entry";

    const commandLine = document.createElement("div");
    commandLine.className = "terminal-command";
    const prompt = document.createElement("span");
    prompt.className = "prompt-symbol";
    prompt.textContent = "›";
    const commandText = document.createElement("span");
    commandText.textContent = command;
    commandLine.append(prompt, commandText);

    const resultLine = document.createElement("div");
    resultLine.className = `terminal-result${isError ? " error" : ""}`;
    resultLine.textContent = result;
    entry.append(commandLine, resultLine);
    terminalOutput.append(entry);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  async function postJSON(url, payload = {}) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    return { response, data };
  }

  function setBusy(nextBusy) {
    busy = nextBusy;
    runButton.disabled = nextBusy;
    readButton.disabled = nextBusy;
    renderButton.disabled = nextBusy;
    runButton.textContent = nextBusy ? "Working…" : "Run ▶";
  }

  async function executeCommand(code) {
    if (!code.trim() || busy) return;
    setBusy(true);
    try {
      const { data } = await postJSON("/api/execute", {
        code,
        latex: getLatex(),
      });
      appendEntry(code, data.output ?? "No output.", !data.ok);
    } catch (error) {
      appendEntry(code, `Request failed: ${error.message}`, true);
    } finally {
      setBusy(false);
      commandInput.focus();
    }
  }

  // MathLive edits update the source editor; source edits update the mathfield.
  mathField.addEventListener("input", () => {
    if (sourceIsBeingApplied) return;
    latexSource.value = getLatex();
    editorStatus.textContent = "Visual and source editors are synchronized.";
  });

  latexSource.addEventListener("input", () => {
    sourceIsBeingApplied = true;
    mathField.value = latexSource.value;
    sourceIsBeingApplied = false;
    editorStatus.textContent = "LaTeX source edited.";
  });

  terminalForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = commandInput.value;
    if (!code.trim()) return;
    if (commandHistory[commandHistory.length - 1] !== code)
      commandHistory.push(code);
    historyIndex = commandHistory.length;
    draftCommand = "";
    commandInput.value = "";
    commandInput.style.height = "auto";
    await executeCommand(code);
  });

  commandInput.addEventListener("keydown", (event) => {
    if (
      event.key === "ArrowUp" &&
      !event.shiftKey &&
      !event.ctrlKey &&
      !event.metaKey
    ) {
      // Navigate prior commands only when the caret is on the first line.
      const beforeCaret = commandInput.value.slice(
        0,
        commandInput.selectionStart,
      );
      if (!beforeCaret.includes("\n")) {
        event.preventDefault();
        if (historyIndex === commandHistory.length)
          draftCommand = commandInput.value;
        if (historyIndex > 0) historyIndex -= 1;
        commandInput.value = commandHistory[historyIndex] ?? draftCommand;
        commandInput.setSelectionRange(
          commandInput.value.length,
          commandInput.value.length,
        );
        commandInput.style.height = "auto";
        commandInput.style.height = `${Math.min(commandInput.scrollHeight, 140)}px`;
      }
      return;
    }
    if (
      event.key === "ArrowDown" &&
      !event.shiftKey &&
      !event.ctrlKey &&
      !event.metaKey
    ) {
      const beforeCaret = commandInput.value.slice(
        0,
        commandInput.selectionStart,
      );
      if (!beforeCaret.includes("\n")) {
        event.preventDefault();
        if (historyIndex < commandHistory.length) historyIndex += 1;
        commandInput.value =
          historyIndex === commandHistory.length
            ? draftCommand
            : commandHistory[historyIndex];
        commandInput.setSelectionRange(
          commandInput.value.length,
          commandInput.value.length,
        );
        commandInput.style.height = "auto";
        commandInput.style.height = `${Math.min(commandInput.scrollHeight, 140)}px`;
      }
      return;
    }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      terminalForm.requestSubmit();
    }
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.ctrlKey &&
      !event.metaKey
    ) {
      // Enter runs single-line commands; Shift+Enter inserts a newline for blocks.
      if (!commandInput.value.includes("\n")) {
        event.preventDefault();
        terminalForm.requestSubmit();
      }
    }
  });

  commandInput.addEventListener("input", () => {
    commandInput.style.height = "auto";
    commandInput.style.height = `${Math.min(commandInput.scrollHeight, 140)}px`;
  });

  renderButton.addEventListener("click", async () => {
    // By design, rendering failures and invalid LaTeX are silent.
    try {
      const { data } = await postJSON("/api/render");
      if (!data.ok || typeof data.latex !== "string") return;
      sourceIsBeingApplied = true;
      mathField.value = data.latex;
      latexSource.value = data.latex;
      sourceIsBeingApplied = false;
      editorStatus.textContent = "Rendered the most recent SymPy result.";
    } catch (_) {
      sourceIsBeingApplied = false;
    }
  });

  readButton.addEventListener("click", async () => {
    if (busy) return;
    const source = getLatex().trim();
    if (!source) return;
    setBusy(true);
    editorStatus.textContent = "Parsing LaTeX…";
    try {
      const { data } = await postJSON("/api/read", { latex: source });
      if (data.ok) {
        appendEntry(`read(${JSON.stringify(source)})`, data.sympy, false);
        editorStatus.textContent =
          "Parsed LaTeX into SymPy. Render is now available.";
      } else {
        appendEntry(
          `read(${JSON.stringify(source)})`,
          data.error || "Could not parse LaTeX.",
          true,
        );
        editorStatus.textContent = "The parser could not read this expression.";
      }
    } catch (error) {
      appendEntry("read(LaTeX)", `Request failed: ${error.message}`, true);
      editorStatus.textContent = "The parser request failed.";
    } finally {
      setBusy(false);
    }
  });

  clearButton.addEventListener("click", () => {
    terminalOutput.replaceChildren();
  });

  document.querySelectorAll(".example-chip").forEach((button) => {
    button.addEventListener("click", () => {
      commandInput.value = button.dataset.code || "";
      commandInput.focus();
      commandInput.style.height = "auto";
      commandInput.style.height = `${Math.min(commandInput.scrollHeight, 140)}px`;
    });
  });

  // Align the editable source with MathLive's normalized value after its definition loads.
  customElements.whenDefined("math-field").then(() => {
    if (!latexSource.value) latexSource.value = getLatex();
  });

  window.addEventListener("pagehide", () => {
    navigator.sendBeacon("/shutdown");
  });
})();
