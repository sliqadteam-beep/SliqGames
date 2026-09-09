import json
import os
import queue
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
import urllib.parse
import zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import psutil
except Exception:
    psutil = None

APP_VERSION = "3.0"
UA = "SliqServer/3.0 (https://sliqado.org/server/)"
BASE = Path.home() / "SliqServer"
SERVER = BASE / "server"
BACKUPS = BASE / "backups"
CONFIG = BASE / "config.json"
SERVER.mkdir(parents=True, exist_ok=True)
BACKUPS.mkdir(parents=True, exist_ok=True)

DEFAULTS = {
    "server_name": "My Server",
    "software": "Paper",
    "version": "1.21.11",
    "max_players": 10,
    "gamemode": "survival",
    "difficulty": "normal",
    "view_distance": 6,
    "simulation_distance": 4,
    "port": 25565,
    "bedrock_port": 19132,
    "memory_mb": 2048,
    "java_enabled": True,
    "bedrock_enabled": False,
    "online_mode": True,
    "pvp": True,
    "whitelist": False,
    "command_blocks": False,
    "spawn_protection": 16,
    "custom_address": "",
    "eula": False,
}

def load_config():
    data = DEFAULTS.copy()
    try:
        if CONFIG.exists():
            data.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    except Exception:
        pass
    return data

def save_config(data):
    BASE.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)

def slugify(value):
    s = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower().replace("_", "-"))
    return re.sub(r"-+", "-", s).strip("-") or "my-server"

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class SliqServerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"SliqServer {APP_VERSION}")
        self.geometry("1100x820")
        self.minsize(860, 650)
        self.configure(bg="#07111f")
        self.proc = None
        self.proc_ps = None
        self.log_queue = queue.Queue()
        self.players = 0
        self.max_seen = 0
        self.starting = False
        self.stop_requested = False
        self.config_data = load_config()
        self.vars = {}
        self._build_style()
        self._build_scroll_page()
        self._load_vars()
        self.after(250, self._drain_logs)
        self.after(1000, self._refresh_metrics)

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground="#101f34", background="#101f34", foreground="white", arrowcolor="white")
        style.map("TCombobox", fieldbackground=[("readonly", "#101f34")], foreground=[("readonly", "white")], selectbackground=[("readonly", "#2563eb")])
        style.configure("TSpinbox", fieldbackground="#101f34", foreground="white", arrowsize=16)
        self.option_add("*TCombobox*Listbox.background", "#101f34")
        self.option_add("*TCombobox*Listbox.foreground", "white")
        self.option_add("*TCombobox*Listbox.selectBackground", "#2563eb")

    def _build_scroll_page(self):
        outer = tk.Frame(self, bg="#07111f")
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, bg="#07111f", highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.page = tk.Frame(self.canvas, bg="#07111f")
        self.window_id = self.canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.page.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.bind_all("<MouseWheel>", self._mousewheel)

        top = tk.Frame(self.page, bg="#07111f")
        top.pack(fill="x", padx=28, pady=(24, 10))
        tk.Label(top, text="SliqServer", fg="white", bg="#07111f", font=("Segoe UI", 28, "bold")).pack(side="left")
        tk.Label(top, text="One-page Minecraft server control", fg="#8ea0b8", bg="#07111f", font=("Segoe UI", 11)).pack(side="left", padx=16, pady=(10, 0))

        self._section_overview()
        self._section_controls()
        self._section_server_settings()
        self._section_access()
        self._section_addons()
        self._section_world()
        self._section_console()

    def _mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def section(self, title, subtitle=""):
        box = tk.Frame(self.page, bg="#0d1b2d", highlightbackground="#1d3047", highlightthickness=1)
        box.pack(fill="x", padx=28, pady=9)
        head = tk.Frame(box, bg="#0d1b2d")
        head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(head, text=title, fg="white", bg="#0d1b2d", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        body = tk.Frame(box, bg="#0d1b2d")
        body.pack(fill="x", padx=18, pady=(0, 18))
        return body

    def card(self, parent, title, value, col):
        f = tk.Frame(parent, bg="#101f34", padx=14, pady=12)
        f.grid(row=0, column=col, sticky="nsew", padx=5)
        tk.Label(f, text=title, fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        lbl = tk.Label(f, text=value, fg="white", bg="#101f34", font=("Segoe UI", 18, "bold"))
        lbl.pack(anchor="w", pady=(5, 0))
        parent.grid_columnconfigure(col, weight=1)
        return lbl

    def _section_overview(self):
        b = self.section("Overview", "Live server status, players and utilization.")
        self.status_lbl = self.card(b, "STATUS", "● OFFLINE", 0)
        self.players_lbl = self.card(b, "PLAYERS", "0 / 10", 1)
        self.cpu_lbl = self.card(b, "SERVER CPU", "0%", 2)
        self.ram_lbl = self.card(b, "SERVER RAM", "0 MB", 3)
        second = tk.Frame(b, bg="#0d1b2d")
        second.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        for c in range(3): second.grid_columnconfigure(c, weight=1)
        self.world_lbl = self.card(second, "WORLD SIZE", "0 B", 0)
        self.uptime_lbl = self.card(second, "UPTIME", "00:00:00", 1)
        self.system_lbl = self.card(second, "SYSTEM LOAD", "CPU 0% · RAM 0%", 2)

    def _section_controls(self):
        b = self.section("Server Control")
        for text, cmd, color in [
            ("▶ START", self.start_server, "#16a34a"),
            ("↻ RESTART", self.restart_server, "#2563eb"),
            ("■ STOP", self.stop_server, "#dc2626"),
        ]:
            btn = tk.Button(b, text=text, command=cmd, bg=color, fg="white", activebackground=color, activeforeground="white",
                            relief="flat", font=("Segoe UI", 11, "bold"), padx=18, pady=12)
            btn.pack(side="left", padx=(0, 9))

    def _entry(self, parent, label, var, row, col=0, width=22):
        f = tk.Frame(parent, bg="#0d1b2d")
        f.grid(row=row, column=col, sticky="ew", padx=6, pady=6)
        tk.Label(f, text=label, fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        e = tk.Entry(f, textvariable=var, width=width, bg="#101f34", fg="white", insertbackground="white",
                     relief="flat", font=("Segoe UI", 10))
        e.pack(fill="x", ipady=7, pady=(4, 0))
        parent.grid_columnconfigure(col, weight=1)
        return e

    def _combo(self, parent, label, var, values, row, col=0):
        f = tk.Frame(parent, bg="#0d1b2d")
        f.grid(row=row, column=col, sticky="ew", padx=6, pady=6)
        tk.Label(f, text=label, fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        cb = ttk.Combobox(f, textvariable=var, values=values, state="readonly")
        cb.pack(fill="x", ipady=5, pady=(4, 0))
        parent.grid_columnconfigure(col, weight=1)
        return cb

    def _spin(self, parent, label, var, frm, to, row, col=0, inc=1):
        f = tk.Frame(parent, bg="#0d1b2d")
        f.grid(row=row, column=col, sticky="ew", padx=6, pady=6)
        tk.Label(f, text=label, fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        sp = ttk.Spinbox(f, textvariable=var, from_=frm, to=to, increment=inc)
        sp.pack(fill="x", ipady=5, pady=(4, 0))
        parent.grid_columnconfigure(col, weight=1)
        return sp

    def _check(self, parent, label, var, row, col=0):
        cb = tk.Checkbutton(parent, text=label, variable=var, bg="#0d1b2d", fg="white", activebackground="#0d1b2d",
                            activeforeground="white", selectcolor="#101f34", font=("Segoe UI", 10))
        cb.grid(row=row, column=col, sticky="w", padx=8, pady=7)
        parent.grid_columnconfigure(col, weight=1)
        return cb

    def _section_server_settings(self):
        b = self.section("Server Settings", "Every option is directly selectable on this page.")
        self.vars["server_name"] = tk.StringVar()
        self.vars["software"] = tk.StringVar()
        self.vars["version"] = tk.StringVar()
        self.vars["max_players"] = tk.IntVar()
        self.vars["gamemode"] = tk.StringVar()
        self.vars["difficulty"] = tk.StringVar()
        self.vars["view_distance"] = tk.IntVar()
        self.vars["simulation_distance"] = tk.IntVar()
        self.vars["memory_mb"] = tk.IntVar()
        self.vars["port"] = tk.IntVar()
        self.vars["bedrock_port"] = tk.IntVar()
        self.vars["spawn_protection"] = tk.IntVar()

        self._entry(b, "Server name", self.vars["server_name"], 0, 0)
        self._combo(b, "Server software", self.vars["software"], ["Paper", "Fabric"], 0, 1)
        self._combo(b, "Minecraft version", self.vars["version"], ["1.21.11", "1.21.10", "1.21.8", "1.21.5", "1.21.4", "1.20.6"], 0, 2)
        self._spin(b, "Max players", self.vars["max_players"], 1, 200, 1, 0)
        self._combo(b, "Gamemode", self.vars["gamemode"], ["survival", "creative", "adventure", "spectator"], 1, 1)
        self._combo(b, "Difficulty", self.vars["difficulty"], ["peaceful", "easy", "normal", "hard"], 1, 2)
        self._spin(b, "View distance", self.vars["view_distance"], 2, 32, 2, 0)
        self._spin(b, "Simulation distance", self.vars["simulation_distance"], 2, 32, 2, 1)
        self._spin(b, "Server RAM (MB)", self.vars["memory_mb"], 512, 32768, 2, 2, 256)
        self._spin(b, "Java port", self.vars["port"], 1024, 65535, 3, 0)
        self._spin(b, "Bedrock port", self.vars["bedrock_port"], 1024, 65535, 3, 1)
        self._spin(b, "Spawn protection", self.vars["spawn_protection"], 0, 100, 3, 2)

        toggles = tk.Frame(b, bg="#0d1b2d")
        toggles.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        for k in ["java_enabled","bedrock_enabled","online_mode","pvp","whitelist","command_blocks","eula"]:
            self.vars[k] = tk.BooleanVar()
        self._check(toggles, "Java players", self.vars["java_enabled"], 0, 0)
        self._check(toggles, "Bedrock players (Geyser)", self.vars["bedrock_enabled"], 0, 1)
        self._check(toggles, "Online mode", self.vars["online_mode"], 0, 2)
        self._check(toggles, "PvP", self.vars["pvp"], 1, 0)
        self._check(toggles, "Whitelist", self.vars["whitelist"], 1, 1)
        self._check(toggles, "Command blocks", self.vars["command_blocks"], 1, 2)
        self._check(toggles, "I accept the Minecraft EULA", self.vars["eula"], 2, 0)

        row = tk.Frame(b, bg="#0d1b2d")
        row.grid(row=5, column=0, columnspan=3, sticky="ew", padx=6, pady=(12, 0))
        tk.Button(row, text="SAVE SETTINGS", command=self.save_settings, bg="#2563eb", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=9).pack(side="left")
        tk.Button(row, text="DOWNLOAD / UPDATE SERVER", command=self.install_server_async, bg="#18283d", fg="white",
                  relief="flat", font=("Segoe UI", 10, "bold"), padx=14, pady=9).pack(side="left", padx=8)

    def _section_access(self):
        b = self.section("Address & Network")
        self.local_ip_var = tk.StringVar(value=local_ip())
        self.address_var = tk.StringVar()
        self.custom_address_var = tk.StringVar()
        self._entry(b, "Local IP", self.local_ip_var, 0, 0)
        self._entry(b, "Standard address", self.address_var, 0, 1)
        self._entry(b, "Custom address", self.custom_address_var, 0, 2)
        tk.Label(b, text="DNS still has to point the hostname to this PC or a tunnel/router forwarding setup.",
                 fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=6)

    def _section_addons(self):
        b = self.section("Mods & Plugins", "Paper uses plugins. Fabric uses mods.")
        tk.Button(b, text="ADD PLUGIN .JAR", command=lambda: self.add_jar("plugins"), bg="#2563eb", fg="white", relief="flat", padx=14, pady=10).pack(side="left", padx=(0,8))
        tk.Button(b, text="ADD MOD .JAR", command=lambda: self.add_jar("mods"), bg="#2563eb", fg="white", relief="flat", padx=14, pady=10).pack(side="left", padx=(0,8))
        tk.Button(b, text="OPEN PLUGINS", command=lambda: self.open_folder(SERVER/"plugins"), bg="#18283d", fg="white", relief="flat", padx=14, pady=10).pack(side="left", padx=(0,8))
        tk.Button(b, text="OPEN MODS", command=lambda: self.open_folder(SERVER/"mods"), bg="#18283d", fg="white", relief="flat", padx=14, pady=10).pack(side="left")

    def _section_world(self):
        b = self.section("World & Backups")
        tk.Button(b, text="REFRESH WORLD SIZE", command=self.refresh_world_size, bg="#18283d", fg="white", relief="flat", padx=14, pady=10).pack(side="left", padx=(0,8))
        tk.Button(b, text="CREATE BACKUP", command=self.create_backup, bg="#2563eb", fg="white", relief="flat", padx=14, pady=10).pack(side="left", padx=(0,8))
        tk.Button(b, text="CLEAR WORLD", command=self.clear_world, bg="#dc2626", fg="white", relief="flat", padx=14, pady=10).pack(side="left")

    def _section_console(self):
        b = self.section("Console")
        self.console = tk.Text(b, height=14, bg="#050a10", fg="#d7e3f4", insertbackground="white", relief="flat", font=("Consolas", 9))
        self.console.pack(fill="x")
        row = tk.Frame(b, bg="#0d1b2d")
        row.pack(fill="x", pady=(8, 0))
        self.command_entry = tk.Entry(row, bg="#101f34", fg="white", insertbackground="white", relief="flat")
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.command_entry.bind("<Return>", lambda e: self.send_command())
        tk.Button(row, text="SEND", command=self.send_command, bg="#2563eb", fg="white", relief="flat", padx=18, pady=8).pack(side="left", padx=(8,0))

    def _load_vars(self):
        c = self.config_data
        for k, var in self.vars.items():
            if k in c:
                var.set(c[k])
        self.custom_address_var.set(c.get("custom_address", ""))
        self._update_address()
        self.vars["server_name"].trace_add("write", lambda *_: self._update_address())
        self.custom_address_var.trace_add("write", lambda *_: self._update_address())

    def _update_address(self):
        standard = f"{slugify(self.vars['server_name'].get() if 'server_name' in self.vars else 'my-server')}.sliqado.org"
        self.address_var.set(self.custom_address_var.get().strip() or standard)

    def current_config(self):
        c = self.config_data.copy()
        for k, var in self.vars.items():
            try:
                c[k] = var.get()
            except Exception:
                pass
        c["custom_address"] = self.custom_address_var.get().strip()
        return c

    def save_settings(self):
        c = self.current_config()
        if not c["java_enabled"] and not c["bedrock_enabled"]:
            messagebox.showwarning("SliqServer", "Enable Java players, Bedrock players, or both.")
            return False
        c["max_players"] = max(1, int(c["max_players"]))
        c["memory_mb"] = max(512, int(c["memory_mb"]))
        self.config_data = c
        save_config(c)
        self._write_server_properties(c)
        self._update_address()
        self.players_lbl.config(text=f"{self.players} / {c['max_players']}")
        return True

    def _write_server_properties(self, c):
        props = {
            "motd": c["server_name"],
            "max-players": c["max_players"],
            "gamemode": c["gamemode"],
            "difficulty": c["difficulty"],
            "server-port": c["port"],
            "view-distance": c["view_distance"],
            "simulation-distance": c["simulation_distance"],
            "online-mode": str(bool(c["online_mode"])).lower(),
            "white-list": str(bool(c["whitelist"])).lower(),
            "pvp": str(bool(c["pvp"])).lower(),
            "enable-command-block": str(bool(c["command_blocks"])).lower(),
            "spawn-protection": c["spawn_protection"],
            "server-ip": "" if c["java_enabled"] else "127.0.0.1",
        }
        existing = {}
        p = SERVER / "server.properties"
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "=" in line and not line.startswith("#"):
                    k,v = line.split("=",1); existing[k]=v
        existing.update({k:str(v) for k,v in props.items()})
        p.write_text("\n".join(f"{k}={v}" for k,v in existing.items()) + "\n", encoding="utf-8")
        if c["eula"]:
            (SERVER / "eula.txt").write_text("eula=true\n", encoding="utf-8")

    def log(self, text):
        self.log_queue.put(text.rstrip())

    def _drain_logs(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.console.insert("end", line + "\n")
                self.console.see("end")
                self._parse_log(line)
        except queue.Empty:
            pass
        self.after(200, self._drain_logs)

    def _parse_log(self, line):
        if "Done (" in line and self.proc and self.proc.poll() is None:
            self.starting = False
        m = re.search(r"There are\s+(\d+)\s+of a max of\s+(\d+)\s+players online", line, re.I)
        if m:
            self.players = int(m.group(1)); self.max_seen = int(m.group(2))
        if " joined the game" in line:
            self.players += 1
        if " left the game" in line:
            self.players = max(0, self.players - 1)

    def _reader(self, proc):
        try:
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                self.log(line)
        except Exception as e:
            self.log(f"[SliqServer] Log reader: {e}")
        finally:
            code = proc.poll()
            if not self.stop_requested and code not in (None, 0):
                self.log(f"[SliqServer] Server stopped with code {code}")

    def java_major(self):
        try:
            p = subprocess.run(["java","-version"], capture_output=True, text=True, timeout=5)
            s = p.stderr + p.stdout
            m = re.search(r'version "(\d+)', s)
            return int(m.group(1)) if m else None
        except Exception:
            return None

    def required_java(self, version):
        if re.match(r"^26\.", version):
            return 25
        parts = version.split(".")
        try:
            minor = int(parts[1])
        except Exception:
            return 21
        if minor >= 20:
            return 21
        if minor >= 17:
            return 17
        return 11

    def install_server_async(self):
        if not self.save_settings():
            return
        threading.Thread(target=self._install_server, daemon=True).start()

    def _install_server(self):
        c = self.current_config()
        try:
            self.log(f"[SliqServer] Downloading {c['software']} for Minecraft {c['version']}…")
            if c["software"] == "Paper":
                builds = http_json(f"https://fill.papermc.io/v3/projects/paper/versions/{urllib.parse.quote(str(c['version']))}/builds")
                if not isinstance(builds, list) or not builds:
                    raise RuntimeError("No Paper build found for this version.")
                stable = [b for b in builds if str(b.get("channel","")).upper() == "STABLE"] or builds
                b = stable[0]
                url = b.get("downloads", {}).get("server:default", {}).get("url")
                if not url:
                    raise RuntimeError("Paper download URL missing.")
                download(url, SERVER/"server.jar")
            else:
                loaders = http_json(f"https://meta.fabricmc.net/v2/versions/loader/{urllib.parse.quote(str(c['version']))}")
                installers = http_json("https://meta.fabricmc.net/v2/versions/installer")
                if not loaders or not installers:
                    raise RuntimeError("No Fabric loader/installer found.")
                loader = loaders[0]["loader"]["version"]
                installer = next((x["version"] for x in installers if x.get("stable")), installers[0]["version"])
                url = f"https://meta.fabricmc.net/v2/versions/loader/{c['version']}/{loader}/{installer}/server/jar"
                download(url, SERVER/"server.jar")
            if c["bedrock_enabled"]:
                self._install_geyser(c["software"])
            self.log("[SliqServer] Server files are ready.")
        except Exception as e:
            self.log(f"[SliqServer] Download failed: {e}")
            self.after(0, lambda: messagebox.showerror("Download failed", str(e)))

    def _install_geyser(self, software):
        folder = SERVER / ("plugins" if software == "Paper" else "mods")
        folder.mkdir(exist_ok=True)
        kind = "spigot" if software == "Paper" else "fabric"
        self.log("[SliqServer] Installing Bedrock bridge (Geyser + Floodgate)…")
        download(f"https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/{kind}", folder/f"Geyser-{kind}.jar")
        download(f"https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/{kind}", folder/f"Floodgate-{kind}.jar")

    def start_server(self):
        if self.proc and self.proc.poll() is None:
            messagebox.showinfo("SliqServer", "Server is already running.")
            return
        if not self.save_settings():
            return
        c = self.current_config()
        if not c["eula"]:
            messagebox.showwarning("Minecraft EULA", "Accept the Minecraft EULA before starting.")
            return
        if not (SERVER/"server.jar").exists():
            if messagebox.askyesno("Server missing", "Server files are missing. Download them now?"):
                def install_then_start():
                    self._install_server()
                    self.after(0, self.start_server)
                threading.Thread(target=install_then_start, daemon=True).start()
            return
        major = self.java_major()
        needed = self.required_java(str(c["version"]))
        if major is None:
            messagebox.showerror("Java required", f"Java {needed}+ is required. Install Java and restart SliqServer.")
            return
        if major < needed:
            messagebox.showerror("Java too old", f"Minecraft {c['version']} needs Java {needed}+; detected Java {major}.")
            return
        if c["bedrock_enabled"] and c["software"] == "Paper":
            try:
                if not any((SERVER/"plugins").glob("Geyser-*.jar")):
                    self._install_geyser("Paper")
            except Exception as e:
                self.log(f"[SliqServer] Bedrock bridge warning: {e}")
        self.starting = True
        self.stop_requested = False
        self.players = 0
        mem = int(c["memory_mb"])
        cmd = [
            "java",
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
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
            if psutil:
                try:
                    self.proc_ps = psutil.Process(self.proc.pid)
                    self.proc_ps.cpu_percent(None)
                except Exception:
                    self.proc_ps = None
            self.started_at = time.time()
            threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
            self.log(f"[SliqServer] Starting {c['software']} {c['version']}…")
        except Exception as e:
            self.starting = False
            messagebox.showerror("Start failed", str(e))

    def send_command(self, command=None):
        cmd = command if command is not None else self.command_entry.get().strip()
        if not cmd:
            return
        if self.proc and self.proc.poll() is None and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
                if command is None:
                    self.command_entry.delete(0, "end")
            except Exception as e:
                self.log(f"[SliqServer] Command failed: {e}")
        elif command is None:
            messagebox.showinfo("SliqServer", "Server is offline.")

    def stop_server(self):
        if not (self.proc and self.proc.poll() is None):
            return
        self.stop_requested = True
        try:
            self.send_command("stop")
        except Exception:
            pass
        def force():
            time.sleep(12)
            if self.proc and self.proc.poll() is None:
                try: self.proc.terminate()
                except Exception: pass
        threading.Thread(target=force, daemon=True).start()

    def restart_server(self):
        if self.proc and self.proc.poll() is None:
            self.stop_server()
            def wait_restart():
                for _ in range(30):
                    if not (self.proc and self.proc.poll() is None):
                        self.after(0, self.start_server); return
                    time.sleep(0.5)
            threading.Thread(target=wait_restart, daemon=True).start()
        else:
            self.start_server()

    def _refresh_metrics(self):
        online = bool(self.proc and self.proc.poll() is None)
        if online:
            status = "● STARTING" if self.starting else "● ONLINE"
            color = "#f59e0b" if self.starting else "#39ff88"
            if not self.starting:
                self.send_command("list")
        else:
            status, color = "● OFFLINE", "#ef4444"
            self.players = 0
            self.proc_ps = None
        self.status_lbl.config(text=status, fg=color)
        maxp = int(self.vars["max_players"].get() or 10)
        self.players_lbl.config(text=f"{self.players} / {maxp}")
        cpu = 0.0; ram_mb = 0.0
        if online and self.proc_ps:
            try:
                cpu = self.proc_ps.cpu_percent(None)
                ram_mb = self.proc_ps.memory_info().rss / (1024*1024)
            except Exception:
                pass
        self.cpu_lbl.config(text=f"{cpu:.1f}%")
        self.ram_lbl.config(text=f"{ram_mb:.0f} MB")
        if online and hasattr(self, "started_at"):
            sec = int(time.time()-self.started_at)
            self.uptime_lbl.config(text=f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}")
        else:
            self.uptime_lbl.config(text="00:00:00")
        if psutil:
            try:
                self.system_lbl.config(text=f"CPU {psutil.cpu_percent(None):.0f}% · RAM {psutil.virtual_memory().percent:.0f}%")
            except Exception:
                pass
        self.after(2000, self._refresh_metrics)

    def refresh_world_size(self):
        def calc():
            total = 0
            for name in ("world","world_nether","world_the_end"):
                p = SERVER/name
                if p.exists():
                    for root, dirs, files in os.walk(p):
                        for fn in files:
                            try: total += (Path(root)/fn).stat().st_size
                            except Exception: pass
            units = ["B","KB","MB","GB","TB"]; size=float(total); i=0
            while size>=1024 and i<len(units)-1:
                size/=1024; i+=1
            self.after(0, lambda: self.world_lbl.config(text=f"{size:.1f} {units[i]}"))
        threading.Thread(target=calc, daemon=True).start()

    def clear_world(self):
        if not messagebox.askyesno("Delete world", "Do You Realy Wanna Delete This World?\n\nThis permanently deletes the map."):
            return
        if self.proc and self.proc.poll() is None:
            messagebox.showwarning("Stop server first", "Stop the server and wait until it is offline before deleting the world.")
            return
        for name in ("world","world_nether","world_the_end"):
            shutil.rmtree(SERVER/name, ignore_errors=True)
        self.world_lbl.config(text="0 B")
        self.log("[SliqServer] World deleted.")

    def create_backup(self):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = BACKUPS/f"world-{stamp}.zip"
        def work():
            try:
                with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
                    for name in ("world","world_nether","world_the_end"):
                        p=SERVER/name
                        if p.exists():
                            for f in p.rglob("*"):
                                if f.is_file():
                                    z.write(f, f.relative_to(SERVER))
                self.log(f"[SliqServer] Backup created: {dest.name}")
            except Exception as e:
                self.log(f"[SliqServer] Backup failed: {e}")
        threading.Thread(target=work, daemon=True).start()

    def add_jar(self, folder):
        path = filedialog.askopenfilename(filetypes=[("Java archives","*.jar")])
        if not path:
            return
        target = SERVER/folder
        target.mkdir(exist_ok=True)
        try:
            shutil.copy2(path, target/Path(path).name)
            self.log(f"[SliqServer] Added {Path(path).name} to {folder}.")
        except Exception as e:
            messagebox.showerror("Copy failed", str(e))

    def open_folder(self, path):
        path.mkdir(exist_ok=True)
        os.startfile(path)

if __name__ == "__main__":
    SliqServerApp().mainloop()
