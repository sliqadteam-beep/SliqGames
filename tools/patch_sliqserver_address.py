import re
import sys
from pathlib import Path


def replace_once(text, pattern, replacement, label):
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 match, got {count}")
    return new_text


def patch_windows(path: Path):
    text = path.read_text(encoding="utf-8")

    section = r'''    def _section_access(self):
        b = self.section("Server Address", "Easy setup for local play or a custom public hostname.")
        self.local_ip_var = tk.StringVar(value=local_ip())
        self.address_var = tk.StringVar()
        self.custom_address_var = tk.StringVar()
        self.dns_provider_var = tk.StringVar(value="Cloudflare")

        local_box = tk.Frame(b, bg="#101f34", padx=14, pady=12)
        local_box.pack(fill="x", pady=(0, 10))
        tk.Label(local_box, text="OPTION 1 · SAME WI-FI", fg="#39ff88", bg="#101f34",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(local_box, text="Use this when the players are connected to the same home network. No DNS setup is needed.",
                 fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9), wraplength=900, justify="left").pack(anchor="w", pady=(3, 8))
        local_row = tk.Frame(local_box, bg="#101f34")
        local_row.pack(fill="x")
        self.local_address_lbl = tk.Label(local_row, text="", fg="white", bg="#101f34", font=("Consolas", 13, "bold"))
        self.local_address_lbl.pack(side="left")
        tk.Button(local_row, text="COPY LOCAL ADDRESS", command=self._copy_local_address, bg="#18283d", fg="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="right")

        public_box = tk.Frame(b, bg="#101f34", padx=14, pady=12)
        public_box.pack(fill="x")
        tk.Label(public_box, text="OPTION 2 · CUSTOM / PUBLIC ADDRESS", fg="#64a8ff", bg="#101f34",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(public_box, text="Example: my-server.sliqado.org or play.yourdomain.com. The hostname only works after DNS and public access are configured.",
                 fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9), wraplength=900, justify="left").pack(anchor="w", pady=(3, 9))

        fields = tk.Frame(public_box, bg="#101f34")
        fields.pack(fill="x")
        left = tk.Frame(fields, bg="#101f34")
        left.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(left, text="Custom hostname (optional)", fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Entry(left, textvariable=self.custom_address_var, bg="#07111f", fg="white", insertbackground="white",
                 relief="flat", font=("Segoe UI", 10)).pack(fill="x", ipady=7, pady=(4, 0))

        right = tk.Frame(fields, bg="#101f34")
        right.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(right, text="Where is your DNS managed?", fg="#8ea0b8", bg="#101f34", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        provider = ttk.Combobox(right, textvariable=self.dns_provider_var,
                                values=["Cloudflare", "IONOS", "Other / Manual"], state="readonly")
        provider.pack(fill="x", ipady=5, pady=(4, 0))

        self.address_preview_lbl = tk.Label(public_box, text="", fg="white", bg="#07111f",
                                            font=("Consolas", 12, "bold"), justify="left", anchor="w",
                                            padx=12, pady=10)
        self.address_preview_lbl.pack(fill="x", pady=(10, 8))

        buttons = tk.Frame(public_box, bg="#101f34")
        buttons.pack(fill="x")
        tk.Button(buttons, text="USE SUGGESTED SLIQADO NAME", command=self._use_suggested_address,
                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), padx=10, pady=8).pack(side="left")
        tk.Button(buttons, text="COPY CUSTOM HOSTNAME", command=self._copy_custom_address,
                  bg="#18283d", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), padx=10, pady=8).pack(side="left", padx=7)
        tk.Button(buttons, text="SHOW 3 EASY SETUP STEPS", command=self._address_setup_help,
                  bg="#2563eb", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), padx=10, pady=8).pack(side="left")

        self.address_help_lbl = tk.Label(public_box,
            text="Important: a custom hostname does not make the server public by itself. You still need router port forwarding or a tunnel.",
            fg="#fbbf24", bg="#101f34", font=("Segoe UI", 9), wraplength=900, justify="left")
        self.address_help_lbl.pack(anchor="w", pady=(9, 0))

        self._update_address()

    def _use_suggested_address(self):
        name = self.vars.get("server_name")
        server_name = name.get() if name is not None else "my-server"
        self.custom_address_var.set(f"{slugify(server_name)}.sliqado.org")
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

    def _copy_custom_address(self):
        self._update_address()
        self._copy_text(self.address_var.get(), "Custom hostname")

    def _address_setup_help(self):
        self._update_address()
        host = self.address_var.get().strip()
        provider = self.dns_provider_var.get() or "your DNS provider"
        try:
            java_port = int(self.vars["port"].get())
        except Exception:
            java_port = 25565
        try:
            bedrock_port = int(self.vars["bedrock_port"].get())
        except Exception:
            bedrock_port = 19132
        extra = "\n\nCloudflare: set the Minecraft DNS record to DNS only (gray cloud), not proxied." if provider == "Cloudflare" else ""
        messagebox.showinfo(
            "Custom Server Address · 3 Easy Steps",
            f"1. OPEN {provider.upper()}\n"
            f"Open the DNS settings for the domain you control.\n\n"
            f"2. POINT THE NAME TO YOUR SERVER\n"
            f"Create the DNS record for:\n{host}\n"
            f"Point it to your public IP or to the hostname/IP given by your tunnel service.\n\n"
            f"3. MAKE MINECRAFT REACHABLE\n"
            f"Java: forward TCP {java_port}\n"
            f"Bedrock: forward UDP {bedrock_port}\n"
            f"If your router cannot port-forward, use a compatible tunnel instead.\n\n"
            f"After DNS updates, players can enter: {host}"
            f"{extra}\n\n"
            f"If you use a *.sliqado.org name, the DNS record must be created by whoever controls the sliqado.org DNS zone."
        )
'''

    text = replace_once(
        text,
        r'    def _section_access\(self\):\n.*?(?=\n    def _section_addons\(self\):)',
        section.rstrip(),
        "Windows address section",
    )

    update = r'''    def _update_address(self):
        standard = f"{slugify(self.vars['server_name'].get() if 'server_name' in self.vars else 'my-server')}.sliqado.org"
        custom = self.custom_address_var.get().strip()
        address = custom or standard
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
            title = "CUSTOM HOSTNAME" if custom else "SUGGESTED HOSTNAME"
            self.address_preview_lbl.config(
                text=f"{title}\n{address}\n\nThis name becomes usable after the DNS/public-access steps are completed."
            )
'''

    text = replace_once(
        text,
        r'    def _update_address\(self\):\n.*?(?=\n    def current_config\(self\):)',
        update.rstrip(),
        "Windows address updater",
    )

    path.write_text(text, encoding="utf-8")


def patch_android(path: Path):
    text = path.read_text(encoding="utf-8")

    section = r'''    private fun buildAddress(page: LinearLayout) {
        val box = section(page, "Server Address", "Two simple choices: same Wi-Fi or a custom public hostname.")

        addressValue = label("", white, 15f).apply {
            setBackgroundColor(field)
            setPadding(dp(12), dp(12), dp(12), dp(12))
        }
        box.addView(addressValue, match())

        box.addView(label("OPTION 1 · SAME WI-FI", green, 12f).apply {
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        box.addView(label("Works immediately for players on the same home network. No DNS setup is needed.", muted, 12f))
        val localRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        localRow.addView(actionButton("COPY LOCAL ADDRESS", field) {
            val port = intOf(javaPort, 25565, 1024, 65535)
            val value = if (port == 25565) localIpv4() else "${localIpv4()}:$port"
            copyAddressText(value, "Local address copied")
        }, weight())
        box.addView(localRow, match())

        box.addView(label("OPTION 2 · CUSTOM / PUBLIC ADDRESS", blue, 12f).apply {
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        box.addView(label("Example: my-server.sliqado.org or play.yourdomain.com. A hostname only works after DNS and public access are configured.", muted, 12f))

        customAddress = edit(box, "Custom hostname (optional)", "")
        val provider = spinner(box, "Where is your DNS managed?", listOf("Cloudflare", "IONOS", "Other / Manual"))

        box.addView(actionButton("USE SUGGESTED SLIQADO NAME", field) {
            val slug = serverName.text.toString().lowercase()
                .replace("_", "-").replace(Regex("[^a-z0-9-]+"), "-")
                .replace(Regex("-+"), "-").trim('-').ifBlank { "my-server" }
            customAddress.setText("$slug.sliqado.org")
            updateAddress()
        }, match(dp(48)))

        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(actionButton("COPY HOSTNAME", field) {
            updateAddress()
            copyAddressText(playerHostname(), "Hostname copied")
        }, weight())
        row.addView(actionButton("3 EASY SETUP STEPS", blue) {
            showAddressHelp(provider.selectedItem?.toString() ?: "Other / Manual")
        }, weight())
        box.addView(row, match())

        box.addView(actionButton("UPDATE ADDRESS PREVIEW", field) { updateAddress() }, match(dp(48)))
        box.addView(label("Important: DNS does not open your router. For friends outside your home, you still need port forwarding or a compatible tunnel.", amber, 12f))
    }

    private fun playerHostname(): String {
        val custom = customAddress.text.toString().trim()
        val slug = serverName.text.toString().lowercase()
            .replace("_", "-").replace(Regex("[^a-z0-9-]+"), "-")
            .replace(Regex("-+"), "-").trim('-').ifBlank { "my-server" }
        return custom.ifBlank { "$slug.sliqado.org" }
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

    private fun showAddressHelp(provider: String) {
        updateAddress()
        val host = playerHostname()
        val javaP = intOf(javaPort, 25565, 1024, 65535)
        val bedrockP = intOf(bedrockPort, 19132, 1024, 65535)
        val cloudflareNote = if (provider == "Cloudflare") "\n\nCloudflare: use DNS only (gray cloud), not proxied, for the Minecraft record." else ""
        AlertDialog.Builder(this)
            .setTitle("Custom Address · 3 Easy Steps")
            .setMessage(
                "1. OPEN $provider\nOpen the DNS settings for the domain you control.\n\n" +
                "2. POINT THE NAME TO YOUR SERVER\nCreate the DNS record for:\n$host\nPoint it to your public IP or your tunnel target.\n\n" +
                "3. MAKE MINECRAFT REACHABLE\nJava: TCP $javaP\nBedrock: UDP $bedrockP\nUse router port forwarding or a compatible tunnel.\n\n" +
                "After DNS updates, players can enter: $host" + cloudflareNote +
                "\n\nIf you use a *.sliqado.org name, the DNS record must be created by whoever controls the sliqado.org DNS zone."
            )
            .setPositiveButton("Got it", null)
            .show()
    }
'''

    text = replace_once(
        text,
        r'    private fun buildAddress\(page: LinearLayout\) \{\n.*?(?=\n    private fun buildAddons\(page: LinearLayout\))',
        section.rstrip(),
        "Android address section",
    )

    update = r'''    private fun updateAddress() {
        val addr = playerHostname()
        val local = localIpv4()
        val javaP = intOf(javaPort, 25565, 1024, 65535)
        val bedrockP = intOf(bedrockPort, 19132, 1024, 65535)
        val custom = customAddress.text.toString().trim().isNotBlank()
        val label = if (custom) "CUSTOM HOSTNAME" else "SUGGESTED HOSTNAME"
        addressValue.text =
            "SAME WI-FI · WORKS NOW\n$local:$javaP\n\n" +
            "$label · NEEDS DNS SETUP\n$addr\n\n" +
            "Java: TCP $javaP   ·   Bedrock: UDP $bedrockP"
    }
'''

    text = replace_once(
        text,
        r'    private fun updateAddress\(\) \{\n.*?(?=\n    private fun applyScreenOn\()',
        update.rstrip(),
        "Android address updater",
    )

    path.write_text(text, encoding="utf-8")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
        raise SystemExit("Usage: patch_sliqserver_address.py windows|android <source-file>")
    path = Path(sys.argv[2])
    if sys.argv[1] == "windows":
        patch_windows(path)
    else:
        patch_android(path)
    print(f"Patched simplified server address UI: {path}")


if __name__ == "__main__":
    main()
