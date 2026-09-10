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

    # A server is ready when its actual TCP listener is reachable, not when one exact log phrase appears.
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

    reader = r'''    def _reader(self, proc):
        recent = []
        try:
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                recent.append(line.rstrip())
                if len(recent) > 80:
                    del recent[:-80]
                self._last_server_lines = recent[:]
                self.log(line)
                low = line.lower()
                if ("done (" in low or "for help, type" in low or "server started" in low) and proc.poll() is None:
                    self.starting = False
        except Exception as e:
            self.log(f"[SliqServer] Log reader: {e}")
        finally:
            try:
                code = proc.wait(timeout=0.2)
            except Exception:
                code = proc.poll()
            if code is not None:
                self.starting = False
            if not self.stop_requested and code not in (None, 0):
                self.log(f"[SliqServer] Server stopped with code {code}")
                details = "\n".join((getattr(self, "_last_server_lines", []) or [])[-18:]).strip()
                if not details:
                    details = f"Java exited with code {code}."
                msg = "The Minecraft server stopped while starting.\n\n" + details
                self.after(0, lambda m=msg: messagebox.showerror("Server failed to start", m))
'''
    text = replace_once(
        text,
        r'    def _reader\(self, proc\):\n.*?(?=\n    def java_major\(self\):)',
        reader.rstrip(),
        "Windows log reader",
    )

    # Make the UI react immediately if Java exits right after Popen, and don't depend only on logs.
    needle = '            threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()\n            self.log(f"[SliqServer] Starting {c[\'software\']} {c[\'version\']}…")'
    if needle in text:
        text = text.replace(
            needle,
            needle + '\n            self.after(1500, self._startup_probe)\n            self.after(6000, self._startup_probe)\n            self.after(20000, self._startup_probe)',
            1,
        )
    else:
        # V4 may have a slightly different log message; insert after the reader thread.
        text, count = re.subn(
            r'(\s+threading\.Thread\(target=self\._reader, args=\(self\.proc,\), daemon=True\)\.start\(\))',
            r'\1\n            self.after(1500, self._startup_probe)\n            self.after(6000, self._startup_probe)\n            self.after(20000, self._startup_probe)',
            text,
            count=1,
        )
        if count != 1:
            raise SystemExit("Could not patch Windows startup probes")

    probe = r'''    def _startup_probe(self):
        if not self.proc:
            return
        code = self.proc.poll()
        if code is not None:
            self.starting = False
            return
        if self._server_port_open():
            self.starting = False
'''
    text = replace_once(
        text,
        r'(?=    def send_command\(self, command=None\):)',
        probe + "\n",
        "Windows startup probe",
        flags=0,
    )

    path.write_text(text, encoding="utf-8")


def patch_android(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # FIFO input can block in awkward ways. A followed command file is much more robust on Termux.
    text = text.replace('rm -f "${\'$\'}ROOT/console.pipe"\nmkfifo "${\'$\'}ROOT/console.pipe"',
                        'rm -f "${\'$\'}ROOT/console.pipe"\n: > "${\'$\'}ROOT/console.in"', 1)
    text = text.replace('while true; do cat "${\'$\'}HOME/sliqserver/console.pipe"; done | java ',
                        'tail -n0 -F "${\'$\'}HOME/sliqserver/console.in" | java ', 1)
    text = text.replace('~/sliqserver/console.pipe', '~/sliqserver/console.in')
    text = text.replace('"${\'$\'}ROOT/console.pipe"', '"${\'$\'}ROOT/console.in"')
    # console.in is a regular file, so commands must be appended instead of truncating it.
    text = re.sub(r"(printf[^\n]+) > (~/sliqserver/console\.in)", r"\1 >> \2", text)
    text = re.sub(r"(printf[^\n]+) > (\"\$\{\'\$\'\}ROOT/console\.in\")", r"\1 >> \2", text)

    # Check Java before launching so a missing Termux runtime produces a useful error.
    marker = 'mkdir -p "${\'$\'}ROOT"\n'
    if marker in text and 'echo "NOJAVA"' not in text:
        text = text.replace(marker, marker + 'if ! command -v java >/dev/null 2>&1; then echo "NOJAVA"; exit 5; fi\n', 1)

    # The old process test could match wrapper shells. Detect the actual java process instead.
    text = text.replace("PID=${'$'}(pgrep -f 'java .*server.jar' | head -n1)",
                        "PID=${'$'}(pidof java 2>/dev/null | awk '{print ${'$'}1}')")

    # Readiness is the real Minecraft TCP listener, not one Paper log sentence.
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

    # Replace the result-callback tail so every failed launch returns to OFFLINE with a useful error.
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
                            .setMessage("SliqServer could not find Java inside Termux. Open the setup section and install the required OpenJDK package, then press Start again.")
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
                .setMessage("SliqServer could not send the start command to Termux. Install the current Termux build, grant the RUN_COMMAND permission, and set allow-external-apps=true in ~/.termux/termux.properties.")
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
