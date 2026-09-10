import re
import sys
from pathlib import Path


def replace_once(text: str, pattern: str, replacement: str, label: str, flags=re.S) -> str:
    new, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 match, got {count}")
    return new


def patch_windows(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if "import socket\n" not in text:
        if "import subprocess\n" in text:
            text = text.replace("import subprocess\n", "import subprocess\nimport socket\n", 1)
        elif "import re\n" in text:
            text = text.replace("import re\n", "import re\nimport socket\n", 1)
        else:
            raise SystemExit("Could not add socket import")

    refresh = r'''    def _server_port_open(self):
        try:
            port = int(self.vars["port"].get() or 25565)
        except Exception:
            port = 25565
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            return False

    def _refresh_metrics(self):
        online_process = bool(self.proc and self.proc.poll() is None)
        ready = online_process and self._server_port_open()
        if ready:
            self.starting = False
            status, color = "● ONLINE", "#39ff88"
            self.send_command("list")
        elif online_process:
            status, color = "● STARTING", "#f59e0b"
        else:
            self.starting = False
            status, color = "● OFFLINE", "#ef4444"
            self.players = 0
            self.proc_ps = None
        self.status_lbl.config(text=status, fg=color)
        try:
            maxp = int(self.vars["max_players"].get() or 10)
        except Exception:
            maxp = 10
        self.players_lbl.config(text=f"{self.players} / {maxp}")
        cpu = 0.0
        ram_mb = 0.0
        if online_process and self.proc_ps:
            try:
                cpu = self.proc_ps.cpu_percent(None)
                ram_mb = self.proc_ps.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        self.cpu_lbl.config(text=f"{cpu:.1f}%")
        self.ram_lbl.config(text=f"{ram_mb:.0f} MB")
        if online_process and hasattr(self, "started_at"):
            sec = max(0, int(time.time() - self.started_at))
            self.uptime_lbl.config(text=f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}")
        else:
            self.uptime_lbl.config(text="00:00:00")
        if psutil:
            try:
                self.system_lbl.config(text=f"CPU {psutil.cpu_percent(None):.0f}% · RAM {psutil.virtual_memory().percent:.0f}%")
            except Exception:
                pass
        self.after(2000, self._refresh_metrics)
'''
    text = replace_once(
        text,
        r'    def _refresh_metrics\(self\):\n.*?(?=\n    def refresh_world_size\(self\):)',
        refresh.rstrip(),
        "Windows metrics/status",
    )

    # Broaden the old log-based ready signal when that code exists, but do not depend on it.
    text = text.replace(
        '        if "Done (" in line and self.proc and self.proc.poll() is None:\n            self.starting = False',
        '        low = line.lower()\n        if ("done (" in low or "for help, type" in low or "server started" in low) and self.proc and self.proc.poll() is None:\n            self.starting = False',
        1,
    )

    path.write_text(text, encoding="utf-8")


def patch_android(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # Use a normal followed command file instead of a named pipe that can block startup/control.
    old_fifo = "rm -f \"${'$'}ROOT/console.pipe\"\nmkfifo \"${'$'}ROOT/console.pipe\""
    new_fifo = "rm -f \"${'$'}ROOT/console.pipe\"\n: > \"${'$'}ROOT/console.in\""
    text = text.replace(old_fifo, new_fifo, 1)
    text = text.replace(
        "while true; do cat \"${'$'}HOME/sliqserver/console.pipe\"; done | java ",
        "tail -n0 -F \"${'$'}HOME/sliqserver/console.in\" | java ",
        1,
    )
    text = text.replace("~/sliqserver/console.pipe", "~/sliqserver/console.in")
    text = text.replace("\"${'$'}ROOT/console.pipe\"", "\"${'$'}ROOT/console.in\"")
    text = re.sub(r"(printf[^\n]+) > (~/sliqserver/console\.in)", r"\1 >> \2", text)
    text = re.sub(r"(printf[^\n]+) > (\"\$\{\'\$\'\}ROOT/console\.in\")", r"\1 >> \2", text)

    marker = "mkdir -p \"${'$'}ROOT\"\n"
    if marker in text and 'echo "NOJAVA"' not in text:
        text = text.replace(
            marker,
            marker + 'if ! command -v java >/dev/null 2>&1; then echo "NOJAVA"; exit 5; fi\n',
            1,
        )

    text = text.replace(
        "PID=${'$'}(pgrep -f 'java .*server.jar' | head -n1)",
        "PID=${'$'}(pidof java 2>/dev/null | awk '{print ${'$'}1}')",
    )

    old_ready = "  if grep -q 'Done (' \"${'$'}ROOT/console.log\" 2>/dev/null; then echo STATUS=ONLINE; else echo STATUS=STARTING; fi"
    new_ready = "  PORT=${intOf(javaPort,25565,1024,65535)}\n  if (echo > /dev/tcp/127.0.0.1/${'$'}PORT) >/dev/null 2>&1; then echo STATUS=ONLINE; else echo STATUS=STARTING; fi"
    if old_ready in text:
        text = text.replace(old_ready, new_ready, 1)
    else:
        text, count = re.subn(
            r"\s*if grep -q 'Done \(' .*?then echo STATUS=ONLINE; else echo STATUS=STARTING; fi",
            "\n" + new_ready,
            text,
            count=1,
        )
        if count != 1:
            raise SystemExit("Could not patch Android readiness check")

    callback_pattern = r'''        TermuxBridge\.runForResult\(this, cmd\) \{ r ->\n            runOnUiThread \{\n                if \(r\.stdout\.contains\("MISSING"\)\) \{.*?                \} else if \(r\.exitCode != 0\) \{\n                    toast\("Start failed: \$\{r\.stderr\.ifBlank \{ r\.errorMessage \}\}"\)\n                \}\n            \}\n        \}'''
    callback_replacement = r'''        val launchOk = TermuxBridge.runForResult(this, cmd) { r ->
            runOnUiThread {
                when {
                    r.stdout.contains("MISSING") -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        AlertDialog.Builder(this).setTitle("Server files missing")
                            .setMessage("The selected server files are not installed yet. Download them now?")
                            .setPositiveButton("Download") { _, _ -> downloadServer() }
                            .setNegativeButton("Cancel", null).show()
                    }
                    r.stdout.contains("NOJAVA") -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        AlertDialog.Builder(this).setTitle("Java runtime missing")
                            .setMessage("SliqServer could not find Java inside Termux. Install the required OpenJDK package in Termux, then press Start again.")
                            .setPositiveButton("OK", null).show()
                    }
                    r.exitCode != 0 -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        val detail = r.stderr.ifBlank { r.errorMessage.ifBlank { r.stdout.ifBlank { "Unknown Termux error" } } }
                        AlertDialog.Builder(this).setTitle("Server failed to start")
                            .setMessage(detail.takeLast(5000))
                            .setPositiveButton("OK", null).show()
                    }
                }
            }
        }
        if (!launchOk) {
            statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
            AlertDialog.Builder(this).setTitle("Termux connection failed")
                .setMessage("SliqServer could not send the start command to Termux. Install the current Termux build, grant RUN_COMMAND permission, and set allow-external-apps=true in ~/.termux/termux.properties.")
                .setPositiveButton("OK", null).show()
        }'''
    text, count = re.subn(callback_pattern, lambda _m: callback_replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("Could not patch Android start result handling")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
        raise SystemExit("Usage: apply_startup_reliability_patch.py windows|android <source-file>")
    path = Path(sys.argv[2])
    if sys.argv[1] == "windows":
        patch_windows(path)
    else:
        patch_android(path)
    print(f"Applied startup reliability patch: {path}")


if __name__ == "__main__":
    main()
