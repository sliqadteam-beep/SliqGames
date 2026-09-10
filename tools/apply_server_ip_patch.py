import re
import sys
from pathlib import Path


def replace_once(text: str, pattern: str, replacement: str, label: str, flags=re.S) -> str:
    new, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 match, got {count}")
    return new


def ensure_windows_imports(text: str) -> str:
    if "import urllib.request\n" not in text:
        lines = text.splitlines(True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_at = i + 1
        lines.insert(insert_at, "import urllib.request\n")
        text = "".join(lines)
    if "import threading\n" not in text:
        lines = text.splitlines(True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_at = i + 1
        lines.insert(insert_at, "import threading\n")
        text = "".join(lines)
    return text


def patch_windows(path: Path) -> None:
    text = ensure_windows_imports(path.read_text(encoding="utf-8"))

    text = text.replace(
        '        self.address_var = tk.StringVar()\n',
        '        self.address_var = tk.StringVar()\n        self.public_ip_var = tk.StringVar(value="Checking…")\n',
        1,
    )

    marker = '''        local_box.pack(fill="x", pady=(0, 10))\n'''
    if marker not in text:
        raise SystemExit("Could not find Windows local IP box")

    # Keep the existing local-address card, then add a dedicated public-IP card before the hostname card.
    insertion_point = '''        public_box = tk.Frame(b, bg="#101f34", padx=14, pady=12)\n'''
    public_ip_ui = '''        ip_box = tk.Frame(b, bg="#101f34", padx=14, pady=12)\n        ip_box.pack(fill="x", pady=(0, 10))\n        tk.Label(ip_box, text="PUBLIC SERVER IP", fg="#fbbf24", bg="#101f34",\n                 font=("Segoe UI", 9, "bold")).pack(anchor="w")\n        tk.Label(ip_box, text="Your internet-facing IP. Friends outside your network need this IP or a working Sliqado hostname/tunnel.",\n                 fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9), wraplength=900, justify="left").pack(anchor="w", pady=(3, 8))\n        ip_row = tk.Frame(ip_box, bg="#101f34")\n        ip_row.pack(fill="x")\n        self.public_ip_lbl = tk.Label(ip_row, textvariable=self.public_ip_var, fg="white", bg="#101f34",\n                                     font=("Consolas", 13, "bold"))\n        self.public_ip_lbl.pack(side="left")\n        tk.Button(ip_row, text="COPY PUBLIC IP", command=self._copy_public_ip,\n                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"),\n                  padx=12, pady=7).pack(side="right")\n        tk.Button(ip_row, text="REFRESH IP", command=self._refresh_public_ip,\n                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"),\n                  padx=12, pady=7).pack(side="right", padx=(0, 8))\n\n'''
    if insertion_point not in text:
        raise SystemExit("Could not find Windows public hostname box")
    text = text.replace(insertion_point, public_ip_ui + insertion_point, 1)

    # Make the local IP meaning explicit.
    text = text.replace('text="SAME WI-FI"', 'text="LOCAL SERVER IP · SAME WI-FI"', 1)

    method_anchor = '''    def _copy_server_address(self):\n'''
    methods = '''    def _copy_public_ip(self):\n        value = self.public_ip_var.get().strip() if hasattr(self, "public_ip_var") else ""\n        if value and value not in {"Checking…", "Unavailable"}:\n            self._copy_text(value, "Public IP")\n\n    def _refresh_public_ip(self):\n        if not hasattr(self, "public_ip_var"):\n            return\n        self.public_ip_var.set("Checking…")\n\n        def work():\n            try:\n                req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "SliqServer/4"})\n                with urllib.request.urlopen(req, timeout=5) as response:\n                    value = response.read(128).decode("utf-8", "replace").strip()\n                if not re.fullmatch(r"[0-9a-fA-F:.]+", value):\n                    value = "Unavailable"\n            except Exception:\n                value = "Unavailable"\n            self.after(0, lambda v=value: self.public_ip_var.set(v))\n\n        threading.Thread(target=work, daemon=True).start()\n\n'''
    if method_anchor not in text:
        raise SystemExit("Could not find Windows address copy method")
    text = text.replace(method_anchor, methods + method_anchor, 1)

    # Refresh once when the network section opens.
    text = text.replace('        self._update_address()\n\n    def _copy_text',
                        '        self._update_address()\n        self._refresh_public_ip()\n\n    def _copy_text', 1)

    path.write_text(text, encoding="utf-8")


def patch_android(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    decl = '    private lateinit var addressValue: TextView\n'
    if decl not in text:
        raise SystemExit("Could not find Android addressValue declaration")
    text = text.replace(decl, decl + '    private lateinit var publicIpValue: TextView\n', 1)

    # Rename same-Wi-Fi label to make it obvious that this is the local server IP.
    text = text.replace('label("SAME WI-FI", green, 12f)', 'label("LOCAL SERVER IP · SAME WI-FI", green, 12f)', 1)

    hostname_heading = '        box.addView(label("YOUR SLIQADO SERVER ADDRESS", blue, 12f).apply {\n'
    public_ui = '''        box.addView(label("PUBLIC SERVER IP", amber, 12f).apply {\n            setTypeface(typeface, android.graphics.Typeface.BOLD)\n        })\n        box.addView(label("Your internet-facing IP. Friends outside your network need this IP or a working Sliqado hostname/tunnel.", muted, 12f))\n        publicIpValue = label("Checking…", white, 15f).apply {\n            setBackgroundColor(field)\n            setPadding(dp(12), dp(12), dp(12), dp(12))\n        }\n        box.addView(publicIpValue, match())\n        val ipRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }\n        ipRow.addView(actionButton("COPY PUBLIC IP", field) {\n            val value = publicIpValue.text.toString().trim()\n            if (value.isNotBlank() && value != "Checking…" && value != "Unavailable") {\n                copyAddressText(value, "Public IP copied")\n            }\n        }, weight())\n        ipRow.addView(actionButton("REFRESH IP", field) { refreshPublicIp() }, weight())\n        box.addView(ipRow, match())\n\n'''
    if hostname_heading not in text:
        raise SystemExit("Could not find Android Sliqado hostname heading")
    text = text.replace(hostname_heading, public_ui + hostname_heading, 1)

    # Refresh the public IP when the section is created.
    text = text.replace(
        '        serverName.addTextChangedListener(object : android.text.TextWatcher {',
        '        refreshPublicIp()\n\n        serverName.addTextChangedListener(object : android.text.TextWatcher {',
        1,
    )

    method_anchor = '    private fun playerHostname(): String {\n'
    method = '''    private fun refreshPublicIp() {\n        if (!::publicIpValue.isInitialized) return\n        publicIpValue.text = "Checking…"\n        Thread {\n            val value = try {\n                val connection = (java.net.URL("https://api.ipify.org").openConnection() as java.net.HttpURLConnection).apply {\n                    connectTimeout = 5000\n                    readTimeout = 5000\n                    requestMethod = "GET"\n                    setRequestProperty("User-Agent", "SliqServer/4")\n                }\n                try {\n                    connection.inputStream.bufferedReader().use { it.readText().trim() }.ifBlank { "Unavailable" }\n                } finally {\n                    connection.disconnect()\n                }\n            } catch (_: Exception) {\n                "Unavailable"\n            }\n            runOnUiThread {\n                if (::publicIpValue.isInitialized) publicIpValue.text = value\n            }\n        }.start()\n    }\n\n'''
    if method_anchor not in text:
        raise SystemExit("Could not find Android playerHostname method")
    text = text.replace(method_anchor, method + method_anchor, 1)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
        raise SystemExit("Usage: apply_server_ip_patch.py windows|android <source-file>")
    path = Path(sys.argv[2])
    if sys.argv[1] == "windows":
        patch_windows(path)
    else:
        patch_android(path)
    print(f"Applied server IP display patch: {path}")


if __name__ == "__main__":
    main()
