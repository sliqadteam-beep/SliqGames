import re
import sys
from pathlib import Path
import patch_sliqserver_address as patcher


def safe_replace_once(text, pattern, replacement, label):
    new_text, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 match, got {count}")
    return new_text


def predefined_windows(path: Path):
    text = path.read_text(encoding="utf-8")

    section = r'''    def _section_access(self):
        b = self.section("Server Address", "Your Sliqado address is generated automatically from the server name.")
        self.local_ip_var = tk.StringVar(value=local_ip())
        self.address_var = tk.StringVar()
        # Kept only for compatibility with older saved settings. Custom addresses are no longer used.
        self.custom_address_var = tk.StringVar(value="")

        local_box = tk.Frame(b, bg="#101f34", padx=14, pady=12)
        local_box.pack(fill="x", pady=(0, 10))
        tk.Label(local_box, text="SAME WI-FI", fg="#39ff88", bg="#101f34",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(local_box, text="Use this address for players on the same home network.",
                 fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 8))
        local_row = tk.Frame(local_box, bg="#101f34")
        local_row.pack(fill="x")
        self.local_address_lbl = tk.Label(local_row, text="", fg="white", bg="#101f34",
                                          font=("Consolas", 13, "bold"))
        self.local_address_lbl.pack(side="left")
        tk.Button(local_row, text="COPY LOCAL ADDRESS", command=self._copy_local_address,
                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=7).pack(side="right")

        public_box = tk.Frame(b, bg="#101f34", padx=14, pady=12)
        public_box.pack(fill="x")
        tk.Label(public_box, text="YOUR SLIQADO SERVER ADDRESS", fg="#64a8ff", bg="#101f34",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(public_box,
                 text="No hostname setup inside SliqServer is needed. The address is created from your server name automatically.",
                 fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9), wraplength=900,
                 justify="left").pack(anchor="w", pady=(3, 9))

        self.address_preview_lbl = tk.Label(public_box, text="", fg="white", bg="#07111f",
                                            font=("Consolas", 14, "bold"), justify="left",
                                            anchor="w", padx=12, pady=12)
        self.address_preview_lbl.pack(fill="x", pady=(0, 8))

        buttons = tk.Frame(public_box, bg="#101f34")
        buttons.pack(fill="x")
        tk.Button(buttons, text="COPY SERVER ADDRESS", command=self._copy_server_address,
                  bg="#2563eb", fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=8).pack(side="left")
        tk.Button(buttons, text="HOW DOES THIS WORK?", command=self._address_setup_help,
                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=8).pack(side="left", padx=8)

        self.address_help_lbl = tk.Label(public_box,
            text="The hostname is automatic. Internet access still needs sliqado.org DNS/tunnel routing to this device.",
            fg="#fbbf24", bg="#101f34", font=("Segoe UI", 9), wraplength=900, justify="left")
        self.address_help_lbl.pack(anchor="w", pady=(9, 0))

        self._update_address()

    def _copy_text(self, value, label="Address"):
        value = str(value).strip()
        if not value:
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()
        if hasattr(self, "address_help_lbl"):
            self.address_help_lbl.config(text=f"✓ {label} copied to clipboard.", fg="#39ff88")

    def _copy_local_address(self):
        try:
            port = int(self.vars["port"].get())
        except Exception:
            port = 25565
        address = self.local_ip_var.get().strip()
        if port != 25565:
            address = f"{address}:{port}"
        self._copy_text(address, "Local address")

    def _copy_server_address(self):
        self._update_address()
        self._copy_text(self.address_var.get(), "Server address")

    def _address_setup_help(self):
        self._update_address()
        host = self.address_var.get().strip()
        try:
            java_port = int(self.vars["port"].get())
        except Exception:
            java_port = 25565
        try:
            bedrock_port = int(self.vars["bedrock_port"].get())
        except Exception:
            bedrock_port = 19132
        messagebox.showinfo(
            "Automatic Sliqado Address",
            f"Your server name automatically creates this address:\n\n{host}\n\n"
            f"Example: 'My Cool Server' becomes 'my-cool-server.sliqado.org'.\n\n"
            f"You do not need to type a custom hostname in SliqServer.\n\n"
            f"For friends outside your home to actually connect, sliqado.org must route this hostname to your public IP or tunnel, and the Minecraft ports must be reachable.\n\n"
            f"Java: TCP {java_port}\nBedrock: UDP {bedrock_port}"
        )
'''

    text = safe_replace_once(
        text,
        r'    def _section_access\(self\):\n.*?(?=\n    def _section_addons\(self\):)',
        section.rstrip(),
        "Windows predefined address section",
    )

    update = r'''    def _update_address(self):
        server_name = self.vars['server_name'].get() if 'server_name' in self.vars else 'my-server'
        address = f"{slugify(server_name)}.sliqado.org"
        self.address_var.set(address)
        try:
            port = int(self.vars["port"].get())
        except Exception:
            port = 25565
        local = self.local_ip_var.get().strip() if hasattr(self, "local_ip_var") else local_ip()
        local_display = local if port == 25565 else f"{local}:{port}"
        if hasattr(self, "local_address_lbl"):
            self.local_address_lbl.config(text=local_display)
        if hasattr(self, "address_preview_lbl"):
            self.address_preview_lbl.config(
                text=f"{address}\n\nGenerated automatically from: {server_name or 'my-server'}"
            )
'''

    text = safe_replace_once(
        text,
        r'    def _update_address\(self\):\n.*?(?=\n    def current_config\(self\):)',
        update.rstrip(),
        "Windows predefined address updater",
    )

    path.write_text(text, encoding="utf-8")


def predefined_android(path: Path):
    text = path.read_text(encoding="utf-8")

    section = r'''    private fun buildAddress(page: LinearLayout) {
        val box = section(page, "Server Address", "Your Sliqado address is generated automatically from the server name.")

        // Kept only so older saved settings remain compatible. There is no custom-address field anymore.
        customAddress = EditText(this).apply { visibility = android.view.View.GONE }

        addressValue = label("", white, 15f).apply {
            setBackgroundColor(field)
            setPadding(dp(12), dp(12), dp(12), dp(12))
        }
        box.addView(addressValue, match())

        box.addView(label("SAME WI-FI", green, 12f).apply {
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        box.addView(label("Use this address for players on the same home network.", muted, 12f))
        box.addView(actionButton("COPY LOCAL ADDRESS", field) {
            val port = intOf(javaPort, 25565, 1024, 65535)
            val value = if (port == 25565) localIpv4() else "${localIpv4()}:$port"
            copyAddressText(value, "Local address copied")
        }, match(dp(48)))

        box.addView(label("YOUR SLIQADO SERVER ADDRESS", blue, 12f).apply {
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        box.addView(label("It is created automatically from the server name. You do not need to type a hostname.", muted, 12f))

        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(actionButton("COPY SERVER ADDRESS", blue) {
            updateAddress()
            copyAddressText(playerHostname(), "Server address copied")
        }, weight())
        row.addView(actionButton("HOW DOES THIS WORK?", field) {
            showAddressHelp()
        }, weight())
        box.addView(row, match())

        box.addView(label("For internet access, sliqado.org still has to route this hostname to your public IP or tunnel.", amber, 12f))

        serverName.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: android.text.Editable?) { updateAddress() }
        })
    }

    private fun playerHostname(): String {
        val slug = serverName.text.toString().lowercase()
            .replace("_", "-").replace(Regex("[^a-z0-9-]+"), "-")
            .replace(Regex("-+"), "-").trim('-').ifBlank { "my-server" }
        return "$slug.sliqado.org"
    }

    private fun localIpv4(): String {
        return try {
            val interfaces = java.util.Collections.list(java.net.NetworkInterface.getNetworkInterfaces())
            for (intf in interfaces) {
                for (addr in java.util.Collections.list(intf.inetAddresses)) {
                    if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) return addr.hostAddress ?: "Unavailable"
                }
            }
            "Unavailable"
        } catch (_: Exception) {
            "Unavailable"
        }
    }

    private fun copyAddressText(value: String, message: String) {
        val clipboard = getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        clipboard.setPrimaryClip(android.content.ClipData.newPlainText("SliqServer address", value))
        toast(message)
    }

    private fun showAddressHelp() {
        updateAddress()
        val host = playerHostname()
        val javaP = intOf(javaPort, 25565, 1024, 65535)
        val bedrockP = intOf(bedrockPort, 19132, 1024, 65535)
        AlertDialog.Builder(this)
            .setTitle("Automatic Sliqado Address")
            .setMessage(
                "Your server name automatically creates this address:\n\n$host\n\n" +
                "Example: My Cool Server becomes my-cool-server.sliqado.org.\n\n" +
                "You do not need to enter a custom hostname.\n\n" +
                "For friends outside your home to connect, sliqado.org must route this hostname to your public IP or tunnel and the Minecraft ports must be reachable.\n\n" +
                "Java: TCP $javaP\nBedrock: UDP $bedrockP"
            )
            .setPositiveButton("Got it", null)
            .show()
    }
'''

    text = safe_replace_once(
        text,
        r'    private fun buildAddress\(page: LinearLayout\) \{\n.*?(?=\n    private fun buildAddons\(page: LinearLayout\))',
        section.rstrip(),
        "Android predefined address section",
    )

    update = r'''    private fun updateAddress() {
        val addr = playerHostname()
        val local = localIpv4()
        val javaP = intOf(javaPort, 25565, 1024, 65535)
        val bedrockP = intOf(bedrockPort, 19132, 1024, 65535)
        addressValue.text =
            "SAME WI-FI\n$local:$javaP\n\n" +
            "AUTOMATIC SLIQADO ADDRESS\n$addr\n\n" +
            "Java: TCP $javaP   ·   Bedrock: UDP $bedrockP"
    }
'''

    text = safe_replace_once(
        text,
        r'    private fun updateAddress\(\) \{\n.*?(?=\n    private fun applyScreenOn\()',
        update.rstrip(),
        "Android predefined address updater",
    )

    path.write_text(text, encoding="utf-8")


patcher.replace_once = safe_replace_once

if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
    raise SystemExit("Usage: apply_address_patch.py windows|android <source-file>")

path = Path(sys.argv[2])
if sys.argv[1] == "windows":
    patcher.patch_windows(path)
    predefined_windows(path)
else:
    patcher.patch_android(path)
    predefined_android(path)

print(f"Applied automatic Sliqado server address UI: {path}")
