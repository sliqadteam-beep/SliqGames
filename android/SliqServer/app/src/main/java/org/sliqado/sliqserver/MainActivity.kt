package org.sliqado.sliqserver

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.NetworkInterface
import java.net.URL
import java.net.URLEncoder
import java.util.Collections

class MainActivity : Activity() {
    private val bg = Color.rgb(7, 17, 31)
    private val panel = Color.rgb(13, 27, 45)
    private val panel2 = Color.rgb(23, 44, 72)
    private val blue = Color.rgb(37, 99, 235)
    private val green = Color.rgb(34, 197, 94)
    private val red = Color.rgb(220, 38, 38)
    private val white = Color.WHITE
    private val muted = Color.rgb(159, 176, 199)
    private lateinit var root: LinearLayout
    private val prefs by lazy { getSharedPreferences("sliqserver", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg
        showHome()
    }

    private fun shellBase(): String {
        val version = prefs.getString("version", "26.2") ?: "26.2"
        val name = prefs.getString("server_name", "Custom Server Name") ?: "Custom Server Name"
        val javaOn = prefs.getBoolean("java_on", true)
        val bedrockOn = prefs.getBoolean("bedrock_on", false)
        val javaPort = prefs.getInt("java_port", 25565)
        val bedrockPort = prefs.getInt("bedrock_port", 19132)
        val motd = prefs.getString("motd", "A SliqServer Minecraft server") ?: "A SliqServer Minecraft server"
        val maxPlayers = prefs.getInt("max_players", 20)
        val software = prefs.getString("software", "Paper") ?: "Paper"
        val bindIp = if (javaOn) "0.0.0.0" else "127.0.0.1"
        val ua = "SliqServer/0.2 (https://sliqado.org)"
        val serverDownload = if (software == "Fabric") """
            LOADER=${'$'}(curl -fsSL -H "User-Agent: $ua" "https://meta.fabricmc.net/v2/versions/loader" | jq -r '.[0].version')
            INSTALLER=${'$'}(curl -fsSL -H "User-Agent: $ua" "https://meta.fabricmc.net/v2/versions/installer" | jq -r '.[0].version')
            curl -fL -H "User-Agent: $ua" "https://meta.fabricmc.net/v2/versions/loader/$version/${'$'}LOADER/${'$'}INSTALLER/server/jar" -o server.jar
            FABRIC_API_URL=${'$'}(curl -fsSL -H "User-Agent: $ua" "https://api.modrinth.com/v2/project/fabric-api/version" | jq -r --arg gv "$version" 'first(.[] | select((.loaders|index("fabric")) and (.game_versions|index(${'$'}gv))) | .files[] | select(.primary == true) | .url) // empty')
            if [ -n "${'$'}FABRIC_API_URL" ]; then curl -fL -H "User-Agent: $ua" "${'$'}FABRIC_API_URL" -o mods/fabric-api.jar; fi
        """.trimIndent() else """
            BUILDS=${'$'}(curl -fsSL -H "User-Agent: $ua" "https://fill.papermc.io/v3/projects/paper/versions/$version/builds")
            PAPER_URL=${'$'}(printf '%s' "${'$'}BUILDS" | jq -r 'first(.[] | select(.channel == "STABLE") | .downloads."server:default".url) // empty')
            if [ -z "${'$'}PAPER_URL" ]; then echo "No stable Paper build found for $version" > ~/sliqserver/last-error.txt; exit 2; fi
            curl -fL -H "User-Agent: $ua" "${'$'}PAPER_URL" -o server.jar
        """.trimIndent()
        val paperScript = """
            set -e
            mkdir -p ~/sliqserver/plugins ~/sliqserver/mods ~/sliqserver/backups
            cd ~/sliqserver
            pkg update -y >/dev/null 2>&1 || true
            pkg install -y curl jq >/dev/null 2>&1 || true
            if [[ ${TermuxBridge.q(version)} == 26.* ]]; then pkg install -y openjdk-25 >/dev/null 2>&1 || true; else pkg install -y openjdk-21 >/dev/null 2>&1 || true; fi
            $serverDownload
            printf 'eula=true\n' > eula.txt
            cat > server.properties <<PROP
server-port=$javaPort
server-ip=$bindIp
motd=$motd
max-players=$maxPlayers
online-mode=true
view-distance=8
difficulty=normal
gamemode=survival
pvp=true
enable-command-block=false
PROP
        """.trimIndent()
        val bedrockScript = if (bedrockOn) {
            if (software == "Fabric") """
                curl -fL "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/fabric" -o mods/Geyser-Fabric.jar
                curl -fL "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/fabric" -o mods/floodgate-fabric.jar
            """.trimIndent() else """
                curl -fL "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot" -o plugins/Geyser-Spigot.jar
                curl -fL "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot" -o plugins/floodgate-spigot.jar
                mkdir -p plugins/Geyser-Spigot
                if [ -f plugins/Geyser-Spigot/config.yml ]; then
                  sed -i -E 's/^([[:space:]]*)port: [0-9]+/\\1port: $bedrockPort/' plugins/Geyser-Spigot/config.yml || true
                fi
            """.trimIndent()
        } else "rm -f plugins/Geyser-Spigot.jar plugins/floodgate-spigot.jar mods/Geyser-Fabric.jar mods/floodgate-fabric.jar"
        val marker = "printf '%s\\n' ${TermuxBridge.q(name)} > server-name.txt"
        return "$paperScript\n$bedrockScript\n$marker"
    }

    private fun startServer() {
        val command = shellBase() + "\ncd ~/sliqserver\nnohup java -Xms512M -Xmx2G -jar server.jar --nogui > console.log 2>&1 & echo ${'$'}! > server.pid"
        TermuxBridge.run(this, command)
        toast("Server start requested")
    }

    private fun stopServer() {
        val cmd = "cd ~/sliqserver; if [ -f server.pid ]; then kill ${'$'}(cat server.pid) 2>/dev/null || true; rm -f server.pid; else pkill -f 'server.jar' 2>/dev/null || true; fi"
        TermuxBridge.run(this, cmd)
        toast("Server stop requested")
    }

    private fun restartServer() {
        val cmd = "cd ~/sliqserver; if [ -f server.pid ]; then kill ${'$'}(cat server.pid) 2>/dev/null || true; rm -f server.pid; fi; sleep 2; " + shellBase() + "; nohup java -Xms512M -Xmx2G -jar server.jar --nogui > console.log 2>&1 & echo ${'$'}! > server.pid"
        TermuxBridge.run(this, cmd)
        toast("Server restart requested")
    }

    private fun initScreen(title: String, subtitle: String = ""): LinearLayout {
        val outer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
        }
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(12), dp(16), dp(12))
            setBackgroundColor(Color.rgb(11, 24, 41))
        }
        if (title != "SliqServer") {
            top.addView(button("‹", panel2) { showHome() }, LinearLayout.LayoutParams(dp(52), dp(46)))
        }
        val titleWrap = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12),0,0,0) }
        titleWrap.addView(text(title, 22f, white, true))
        if (subtitle.isNotBlank()) titleWrap.addView(text(subtitle, 12f, muted))
        top.addView(titleWrap, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        outer.addView(top)
        val scroll = ScrollView(this)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(28))
        }
        scroll.addView(root)
        outer.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(outer)
        return root
    }

    private fun showHome() {
        initScreen("SliqServer", "Minecraft server control")
        val name = prefs.getString("server_name", "Custom Server Name") ?: "Custom Server Name"
        val card = card()
        card.addView(text(name, 26f, white, true))
        card.addView(text(standardAddress(), 15f, muted))
        val platform = when {
            prefs.getBoolean("java_on", true) && prefs.getBoolean("bedrock_on", false) -> "Java + Bedrock"
            prefs.getBoolean("bedrock_on", false) -> "Bedrock"
            else -> "Java"
        }
        val software = prefs.getString("software", "Paper") ?: "Paper"
        card.addView(text("$platform • $software • ${prefs.getString("version", "26.2")}", 13f, muted))
        root.addView(card, fullMargin())
        val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        controls.addView(button("START", green) { startServer() }, weightParams())
        controls.addView(button("STOP", red) { stopServer() }, weightParams())
        controls.addView(button("RESTART", blue) { restartServer() }, weightParams())
        root.addView(controls, fullMargin())

        root.addView(menuButton("🧰  Server Software", "Paper for plugins or Fabric for mods") { showSoftware() })
        root.addView(menuButton("☕  Java / Bedrock", "Choose Java, Bedrock, or both") { showPlatforms() })
        root.addView(menuButton("🌐  Server Address", "IP, ports, sliqado.org and custom DNS") { showAddress() })
        root.addView(menuButton("🧱  Minecraft Version", "Choose a Paper/Minecraft version") { showVersion() })
        root.addView(menuButton("🔌  Plugins", "Search and install Paper plugins") { openAddons("plugin") })
        root.addView(menuButton("🧩  Mods", "Search and install server-side Fabric mods") { openAddons("mod") })
        root.addView(menuButton("🖥  Console", "Open the live Termux server console") { showConsole() })
        root.addView(menuButton("⚙  Server Settings", "Name, MOTD, players and ports") { showSettings() })
        root.addView(menuButton("💾  Backups", "Create or restore server backups") { showBackups() })
        root.addView(button("STOP SERVER & EXIT TO TABLET", red) { stopServer(); finishAndRemoveTask() }, fullMargin())
        root.addView(text("Android uses Termux/OpenJDK as the server engine. Bedrock access is provided by Geyser + Floodgate so Java and Bedrock players can share one world.", 12f, muted), fullMargin())
    }

    private fun showSoftware() {
        initScreen("Server Software", "Choose plugins or mods")
        val spinner = Spinner(this)
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, arrayOf("Paper", "Fabric"))
        selectSpinner(spinner, prefs.getString("software", "Paper") ?: "Paper")
        root.addView(spinner, fullMargin())
        root.addView(text("Paper loads plugins. Fabric loads mods. The Plugins and Mods browsers stay available, but only add-ons for the selected server software are loaded.", 13f, muted), fullMargin())
        root.addView(button("SAVE SOFTWARE", blue) {
            prefs.edit().putString("software", spinner.selectedItem.toString()).apply()
            toast("Server software saved")
        }, fullMargin())
    }

    private fun showPlatforms() {
        initScreen("Java / Bedrock", "Choose who can join")
        val javaSwitch = Switch(this).apply {
            text = "Java Edition"
            setTextColor(white)
            textSize = 18f
            isChecked = prefs.getBoolean("java_on", true)
        }
        val bedrockSwitch = Switch(this).apply {
            text = "Bedrock Edition"
            setTextColor(white)
            textSize = 18f
            isChecked = prefs.getBoolean("bedrock_on", false)
        }
        root.addView(sectionCard("Java Edition", "Paper Java server on TCP 25565. Mods/plugins depend on the selected software.", javaSwitch))
        root.addView(sectionCard("Bedrock Edition", "Geyser/Floodgate bridge on UDP 19132. Bedrock phones, tablets, consoles and Windows can join the same world.", bedrockSwitch))
        val modeText = text("", 14f, muted)
        fun updateMode() {
            if (!javaSwitch.isChecked && !bedrockSwitch.isChecked) javaSwitch.isChecked = true
            prefs.edit().putBoolean("java_on", javaSwitch.isChecked).putBoolean("bedrock_on", bedrockSwitch.isChecked).apply()
            modeText.text = when {
                javaSwitch.isChecked && bedrockSwitch.isChecked -> "Mode: Java + Bedrock"
                bedrockSwitch.isChecked -> "Mode: Bedrock only (Java engine is bound to localhost)"
                else -> "Mode: Java only"
            }
        }
        javaSwitch.setOnCheckedChangeListener { _, _ -> updateMode() }
        bedrockSwitch.setOnCheckedChangeListener { _, _ -> updateMode() }
        updateMode()
        root.addView(modeText, fullMargin())
        root.addView(text("Fabric + Bedrock currently works best on Minecraft 26.2 because current Geyser-Fabric targets 26.2. Paper + Geyser is the recommended cross-play mode.", 12f, muted), fullMargin())
        root.addView(button("SAVE", blue) { updateMode(); toast("Platform mode saved") }, fullMargin())
    }

    private fun showAddress() {
        initScreen("Server Address", "Share your server")
        val local = localIp()
        val publicLabel = text("Checking public IP…", 16f, white, true)
        val address = standardAddress()
        root.addView(infoCard("Local IP", local))
        val publicCard = card(); publicCard.addView(text("Public IP", 12f, muted)); publicCard.addView(publicLabel); root.addView(publicCard, fullMargin())
        Thread {
            val p = try { JSONObject(httpGet("https://api.ipify.org?format=json")).optString("ip", "Unavailable") } catch (_: Exception) { "Unavailable" }
            runOnUiThread { publicLabel.text = p; prefs.edit().putString("public_ip", p).apply() }
        }.start()
        val addressCard = card()
        addressCard.addView(text("Standard address", 12f, muted))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        row.addView(text(address, 18f, white, true), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        row.addView(button("COPY", panel2) { copy(address) }, LinearLayout.LayoutParams(dp(84), dp(44)))
        row.addView(button("CUSTOM", blue) { customAddressDialog() }, LinearLayout.LayoutParams(dp(100), dp(44)))
        addressCard.addView(row)
        addressCard.addView(text("Sliqado address format: <server-name>.sliqado.org. Spaces and underscores are converted to '-' because hostnames cannot reliably use underscores.", 12f, muted))
        root.addView(addressCard, fullMargin())
        root.addView(infoCard("Java", "${prefs.getInt("java_port",25565)} / TCP"))
        root.addView(infoCard("Bedrock", "${prefs.getInt("bedrock_port",19132)} / UDP"))
        root.addView(text("For players outside your Wi‑Fi, your router must forward the selected ports, or you need a tunnel. DNS only names the server; it does not open the router ports.", 13f, muted), fullMargin())
        root.addView(button("CHECK STANDARD ADDRESS", blue) { checkAddress(address) }, fullMargin())
    }

    private fun customAddressDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(18),dp(8),dp(18),0) }
        val input = EditText(this).apply { hint = "play.example.com"; setText(prefs.getString("custom_address", "")); setTextColor(white); setHintTextColor(muted) }
        val provider = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, arrayOf("IONOS", "Cloudflare", "Other / Manual"))
        }
        box.addView(input); box.addView(provider)
        AlertDialog.Builder(this)
            .setTitle("Custom server address")
            .setView(box)
            .setPositiveButton("SAVE") { _, _ ->
                val host = input.text.toString().trim()
                if (host.isBlank()) return@setPositiveButton
                prefs.edit().putString("custom_address", host).apply()
                showDnsInstructions(host, provider.selectedItem.toString())
            }
            .setNegativeButton("CANCEL", null)
            .show()
    }

    private fun showDnsInstructions(host: String, provider: String) {
        val ip = prefs.getString("public_ip", "YOUR_PUBLIC_IP") ?: "YOUR_PUBLIC_IP"
        val jp = prefs.getInt("java_port", 25565)
        val bp = prefs.getInt("bedrock_port", 19132)
        val records = """
Provider: $provider
Hostname: $host

A record
Name: ${host.substringBefore('.')}
Value: $ip
TTL: 300

Java SRV record
Name: _minecraft._tcp.${host.substringBefore('.')}
Priority: 0
Weight: 5
Port: $jp
Target: $host

Bedrock uses UDP port $bp. Keep that port forwarded/open.

IONOS supports DNS records and Dynamic DNS through its DNS API. Cloudflare also supports DNS record creation through API tokens. The app intentionally does not store your DNS API secret.
        """.trimIndent()
        AlertDialog.Builder(this).setTitle("DNS setup").setMessage(records).setPositiveButton("COPY") { _, _ -> copy(records) }.setNegativeButton("CLOSE", null).show()
    }

    private fun checkAddress(host: String) {
        Thread {
            val result = try {
                val addresses = java.net.InetAddress.getAllByName(host).joinToString { it.hostAddress ?: "?" }
                "DNS resolves to: $addresses"
            } catch (e: Exception) { "Address is not active yet: ${e.message ?: "DNS lookup failed"}" }
            runOnUiThread { AlertDialog.Builder(this).setTitle(host).setMessage(result).setPositiveButton("OK", null).show() }
        }.start()
    }

    private fun showVersion() {
        initScreen("Minecraft Version", "Paper server version")
        val spinner = Spinner(this)
        val fallback = mutableListOf("26.2", "26.1", "1.21.11", "1.21.10", "1.21.8", "1.21.7", "1.21.5", "1.21.4")
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, fallback)
        spinner.adapter = adapter
        root.addView(spinner, fullMargin())
        val status = text("Loading versions from PaperMC…", 13f, muted)
        root.addView(status, fullMargin())
        Thread {
            try {
                val json = JSONObject(httpGet("https://fill.papermc.io/v3/projects/paper"))
                val groups = json.getJSONObject("versions")
                val list = mutableListOf<String>()
                val keys = groups.keys()
                while (keys.hasNext()) {
                    val arr = groups.getJSONArray(keys.next())
                    for (i in 0 until arr.length()) list.add(arr.getString(i))
                }
                runOnUiThread {
                    adapter.clear(); adapter.addAll(list.distinct()); adapter.notifyDataSetChanged()
                    selectSpinner(spinner, prefs.getString("version","26.2") ?: "26.2")
                    status.text = "Stable builds are downloaded from PaperMC when the server starts."
                }
            } catch (e: Exception) { runOnUiThread { status.text = "Using built-in version list." } }
        }.start()
        selectSpinner(spinner, prefs.getString("version","26.2") ?: "26.2")
        root.addView(button("SAVE VERSION", blue) {
            prefs.edit().putString("version", spinner.selectedItem.toString()).apply(); toast("Version saved")
        }, fullMargin())
        root.addView(text("Paper 26.1+ requires Java 25; older modern versions use Java 21. SliqServer installs the matching Termux OpenJDK package when starting.", 12f, muted), fullMargin())
    }

    private fun showSettings() {
        initScreen("Server Settings", "Basic Minecraft settings")
        val name = edit("Server name", prefs.getString("server_name", "Custom Server Name") ?: "Custom Server Name")
        val motd = edit("Description / MOTD", prefs.getString("motd", "A SliqServer Minecraft server") ?: "A SliqServer Minecraft server")
        val players = edit("Max players", prefs.getInt("max_players",20).toString(), true)
        val javaPort = edit("Java port", prefs.getInt("java_port",25565).toString(), true)
        val bedrockPort = edit("Bedrock port", prefs.getInt("bedrock_port",19132).toString(), true)
        listOf(name,motd,players,javaPort,bedrockPort).forEach { root.addView(it, fullMargin()) }
        root.addView(button("SAVE SETTINGS", blue) {
            prefs.edit()
                .putString("server_name", name.text.toString().ifBlank { "Custom Server Name" })
                .putString("motd", motd.text.toString())
                .putInt("max_players", players.text.toString().toIntOrNull()?.coerceIn(1,500) ?: 20)
                .putInt("java_port", javaPort.text.toString().toIntOrNull()?.coerceIn(1024,65535) ?: 25565)
                .putInt("bedrock_port", bedrockPort.text.toString().toIntOrNull()?.coerceIn(1024,65535) ?: 19132)
                .apply()
            toast("Settings saved")
        }, fullMargin())
        root.addView(button("INITIAL TERMUX SETUP", panel2) {
            TermuxBridge.run(this, "pkg update -y && pkg install -y curl jq openjdk-21 openjdk-25")
        }, fullMargin())
        root.addView(text("In Termux, set allow-external-apps=true in ~/.termux/termux.properties, then restart Termux. This lets SliqServer send start/stop/install commands without leaving a terminal open.", 12f, muted), fullMargin())
    }

    private fun showConsole() {
        initScreen("Console", "Server output and commands")
        val info = text("Use the buttons below to open the live server log or send a command.", 14f, muted)
        root.addView(info, fullMargin())
        root.addView(button("OPEN LIVE CONSOLE", blue) {
            TermuxBridge.run(this, "cd ~/sliqserver; touch console.log; tail -n 200 -f console.log", false)
        }, fullMargin())
        val command = edit("Minecraft command (without /)", "")
        root.addView(command, fullMargin())
        root.addView(button("SEND COMMAND", panel2) {
            val c = command.text.toString().trim(); if (c.isNotEmpty()) {
                toast("Direct stdin console commands are not available with detached Java yet. Use OPEN LIVE CONSOLE, then type the command in Termux.")
            }
        }, fullMargin())
    }

    private fun showBackups() {
        initScreen("Backups", "World and server files")
        root.addView(button("CREATE BACKUP", blue) {
            TermuxBridge.run(this, "mkdir -p ~/sliqserver/backups; cd ~/sliqserver; tar --exclude=backups -czf backups/backup-${'$'}(date +%Y%m%d-%H%M%S).tar.gz .")
            toast("Backup requested")
        }, fullMargin())
        root.addView(button("LIST BACKUPS", panel2) {
            TermuxBridge.run(this, "cd ~/sliqserver; ls -lh backups; echo; read -p 'Press Enter to close'", false)
        }, fullMargin())
        root.addView(text("Restore is intentionally manual from the live Termux console so an old backup cannot overwrite a running world by accident.", 12f, muted), fullMargin())
    }

    private fun openAddons(kind: String) {
        val i = Intent(this, AddonActivity::class.java)
        i.putExtra("kind", kind)
        i.putExtra("version", prefs.getString("version", "26.2"))
        startActivity(i)
    }

    private fun standardAddress(): String {
        val custom = prefs.getString("custom_address", "")?.trim().orEmpty()
        if (custom.isNotEmpty()) return custom
        val raw = prefs.getString("server_name", "Custom Server Name") ?: "Custom Server Name"
        val slug = raw.trim().replace(Regex("[^A-Za-z0-9-]+"), "-").trim('-').ifBlank { "Custom-Server-Name" }
        return "$slug.sliqado.org"
    }

    private fun localIp(): String = try {
        val interfaces = Collections.list(NetworkInterface.getNetworkInterfaces())
        for (intf in interfaces) for (addr in Collections.list(intf.inetAddresses)) {
            if (!addr.isLoopbackAddress && addr is Inet4Address) return addr.hostAddress ?: "Unavailable"
        }
        "Unavailable"
    } catch (_: Exception) { "Unavailable" }

    private fun httpGet(url: String): String {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 10000; c.readTimeout = 15000
        c.setRequestProperty("User-Agent", "SliqServer/0.2 (https://sliqado.org)")
        c.inputStream.bufferedReader().use { return it.readText() }
    }

    private fun selectSpinner(spinner: Spinner, value: String) {
        val a = spinner.adapter ?: return
        for (i in 0 until a.count) if (a.getItem(i).toString() == value) { spinner.setSelection(i); return }
    }

    private fun menuButton(title: String, sub: String, click: () -> Unit): View {
        val c = card(); c.isClickable = true; c.setOnClickListener { click() }
        c.addView(text(title, 18f, white, true)); c.addView(text(sub, 12f, muted)); return c.apply { layoutParams = fullMargin() }
    }

    private fun infoCard(label: String, value: String): View {
        val c = card(); c.addView(text(label, 12f, muted)); c.addView(text(value, 18f, white, true)); return c.apply { layoutParams = fullMargin() }
    }

    private fun sectionCard(title: String, desc: String, control: View): View {
        val c = card(); c.addView(text(title, 19f, white, true)); c.addView(text(desc, 13f, muted)); c.addView(control); return c.apply { layoutParams = fullMargin() }
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL; setPadding(dp(16),dp(16),dp(16),dp(16)); setBackgroundColor(panel)
    }

    private fun button(label: String, color: Int, click: () -> Unit): Button = Button(this).apply {
        text = label; setTextColor(white); setBackgroundColor(color); isAllCaps = false; typeface = Typeface.DEFAULT_BOLD; setOnClickListener { click() }
    }

    private fun text(s: String, size: Float, color: Int, bold: Boolean = false): TextView = TextView(this).apply {
        text = s; textSize = size; setTextColor(color); if (bold) typeface = Typeface.DEFAULT_BOLD; setPadding(0,dp(4),0,dp(4))
    }

    private fun edit(hintText: String, value: String, numeric: Boolean = false): EditText = EditText(this).apply {
        hint = hintText; setText(value); setTextColor(white); setHintTextColor(muted); setBackgroundColor(panel); setPadding(dp(14),dp(12),dp(14),dp(12))
        if (numeric) inputType = InputType.TYPE_CLASS_NUMBER
    }

    private fun fullMargin(): LinearLayout.LayoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { setMargins(0,0,0,dp(12)) }
    private fun weightParams(): LinearLayout.LayoutParams = LinearLayout.LayoutParams(0, dp(54), 1f).apply { setMargins(dp(3),0,dp(3),0) }
    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()
    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_SHORT).show()
    private fun copy(s: String) { (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText("SliqServer",s)); toast("Copied") }
}
