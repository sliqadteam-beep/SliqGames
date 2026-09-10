import re
import sys
from pathlib import Path


def replace_once(text, pattern, replacement, label, flags=re.S):
    out, n = re.subn(pattern, lambda _m: replacement, text, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 match, got {n}")
    return out


def patch_android(path: Path):
    text = path.read_text(encoding="utf-8")

    # Loading / ETA widgets.
    decl = '    private lateinit var addressValue: TextView\n'
    extra_decl = (
        '    private lateinit var startProgress: ProgressBar\n'
        '    private lateinit var startEtaValue: TextView\n'
    )
    if extra_decl not in text:
        text = text.replace(decl, extra_decl + decl, 1)

    state = '    private var refreshBusy = false\n'
    extra_state = (
        '    private var startUiActive = false\n'
        '    private var startUiBeganAt = 0L\n'
    )
    if extra_state not in text:
        text = text.replace(state, state + extra_state, 1)

    controls = r'''    private fun buildControls(page: LinearLayout) {
        val box = section(page, "Server Control")
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(actionButton("▶ START", green) { startServer() }, weight())
        row.addView(actionButton("↻ RESTART", blue) { restartServer() }, weight())
        row.addView(actionButton("■ STOP", red) { stopServer() }, weight())
        box.addView(row, match())

        startProgress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 0
            visibility = android.view.View.GONE
        }
        box.addView(startProgress, match(dp(12)))
        startEtaValue = label("", muted, 12f).apply {
            visibility = android.view.View.GONE
            setPadding(0, dp(5), 0, 0)
        }
        box.addView(startEtaValue, match())
    }
'''
    text = replace_once(text, r'    private fun buildControls\(page: LinearLayout\) \{.*?(?=\n    private fun buildSettings\(page: LinearLayout\))', controls.rstrip(), 'Android controls')

    helpers = r'''    private fun beginStartupUi(stage: String = "Preparing server") {
        if (!::startProgress.isInitialized || !::startEtaValue.isInitialized) return
        startUiActive = true
        startUiBeganAt = System.currentTimeMillis()
        startProgress.visibility = android.view.View.VISIBLE
        startEtaValue.visibility = android.view.View.VISIBLE
        startProgress.progress = 3
        startEtaValue.text = "$stage · estimating time…"
        handler.removeCallbacks(startEtaRunnable)
        handler.post(startEtaRunnable)
    }

    private val startEtaRunnable = object : Runnable {
        override fun run() {
            if (!startUiActive || !::startProgress.isInitialized || !::startEtaValue.isInitialized) return
            val elapsed = ((System.currentTimeMillis() - startUiBeganAt) / 1000).coerceAtLeast(0)
            val remembered = prefs.getLong("last_start_seconds", 0L)
            val estimate = if (remembered in 8..240) remembered else 35L
            val pct = ((elapsed.toDouble() / estimate.toDouble()) * 92.0).toInt().coerceIn(4, 95)
            startProgress.progress = pct
            val stage = when {
                elapsed < 4 -> "Preparing runtime"
                elapsed < 10 -> "Launching Java"
                elapsed < 22 -> "Loading Minecraft"
                else -> "Loading world & plugins"
            }
            val remaining = estimate - elapsed
            startEtaValue.text = if (remaining > 0) {
                "$stage · about ${remaining}s remaining"
            } else {
                "$stage · ${elapsed}s elapsed (this device is taking longer than usual)"
            }
            handler.postDelayed(this, 1000)
        }
    }

    private fun finishStartupUi(success: Boolean) {
        if (!::startProgress.isInitialized || !::startEtaValue.isInitialized) return
        val elapsed = ((System.currentTimeMillis() - startUiBeganAt) / 1000).coerceAtLeast(0)
        startUiActive = false
        handler.removeCallbacks(startEtaRunnable)
        if (success) {
            startProgress.progress = 100
            startEtaValue.text = "Server online · started in ${elapsed}s"
            if (elapsed in 3..600) prefs.edit().putLong("last_start_seconds", elapsed).apply()
        } else {
            startProgress.progress = 0
            startEtaValue.text = "Start stopped · check the error message or Console"
        }
    }

    private fun requiredJavaFor(version: String): Int {
        if (version.startsWith("26.")) return 25
        val p = version.split(".")
        val minor = p.getOrNull(1)?.toIntOrNull() ?: return 21
        if (minor >= 20) return 21
        if (minor >= 17) return 17
        return 17
    }

    private fun javaPackageFor(version: String): String = when (requiredJavaFor(version)) {
        25 -> "openjdk-25"
        21 -> "openjdk-21"
        else -> "openjdk-17"
    }

'''
    text = text.replace('    private fun startServer() {\n', helpers + '    private fun startServer() {\n', 1)

    # Start should show ETA immediately after validation.
    text = text.replace(
        '        val mem = intOf(memoryMb,2048,512,16384)\n',
        '        beginStartupUi("Preparing runtime")\n        val mem = intOf(memoryMb,2048,512,16384)\n        val selectedVersion = versionSpinner.selectedItem.toString()\n        val requiredJava = requiredJavaFor(selectedVersion)\n        val javaPackage = javaPackageFor(selectedVersion)\n',
        1,
    )

    # Replace simple Java existence check with version-aware auto repair.
    old = 'if ! command -v java >/dev/null 2>&1; then echo "NOJAVA"; exit 5; fi\n'
    new = '''CURRENT=0
if command -v java >/dev/null 2>&1; then
  CURRENT=$(java -version 2>&1 | sed -n '1s/.*version "\\([0-9][0-9]*\\).*/\\1/p')
  [ -z "$CURRENT" ] && CURRENT=0
fi
if [ "$CURRENT" -lt ${requiredJava} ]; then
  pkg update -y >/dev/null 2>&1 || true
  pkg install -y ${javaPackage} curl procps coreutils >/dev/null 2>&1 || true
  hash -r
fi
CURRENT=0
if command -v java >/dev/null 2>&1; then
  CURRENT=$(java -version 2>&1 | sed -n '1s/.*version "\\([0-9][0-9]*\\).*/\\1/p')
  [ -z "$CURRENT" ] && CURRENT=0
fi
if [ "$CURRENT" -lt ${requiredJava} ]; then echo "NOJAVA:$CURRENT:${requiredJava}"; exit 5; fi
'''
    if old not in text:
        raise SystemExit('Could not find Android Java check')
    text = text.replace(old, new, 1)

    # Missing server files: Start now downloads them and retries automatically.
    text = text.replace(
        '''                    r.stdout.contains("MISSING") -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        AlertDialog.Builder(this).setTitle("Server files missing")
                            .setMessage("The selected server files are not installed yet. Download them now?")
                            .setPositiveButton("Download") { _, _ -> downloadServer() }
                            .setNegativeButton("Cancel", null).show()
                    }''',
        '''                    r.stdout.contains("MISSING") -> {
                        statusValue.text = "● STARTING"; statusValue.setTextColor(amber)
                        if (::startEtaValue.isInitialized) startEtaValue.text = "Downloading server files…"
                        downloadServer(true)
                    }''',
        1,
    )

    text = text.replace(
        '''                    r.stdout.contains("NOJAVA") -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        AlertDialog.Builder(this).setTitle("Java runtime missing")
                            .setMessage("SliqServer could not find Java inside Termux. Open the setup section and install the required OpenJDK package, then press Start again.")
                            .setPositiveButton("OK", null).show()
                    }''',
        '''                    r.stdout.contains("NOJAVA") -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        finishStartupUi(false)
                        AlertDialog.Builder(this).setTitle("Java runtime setup failed")
                            .setMessage("SliqServer tried to install the required Java ${requiredJava} runtime in Termux, but it is still unavailable. Make sure Termux has internet access and allow-external-apps=true, then try Start again.")
                            .setPositiveButton("OK", null).show()
                    }''',
        1,
    )
    text = text.replace(
        '                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)\n                        val detail = r.stderr',
        '                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)\n                        finishStartupUi(false)\n                        val detail = r.stderr',
        1,
    )
    text = text.replace(
        '            statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)\n            AlertDialog.Builder(this).setTitle("Termux connection failed")',
        '            statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)\n            finishStartupUi(false)\n            AlertDialog.Builder(this).setTitle("Termux connection failed")',
        1,
    )

    # Stop also ends startup progress.
    text = text.replace('    private fun stopServer() {\n', '    private fun stopServer() {\n        if (startUiActive) finishStartupUi(false)\n', 1)

    # Online status completes ETA and learns this device's startup time.
    needle = '        statusValue.text = "● $status"\n        statusValue.setTextColor(if(status=="ONLINE") green else if(status=="STARTING") amber else red)\n'
    repl = needle + '        if (status == "ONLINE" && startUiActive) finishStartupUi(true)\n'
    if needle not in text:
        raise SystemExit('Could not patch Android online ETA completion')
    text = text.replace(needle, repl, 1)

    # Make downloadServer auto-start capable and install the right Java for the selected version.
    text = text.replace('    private fun downloadServer() {\n', '    private fun downloadServer(autoStart: Boolean = false) {\n', 1)
    text = text.replace(
        '                val runtime = "pkg install -y openjdk-21 curl procps coreutils >/dev/null 2>&1 || true; mkdir -p ~/sliqserver"\n',
        '                val runtimePackage = javaPackageFor(version)\n                val runtime = "pkg update -y >/dev/null 2>&1 || true; pkg install -y $runtimePackage curl procps coreutils >/dev/null 2>&1 || true; mkdir -p ~/sliqserver"\n',
        1,
    )
    text = text.replace(
        '                        if(r.exitCode==0) toast("Server files ready")\n                        else toast("Download failed: ${r.stderr.ifBlank { r.errorMessage }}")',
        '                        if(r.exitCode==0) {\n                            toast("Server files ready")\n                            if (autoStart) handler.postDelayed({ startServer() }, 700)\n                        } else {\n                            finishStartupUi(false)\n                            toast("Download failed: ${r.stderr.ifBlank { r.errorMessage }}")\n                        }',
        1,
    )
    text = text.replace(
        '                runOnUiThread { toast("Download failed: ${e.message}") }',
        '                runOnUiThread { finishStartupUi(false); toast("Download failed: ${e.message}") }',
        1,
    )

    # Globally unique-looking persistent server id in hostname.
    old_host = '''    private fun playerHostname(): String {
        val slug = serverName.text.toString().lowercase()
            .replace("_", "-").replace(Regex("[^a-z0-9-]+"), "-")
            .replace(Regex("-+"), "-").trim('-').ifBlank { "my-server" }
        return "$slug.sliqado.org"
    }
'''
    new_host = '''    private fun playerHostname(): String {
        val slug = serverName.text.toString().lowercase()
            .replace("_", "-").replace(Regex("[^a-z0-9-]+"), "-")
            .replace(Regex("-+"), "-").trim('-').ifBlank { "my-server" }
        var serverId = prefs.getString("server_id", "") ?: ""
        if (!serverId.matches(Regex("[a-z0-9]{6}"))) {
            serverId = java.util.UUID.randomUUID().toString().replace("-", "").take(6).lowercase()
            prefs.edit().putString("server_id", serverId).apply()
        }
        return "$slug-$serverId.sliqado.org"
    }
'''
    if old_host not in text:
        # Address patch may differ only slightly; replace the return line and inject id.
        pattern = r'    private fun playerHostname\(\): String \{.*?\n    \}\n'
        text = replace_once(text, pattern, new_host.rstrip(), 'Android unique hostname')
    else:
        text = text.replace(old_host, new_host, 1)
    text = text.replace("my-cool-server.sliqado.org", "my-cool-server-a1b2c3.sliqado.org")
    text = text.replace("Example: My Cool Server becomes my-cool-server.sliqado.org.", "Example: My Cool Server becomes my-cool-server-a1b2c3.sliqado.org. The 6-character Server ID prevents name collisions.")

    path.write_text(text, encoding="utf-8")


def patch_windows(path: Path):
    text = path.read_text(encoding="utf-8")

    # Imports used by managed Java and IDs.
    if 'import uuid\n' not in text:
        text = text.replace('import zipfile\n', 'import zipfile\nimport uuid\n', 1)

    controls = r'''    def _section_controls(self):
        b = self.section("Server Control")
        row = tk.Frame(b, bg="#0d1b2d")
        row.pack(fill="x")
        for text, cmd, color in [
            ("▶ START", self.start_server, "#16a34a"),
            ("↻ RESTART", self.restart_server, "#2563eb"),
            ("■ STOP", self.stop_server, "#dc2626"),
        ]:
            btn = tk.Button(row, text=text, command=cmd, bg=color, fg="white", activebackground=color, activeforeground="white",
                            relief="flat", font=("Segoe UI", 11, "bold"), padx=18, pady=12)
            btn.pack(side="left", padx=(0, 9))
        self.start_progress_var = tk.DoubleVar(value=0)
        self.start_progress = ttk.Progressbar(b, maximum=100, variable=self.start_progress_var)
        self.start_progress.pack(fill="x", pady=(12, 4))
        self.start_eta_lbl = tk.Label(b, text="", fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9))
        self.start_eta_lbl.pack(anchor="w")
        self._start_ui_active = False
        self._start_ui_began = 0.0
        self._start_stage = "Preparing server"
'''
    text = replace_once(text, r'    def _section_controls\(self\):.*?(?=\n    def _entry\()', controls.rstrip(), 'Windows controls')

    helpers = r'''    def _begin_startup_ui(self, stage="Preparing server"):
        if not hasattr(self, "start_progress_var"):
            return
        if not self._start_ui_active:
            self._start_ui_began = time.time()
        self._start_ui_active = True
        self._start_stage = stage
        self.start_progress_var.set(max(3, self.start_progress_var.get()))
        self._startup_eta_tick()

    def _startup_eta_tick(self):
        if not getattr(self, "_start_ui_active", False):
            return
        elapsed = max(0, int(time.time() - self._start_ui_began))
        try:
            remembered = int(float(self.config_data.get("last_start_seconds", 0)))
        except Exception:
            remembered = 0
        estimate = remembered if 8 <= remembered <= 240 else 30
        pct = min(95, max(4, int((elapsed / max(1, estimate)) * 92)))
        self.start_progress_var.set(pct)
        stage = self._start_stage
        if stage == "Preparing server":
            stage = "Launching Java" if elapsed >= 5 else "Preparing server"
        remaining = estimate - elapsed
        if remaining > 0:
            text = f"{stage} · about {remaining}s remaining"
        else:
            text = f"{stage} · {elapsed}s elapsed (taking longer than usual)"
        self.start_eta_lbl.config(text=text, fg="#8ea0b8")
        self.after(1000, self._startup_eta_tick)

    def _finish_startup_ui(self, success):
        if not hasattr(self, "start_progress_var"):
            return
        if not getattr(self, "_start_ui_active", False) and success:
            return
        elapsed = max(0, int(time.time() - getattr(self, "_start_ui_began", time.time())))
        self._start_ui_active = False
        if success:
            self.start_progress_var.set(100)
            self.start_eta_lbl.config(text=f"Server online · started in {elapsed}s", fg="#39ff88")
            if 3 <= elapsed <= 600:
                self.config_data["last_start_seconds"] = elapsed
                try: save_config(self.config_data)
                except Exception: pass
        else:
            self.start_progress_var.set(0)
            self.start_eta_lbl.config(text="Start stopped · check the error message or Console", fg="#ef4444")

    def _server_id(self):
        sid = str(self.config_data.get("server_id", "")).lower()
        if not re.fullmatch(r"[a-z0-9]{6}", sid):
            sid = uuid.uuid4().hex[:6]
            self.config_data["server_id"] = sid
            try: save_config(self.config_data)
            except Exception: pass
        return sid

    def _managed_java_path(self, needed):
        root = BASE / "runtime" / f"java-{needed}"
        if root.exists():
            for exe in root.rglob("java.exe"):
                if exe.parent.name.lower() == "bin":
                    return exe
        return None

    def _java_executable(self):
        p = getattr(self, "_managed_java", None)
        if p and Path(p).exists():
            return str(p)
        return "java"

    def _java_major_from(self, exe):
        try:
            p = subprocess.run([str(exe), "-version"], capture_output=True, text=True, timeout=8)
            m = re.search(r'version "(\\d+)', (p.stderr or "") + (p.stdout or ""))
            return int(m.group(1)) if m else None
        except Exception:
            return None

    def _install_java_runtime_async(self, needed):
        if getattr(self, "_java_installing", False):
            return
        existing = self._managed_java_path(needed)
        if existing:
            self._managed_java = str(existing)
            self.after(0, self.start_server)
            return
        self._java_installing = True
        self._begin_startup_ui(f"Installing Java {needed}")

        def work():
            try:
                root = BASE / "runtime" / f"java-{needed}"
                root.mkdir(parents=True, exist_ok=True)
                archive = root / "java.zip"
                url = f"https://api.adoptium.net/v3/binary/latest/{needed}/ga/windows/x64/jdk/hotspot/normal/eclipse"
                self.log(f"[SliqServer] Downloading managed Java {needed}…")
                download(url, archive)
                with zipfile.ZipFile(archive, "r") as z:
                    z.extractall(root)
                try: archive.unlink()
                except Exception: pass
                exe = self._managed_java_path(needed)
                if not exe:
                    raise RuntimeError("Downloaded Java runtime did not contain java.exe")
                self._managed_java = str(exe)
                self.log(f"[SliqServer] Managed Java {needed} is ready.")
                self._java_installing = False
                self.after(0, self.start_server)
            except Exception as e:
                self._java_installing = False
                self.log(f"[SliqServer] Java setup failed: {e}")
                def show():
                    self._finish_startup_ui(False)
                    messagebox.showerror("Java setup failed", str(e))
                self.after(0, show)
        threading.Thread(target=work, daemon=True).start()

'''
    # Insert helpers immediately before current java_major.
    text = text.replace('    def java_major(self):\n', helpers + '    def java_major(self):\n', 1)

    # Make java_major use managed java if available.
    text = replace_once(
        text,
        r'    def java_major\(self\):\n.*?(?=\n    def required_java\(self, version\):)',
        '''    def java_major(self):\n        return self._java_major_from(self._java_executable())\n'''.rstrip(),
        'Windows java_major',
    )

    start = r'''    def start_server(self):
        if self.proc and self.proc.poll() is None:
            messagebox.showinfo("SliqServer", "Server is already running.")
            return
        if not self.save_settings():
            return
        c = self.current_config()
        if not c["eula"]:
            messagebox.showwarning("Minecraft EULA", "Accept the Minecraft EULA before starting.")
            return

        self._begin_startup_ui("Preparing server")

        if not (SERVER / "server.jar").exists():
            self._start_stage = "Downloading server files"
            def install_then_start():
                self._install_server()
                if (SERVER / "server.jar").exists():
                    self.after(0, self.start_server)
                else:
                    self.after(0, lambda: self._finish_startup_ui(False))
            threading.Thread(target=install_then_start, daemon=True).start()
            return

        needed = self.required_java(str(c["version"]))
        major = self.java_major()
        if major is None or major < needed:
            managed = self._managed_java_path(needed)
            if managed and self._java_major_from(managed) is not None:
                self._managed_java = str(managed)
                major = self._java_major_from(managed)
            if major is None or major < needed:
                self._install_java_runtime_async(needed)
                return

        if c["bedrock_enabled"] and c["software"] == "Paper":
            try:
                if not any((SERVER / "plugins").glob("Geyser-*.jar")):
                    self._start_stage = "Installing Bedrock bridge"
                    self._install_geyser("Paper")
            except Exception as e:
                self.log(f"[SliqServer] Bedrock bridge warning: {e}")

        self.starting = True
        self.stop_requested = False
        self.players = 0
        self._start_stage = "Loading Minecraft"
        mem = int(c["memory_mb"])
        cmd = [
            self._java_executable(),
            f"-Xms{min(1024, mem)}M",
            f"-Xmx{mem}M",
            "-XX:+UseG1GC",
            "-XX:+ParallelRefProcEnabled",
            "-XX:MaxGCPauseMillis=200",
            "-jar", "server.jar", "nogui"
        ]
        try:
            self.proc = subprocess.Popen(cmd, cwd=SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, bufsize=1,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if psutil:
                try:
                    self.proc_ps = psutil.Process(self.proc.pid)
                    self.proc_ps.cpu_percent(None)
                except Exception:
                    self.proc_ps = None
            self.started_at = time.time()
            threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
            self.log(f"[SliqServer] Starting {c['software']} {c['version']}…")
            self.after(1500, self._startup_probe)
            self.after(6000, self._startup_probe)
            self.after(20000, self._startup_probe)
        except Exception as e:
            self.starting = False
            self._finish_startup_ui(False)
            messagebox.showerror("Start failed", str(e))
'''
    text = replace_once(text, r'    def start_server\(self\):.*?(?=\n    def _startup_probe\(self\):|\n    def send_command\(self, command=None\):)', start.rstrip(), 'Windows start server')

    # If an existing startup probe is present, online port still drives final status.
    text = text.replace(
        '        if self._server_port_open():\n            self.starting = False\n',
        '        if self._server_port_open():\n            self.starting = False\n            self._finish_startup_ui(True)\n',
        1,
    )
    text = text.replace(
        '        if ready:\n            self.starting = False\n',
        '        if ready:\n            self.starting = False\n            self._finish_startup_ui(True)\n',
        1,
    )
    text = text.replace('    def stop_server(self):\n', '    def stop_server(self):\n        if getattr(self, "_start_ui_active", False):\n            self._finish_startup_ui(False)\n', 1)

    # Error reader should end the loading bar too.
    text = text.replace(
        '                self.after(0, lambda m=msg: messagebox.showerror("Server failed to start", m))',
        '                def show_start_error(m=msg):\n                    self._finish_startup_ui(False)\n                    messagebox.showerror("Server failed to start", m)\n                self.after(0, show_start_error)',
        1,
    )

    # Persistent ID avoids duplicate server-name hostnames.
    text = text.replace(
        '        address = f"{slugify(server_name)}.sliqado.org"\n',
        '        address = f"{slugify(server_name)}-{self._server_id()}.sliqado.org"\n',
        1,
    )
    text = text.replace('my-cool-server.sliqado.org', 'my-cool-server-a1b2c3.sliqado.org')

    path.write_text(text, encoding="utf-8")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
        raise SystemExit("Usage: apply_startup_eta_unique_patch.py windows|android <source-file>")
    path = Path(sys.argv[2])
    if sys.argv[1] == "android":
        patch_android(path)
    else:
        patch_windows(path)
    print(f"Applied startup ETA + runtime repair + unique address patch: {path}")


if __name__ == "__main__":
    main()
