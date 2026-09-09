import re
import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 exact match, got {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    new_text, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 regex match, got {count}")
    return new_text


def patch_windows(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    # Persist a separate Minecraft server-list description instead of reusing the server name.
    text = regex_once(
        text,
        r'(?m)^(\s*)"server_name":\s*"My Server",\s*$',
        '    "server_name": "My Server",\n    "server_description": "A SliqServer Minecraft server",',
        "Windows description default",
    )

    text = replace_once(
        text,
        '        self.vars["server_name"] = tk.StringVar()\n',
        '        self.vars["server_name"] = tk.StringVar()\n        self.vars["server_description"] = tk.StringVar()\n',
        "Windows description variable",
    )

    branding_block = r'''
        # Server-list branding. Minecraft Java reads server-icon.png from the server root.
        branding = tk.Frame(b, bg="#0d1b2d", highlightbackground="#1d3047", highlightthickness=1)
        branding.grid(row=98, column=0, columnspan=3, sticky="ew", padx=6, pady=(14, 4))
        branding.grid_columnconfigure(0, weight=1)
        tk.Label(branding, text="SERVER LIST BRANDING", fg="#39ff88", bg="#0d1b2d",
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
        tk.Label(branding, text="This is what players see in Minecraft's Multiplayer server list.", fg="#8ea0b8",
                 bg="#0d1b2d", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        desc_wrap = tk.Frame(branding, bg="#0d1b2d")
        desc_wrap.grid(row=2, column=0, sticky="ew", padx=6, pady=2)
        desc_wrap.grid_columnconfigure(0, weight=1)
        self._entry(desc_wrap, "Server description / MOTD", self.vars["server_description"], 0, 0)
        tk.Label(branding, text="Shown under the server name in Minecraft. Keep it short so it fits well in the server list.",
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
        tk.Label(branding, text="Any common image format works. SliqServer center-crops it and saves the exact 64×64 PNG Minecraft requires.",
                 fg="#8ea0b8", bg="#0d1b2d", font=("Segoe UI", 8), wraplength=900, justify="left").grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))
        self._refresh_server_icon_preview()

    def _choose_server_icon(self):
        source = filedialog.askopenfilename(
            title="Choose Minecraft server logo",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                ("PNG", "*.png"),
                ("All files", "*.*"),
            ],
        )
        if not source:
            return
        try:
            from PIL import Image, ImageOps
            with Image.open(source) as opened:
                img = opened.convert("RGBA")
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                img = ImageOps.fit(img, (64, 64), method=resample, centering=(0.5, 0.5))
                img.save(SERVER / "server-icon.png", format="PNG", optimize=True)
            self._refresh_server_icon_preview()
            messagebox.showinfo("SliqServer", "Server logo saved as a 64×64 PNG.\nRestart the Minecraft server if it is currently online so every client sees the new logo.")
        except Exception as exc:
            messagebox.showerror("SliqServer", f"Could not use this image:\n{exc}")

    def _remove_server_icon(self):
        icon = SERVER / "server-icon.png"
        try:
            if icon.exists():
                icon.unlink()
            self._refresh_server_icon_preview()
        except Exception as exc:
            messagebox.showerror("SliqServer", f"Could not remove the server logo:\n{exc}")

    def _refresh_server_icon_preview(self):
        icon = SERVER / "server-icon.png"
        if not hasattr(self, "server_icon_preview"):
            return
        if not icon.exists():
            self.server_icon_preview.config(image="", text="No logo")
            if hasattr(self, "server_icon_status"):
                self.server_icon_status.config(text="No server logo set", fg="#8ea0b8")
            self._server_icon_photo = None
            return
        try:
            from PIL import Image, ImageTk
            with Image.open(icon) as opened:
                img = opened.convert("RGBA").resize((64, 64), getattr(getattr(Image, "Resampling", Image), "LANCZOS"))
            self._server_icon_photo = ImageTk.PhotoImage(img)
            self.server_icon_preview.config(image=self._server_icon_photo, text="", padx=4, pady=4)
            if hasattr(self, "server_icon_status"):
                self.server_icon_status.config(text="✓ server-icon.png · 64×64", fg="#39ff88")
        except Exception:
            self.server_icon_preview.config(image="", text="Logo set")
            if hasattr(self, "server_icon_status"):
                self.server_icon_status.config(text="✓ server-icon.png", fg="#39ff88")
'''

    marker = '\n    def _section_access(self):'
    if marker not in text:
        raise SystemExit("Could not patch Windows branding UI: _section_access marker missing")
    text = text.replace(marker, '\n' + branding_block.rstrip() + marker, 1)

    write_prefix = '    def _write_server_properties(self, c):\n        props = {\n'
    write_replacement = '''    def _write_server_properties(self, c):
        _server_desc = str(c.get("server_description") or c.get("server_name") or "A Minecraft server")
        _server_desc = _server_desc.replace("\\r", " ").replace("\\n", "\\\\n")
        props = {
'''
    text = replace_once(text, write_prefix, write_replacement, "Windows properties description prep")
    text = replace_once(text, '            "motd": c["server_name"],\n', '            "motd": _server_desc,\n', "Windows MOTD")

    path.write_text(text, encoding="utf-8")


def patch_android(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '    private lateinit var serverName: EditText\n',
        '    private lateinit var serverName: EditText\n    private lateinit var serverDescription: EditText\n    private lateinit var serverIconStatus: TextView\n',
        "Android branding fields",
    )

    # Add the description directly beneath the server name.
    text = replace_once(
        text,
        '        serverName = edit(box, "Server name", "My Server")\n',
        '        serverName = edit(box, "Server name", "My Server")\n        serverDescription = edit(box, "Server description / MOTD", "A SliqServer Minecraft server")\n',
        "Android description control",
    )

    logo_ui = r'''        serverIconStatus = label("No server logo set", muted, 12f)
        box.addView(serverIconStatus, match())
        val logoRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        logoRow.addView(actionButton("CHOOSE SERVER LOGO", blue) { chooseServerIcon() }, weight())
        logoRow.addView(actionButton("REMOVE LOGO", field) { removeServerIcon() }, weight())
        box.addView(logoRow, match(dp(50)))
        box.addView(label("The image is center-cropped and converted to Minecraft's required 64×64 server-icon.png.", muted, 11f))
        updateServerIconStatus()
'''

    # Put logo controls immediately after Spawn protection, before the switches.
    text = regex_once(
        text,
        r'(\s*spawnProtection\s*=\s*edit\(box,\s*"Spawn protection",\s*"16",\s*true\)\s*\n)',
        lambda_text := None if False else '',
        "unused",
    ) if False else text
    spawn_match = re.search(r'(?m)^\s*spawnProtection\s*=\s*edit\(box,\s*"Spawn protection",\s*"16",\s*true\)\s*$', text)
    if not spawn_match:
        raise SystemExit("Could not patch Android logo UI: Spawn protection field missing")
    insert_pos = text.find('\n', spawn_match.end())
    if insert_pos < 0:
        insert_pos = spawn_match.end()
    else:
        insert_pos += 1
    text = text[:insert_pos] + '\n' + logo_ui + text[insert_pos:]

    text = replace_once(
        text,
        '        serverName.setText(prefs.getString("server_name","My Server"))\n',
        '        serverName.setText(prefs.getString("server_name","My Server"))\n        serverDescription.setText(prefs.getString("server_description","A SliqServer Minecraft server"))\n        updateServerIconStatus()\n',
        "Android description load",
    )

    text = replace_once(
        text,
        '            .putString("server_name", serverName.text.toString().trim().ifBlank { "My Server" })\n',
        '            .putString("server_name", serverName.text.toString().trim().ifBlank { "My Server" })\n            .putString("server_description", serverDescription.text.toString().trim().ifBlank { serverName.text.toString().trim().ifBlank { "My Server" } })\n',
        "Android description save",
    )

    # Re-apply the copied icon whenever settings are saved, so Termux always has server-icon.png.
    text = replace_once(
        text,
        '        writeServerProperties()\n        updateAddress()\n',
        '        writeServerProperties()\n        applyServerIcon()\n        updateAddress()\n',
        "Android icon apply on save",
    )

    text = replace_once(
        text,
        '        val name = serverName.text.toString().trim().ifBlank { "My Server" }\n        val props = """\n',
        '        val name = serverName.text.toString().trim().ifBlank { "My Server" }\n        val description = serverDescription.text.toString().trim().ifBlank { name }.replace("\\r", " ").replace("\\n", "\\\\n")\n        val props = """\n',
        "Android description prep",
    )
    text = replace_once(text, 'motd=$name\n', 'motd=$description\n', "Android MOTD")

    branding_methods = r'''
    private fun chooseServerIcon() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
        }
        startActivityForResult(intent, 4404)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 4404 || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        try {
            val source = contentResolver.openInputStream(uri)?.use { android.graphics.BitmapFactory.decodeStream(it) }
                ?: throw IllegalArgumentException("Android could not open that image")
            if (source.width < 1 || source.height < 1) throw IllegalArgumentException("Invalid image")
            val side = minOf(source.width, source.height)
            val x = (source.width - side) / 2
            val y = (source.height - side) / 2
            val square = android.graphics.Bitmap.createBitmap(source, x, y, side, side)
            val icon = android.graphics.Bitmap.createScaledBitmap(square, 64, 64, true)
            val output = java.io.ByteArrayOutputStream()
            icon.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, output)
            val encoded = android.util.Base64.encodeToString(output.toByteArray(), android.util.Base64.NO_WRAP)
            prefs.edit().putString("server_icon_b64", encoded).apply()
            if (square !== source) square.recycle()
            if (icon !== square && icon !== source) icon.recycle()
            source.recycle()
            applyServerIcon()
            updateServerIconStatus()
            toast("Server logo saved · 64×64 PNG")
        } catch (e: Exception) {
            AlertDialog.Builder(this)
                .setTitle("Could not use this logo")
                .setMessage(e.message ?: e.toString())
                .setPositiveButton("OK", null)
                .show()
        }
    }

    private fun applyServerIcon() {
        val encoded = prefs.getString("server_icon_b64", "") ?: ""
        if (encoded.isBlank()) {
            TermuxBridge.run(this, "rm -f ~/sliqserver/server-icon.png")
            return
        }
        val cmd = "mkdir -p ~/sliqserver; printf %s ${TermuxBridge.q(encoded)} | base64 -d > ~/sliqserver/server-icon.png"
        TermuxBridge.run(this, cmd)
    }

    private fun removeServerIcon() {
        prefs.edit().remove("server_icon_b64").apply()
        TermuxBridge.run(this, "rm -f ~/sliqserver/server-icon.png")
        updateServerIconStatus()
        toast("Server logo removed")
    }

    private fun updateServerIconStatus() {
        if (!::serverIconStatus.isInitialized) return
        val hasLogo = !(prefs.getString("server_icon_b64", "") ?: "").isBlank()
        serverIconStatus.text = if (hasLogo) "✓ Server logo set · 64×64 PNG" else "No server logo set"
        serverIconStatus.setTextColor(if (hasLogo) green else muted)
    }
'''

    marker = '\n    private fun buildAddress(page: LinearLayout) {'
    if marker not in text:
        raise SystemExit("Could not patch Android branding methods: buildAddress marker missing")
    text = text.replace(marker, '\n' + branding_methods.rstrip() + marker, 1)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
        raise SystemExit("Usage: apply_server_branding_patch.py windows|android <source-file>")
    path = Path(sys.argv[2])
    if not path.exists():
        raise SystemExit(f"Source file not found: {path}")
    if sys.argv[1] == "windows":
        patch_windows(path)
    else:
        patch_android(path)
    print(f"Applied server logo + description branding patch: {path}")


if __name__ == "__main__":
    main()
