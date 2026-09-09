import re
import sys
from pathlib import Path


def one(text: str, pattern: str, replacement: str, label: str) -> str:
    out, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, got {count}")
    return out


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # Persistent config default.
    if '"server_description"' not in text:
        text = one(
            text,
            r'^\s*"server_name"\s*:\s*"My Server",\s*$',
            '    "server_name": "My Server",\n    "server_description": "A SliqServer Minecraft server",',
            "description default",
        )

    branding = r'''
        # Minecraft server-list branding.
        self.server_description_var = tk.StringVar(
            value=str(self.config_data.get("server_description") or self.config_data.get("server_name") or "A SliqServer Minecraft server")
        )
        branding = tk.Frame(b, bg="#0d1b2d", highlightbackground="#1d3047", highlightthickness=1)
        branding.grid(row=98, column=0, columnspan=3, sticky="ew", padx=6, pady=(14, 4))
        branding.grid_columnconfigure(0, weight=1)
        tk.Label(branding, text="SERVER LIST BRANDING", fg="#39ff88", bg="#0d1b2d",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
        tk.Label(branding, text="Customize how your server appears in Minecraft's Multiplayer list.",
                 fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        desc_wrap = tk.Frame(branding, bg="#0d1b2d")
        desc_wrap.grid(row=2, column=0, sticky="ew", padx=6, pady=2)
        desc_wrap.grid_columnconfigure(0, weight=1)
        self._entry(desc_wrap, "Server description / MOTD", self.server_description_var, 0, 0)
        tk.Label(branding, text="Shown below the server name in Minecraft. A short description works best.",
                 fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 8)).grid(row=3, column=0, sticky="w", padx=12, pady=(0, 8))

        logo_row = tk.Frame(branding, bg="#0d1b2d")
        logo_row.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.server_icon_preview = tk.Label(logo_row, text="No logo", fg="#8ea0b8", bg="#101f34",
                                            font=("Segoe UI", 9), padx=12, pady=12)
        self.server_icon_preview.pack(side="left", padx=(0, 10))
        logo_buttons = tk.Frame(logo_row, bg="#0d1b2d")
        logo_buttons.pack(side="left", fill="x", expand=True)
        tk.Button(logo_buttons, text="CHOOSE SERVER LOGO", command=self._choose_server_icon,
                  bg="#2563eb", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), padx=12, pady=8).pack(side="left")
        tk.Button(logo_buttons, text="REMOVE LOGO", command=self._remove_server_icon,
                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), padx=12, pady=8).pack(side="left", padx=8)
        self.server_icon_status = tk.Label(logo_buttons, text="", fg="#8ea0b8", bg="#0d1b2d",
                                           font=("Segoe UI", 9), justify="left")
        self.server_icon_status.pack(side="left", padx=6)
        tk.Label(branding,
                 text="Choose PNG, JPG, WEBP, BMP or GIF. SliqServer center-crops it and creates Minecraft's required 64×64 server-icon.png.",
                 fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 8), wraplength=900, justify="left").grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))
        self._refresh_server_icon_preview()

    def _choose_server_icon(self):
        source = filedialog.askopenfilename(
            title="Choose Minecraft server logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("PNG", "*.png"), ("All files", "*.*")],
        )
        if not source:
            return
        try:
            from PIL import Image, ImageOps
            with Image.open(source) as opened:
                image = opened.convert("RGBA")
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                image = ImageOps.fit(image, (64, 64), method=resample, centering=(0.5, 0.5))
                image.save(SERVER / "server-icon.png", format="PNG", optimize=True)
            self._refresh_server_icon_preview()
            messagebox.showinfo(
                "SliqServer",
                "Server logo saved as a 64×64 PNG.\n\nRestart the Minecraft server if it is online so clients refresh the logo."
            )
        except Exception as exc:
            messagebox.showerror("SliqServer", f"Could not use this image:\n{exc}")

    def _remove_server_icon(self):
        try:
            icon = SERVER / "server-icon.png"
            if icon.exists():
                icon.unlink()
            self._refresh_server_icon_preview()
        except Exception as exc:
            messagebox.showerror("SliqServer", f"Could not remove the server logo:\n{exc}")

    def _refresh_server_icon_preview(self):
        if not hasattr(self, "server_icon_preview"):
            return
        icon = SERVER / "server-icon.png"
        if not icon.exists():
            self._server_icon_photo = None
            self.server_icon_preview.config(image="", text="No logo", padx=12, pady=12)
            if hasattr(self, "server_icon_status"):
                self.server_icon_status.config(text="No server logo set", fg="#8ea0b8")
            return
        try:
            from PIL import Image, ImageTk
            with Image.open(icon) as opened:
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                image = opened.convert("RGBA").resize((64, 64), resample)
            self._server_icon_photo = ImageTk.PhotoImage(image)
            self.server_icon_preview.config(image=self._server_icon_photo, text="", padx=4, pady=4)
            self.server_icon_status.config(text="✓ server-icon.png · 64×64", fg="#39ff88")
        except Exception:
            self.server_icon_preview.config(image="", text="Logo set")
            self.server_icon_status.config(text="✓ server-icon.png", fg="#39ff88")
'''

    marker = "\n    def _section_access(self):"
    if marker not in text:
        raise SystemExit("branding UI marker not found")
    text = text.replace(marker, "\n" + branding.rstrip() + marker, 1)

    # Save the standalone description regardless of how V4 creates its ordinary self.vars controls.
    current = re.search(r'(?ms)^    def current_config\(self\):\n.*?(?=^    def save_settings\(self\):)', text)
    if not current:
        raise SystemExit("current_config method not found")
    method = current.group(0)
    method2, count = re.subn(
        r'(?m)^(\s*)return c\s*$',
        lambda m: m.group(1) + 'c["server_description"] = self.server_description_var.get().strip() or str(c.get("server_name") or "My Server")\n' + m.group(1) + 'return c',
        method,
        count=1,
    )
    if count != 1:
        raise SystemExit("current_config return not found")
    text = text[:current.start()] + method2 + text[current.end():]

    # Make the Minecraft MOTD use the new description. Match any V4 expression on the motd line.
    writer = re.search(r'(?ms)^    def _write_server_properties\(self, c\):\n.*?(?=^    def \w+\()', text)
    if not writer:
        raise SystemExit("server.properties writer not found")
    w = writer.group(0)
    def_line = '    def _write_server_properties(self, c):\n'
    prep = (
        def_line +
        '        _server_desc = str(c.get("server_description") or c.get("server_name") or "A Minecraft server")\n' +
        '        _server_desc = _server_desc.replace("\\r", " ").replace("\\n", "\\\\n")\n'
    )
    if def_line not in w:
        raise SystemExit("server.properties writer signature changed")
    w = w.replace(def_line, prep, 1)

    motd_pattern = re.compile(r'(?m)^(\s*)["\']motd["\']\s*:\s*.*?,\s*$')
    w2, motd_count = motd_pattern.subn(lambda m: m.group(1) + '"motd": _server_desc,', w, count=1)
    if motd_count == 0:
        # Fallback for a writer that builds props then writes/merges them later.
        existing = re.search(r'(?m)^(\s*)existing\s*=\s*\{', w)
        if not existing:
            raise SystemExit("Could not find a MOTD property or props merge point")
        indent = existing.group(1)
        w2 = w[:existing.start()] + indent + 'props["motd"] = _server_desc\n' + w[existing.start():]
    text = text[:writer.start()] + w2 + text[writer.end():]

    path.write_text(text, encoding="utf-8")
    print(f"Applied robust Windows server branding patch: {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_windows_server_branding_v4.py <source-file>")
    patch(Path(sys.argv[1]))
