package org.sliqado.sliqserver

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.widget.*
import java.io.ByteArrayOutputStream

class DedicatedServerActivity : Activity() {
    private val bg = Color.rgb(7, 17, 31)
    private val panel = Color.rgb(13, 27, 45)
    private val field = Color.rgb(16, 31, 52)
    private val green = Color.rgb(57, 255, 136)
    private val blue = Color.rgb(37, 99, 235)
    private val red = Color.rgb(239, 68, 68)
    private val amber = Color.rgb(245, 158, 11)
    private val white = Color.WHITE
    private val muted = Color.rgb(142, 160, 184)
    private val handler = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("sliqserver_v3", MODE_PRIVATE) }

    private lateinit var statusText: TextView
    private lateinit var playersText: TextView
    private lateinit var cpuText: TextView
    private lateinit var ramText: TextView
    private lateinit var wifiText: TextView
    private lateinit var nameInput: EditText
    private lateinit var descriptionInput: EditText
    private lateinit var maxPlayersInput: EditText
    private lateinit var iconText: TextView
    private var metricsBusy = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "SliqServer"
        buildUi()
        loadConfig()
        installAutomationScripts()
        if (prefs.getBoolean("server_enabled", true)) {
            startManager()
        }
        handler.post(metricsRunnable)
    }

    override fun onResume() {
        super.onResume()
        refreshWifi()
    }

    override fun onDestroy() {
        handler.removeCallbacks(metricsRunnable)
        super.onDestroy()
    }

    private fun buildUi() {
        val scroll = ScrollView(this).apply { setBackgroundColor(bg) }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(20), dp(16), dp(40))
            setBackgroundColor(bg)
        }
        scroll.addView(page)
        setContentView(scroll)

        page.addView(text("SliqServer", 30f, white, true))
        page.addView(text("Dedicated Minecraft server · always-on mode", 13f, muted))

        val statusBox = section(page, "SERVER")
        statusText = text("● STARTING", 20f, amber, true)
        statusBox.addView(statusText)
        val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        controls.addView(button("ON", green) { enableServer() }, weight())
        controls.addView(button("OFF", red) { disableServer() }, weight())
        statusBox.addView(controls, match(dp(52)))

        val stats = section(page, "LIVE STATUS")
        playersText = text("Players: 0 / 10", 16f, white, true)
        cpuText = text("CPU: 0%", 14f, white)
        ramText = text("RAM: 0 MB", 14f, white)
        stats.addView(playersText)
        stats.addView(cpuText)
        stats.addView(ramText)

        val settingsBox = section(page, "SERVER SETTINGS")
        nameInput = edit(settingsBox, "Server name", "My Server")
        descriptionInput = edit(settingsBox, "Server description", "A SliqServer Minecraft server")
        maxPlayersInput = edit(settingsBox, "Max players", "10", true)
        iconText = text("Server image: not set", 13f, muted)
        settingsBox.addView(iconText)
        settingsBox.addView(button("UPLOAD SERVER IMAGE", blue) { chooseIcon() }, match(dp(50)))
        settingsBox.addView(button("SAVE CHANGES", blue) {
            saveConfig()
            toast("Saved")
        }, match(dp(50)))

        val addressBox = section(page, "SERVER ADDRESS")
        addressBox.addView(text("sliqado.org", 22f, green, true))
        addressBox.addView(text("Minecraft connection address", 12f, muted))

        val wifiBox = section(page, "WI-FI")
        wifiText = text("Checking Wi-Fi…", 15f, white, true)
        wifiBox.addView(wifiText)
        wifiBox.addView(button("CHOOSE WI-FI", field) {
            startActivity(Intent(Settings.ACTION_WIFI_SETTINGS))
        }, match(dp(50)))
        wifiBox.addView(text("Choose the Wi-Fi network Android should use for the server.", 12f, muted))

        val autoBox = section(page, "AUTOMATION")
        autoBox.addView(text("✓ Starts again after reboot\n✓ Keeps the server running\n✓ Checks every 15 minutes for a newer stable Minecraft/Paper version\n✓ Creates a backup before updating\n✓ Starts the server again after an update", 13f, white))
    }

    private fun enableServer() {
        saveConfig()
        if (!prefs.getBoolean("eula_accepted", false)) {
            AlertDialog.Builder(this)
                .setTitle("Minecraft EULA")
                .setMessage("Starting a Minecraft server requires accepting the Minecraft EULA. Do you accept it?")
                .setPositiveButton("ACCEPT & START") { _, _ ->
                    prefs.edit().putBoolean("eula_accepted", true).putBoolean("server_enabled", true).apply()
                    TermuxBridge.run(this, "mkdir -p ~/sliqserver; printf 'eula=true\\n' > ~/sliqserver/eula.txt; rm -f ~/sliqserver/manual-off")
                    installAutomationScripts()
                    startManager()
                }
                .setNegativeButton("CANCEL", null)
                .show()
            return
        }
        prefs.edit().putBoolean("server_enabled", true).apply()
        TermuxBridge.run(this, "rm -f ~/sliqserver/manual-off")
        installAutomationScripts()
        startManager()
    }

    private fun disableServer() {
        prefs.edit().putBoolean("server_enabled", false).apply()
        TermuxBridge.run(this, "mkdir -p ~/sliqserver; touch ~/sliqserver/manual-off; printf 'stop\\n' >> ~/sliqserver/console.in 2>/dev/null || true")
        statusText.text = "● OFFLINE"
        statusText.setTextColor(red)
    }

    private fun startManager() {
        statusText.text = "● STARTING"
        statusText.setTextColor(amber)
        val cmd = "mkdir -p ~/sliqserver; rm -f ~/sliqserver/manual-off; if ! pgrep -f '[s]liqserver-manager.sh' >/dev/null 2>&1; then nohup bash ~/sliqserver/sliqserver-manager.sh >> ~/sliqserver/manager.log 2>&1 </dev/null & fi"
        TermuxBridge.run(this, cmd)
    }

    private fun loadConfig() {
        nameInput.setText(prefs.getString("server_name", "My Server"))
        descriptionInput.setText(prefs.getString("server_description", "A SliqServer Minecraft server"))
        maxPlayersInput.setText(prefs.getInt("max_players", 10).toString())
        iconText.text = if (prefs.contains("server_icon_b64")) "Server image: ✓ set" else "Server image: not set"
        refreshWifi()
    }

    private fun saveConfig() {
        val serverName = nameInput.text.toString().trim().ifBlank { "My Server" }
        val description = descriptionInput.text.toString().trim().ifBlank { serverName }
        val maxPlayers = maxPlayersInput.text.toString().toIntOrNull()?.coerceIn(1, 200) ?: 10
        prefs.edit()
            .putString("server_name", serverName)
            .putString("server_description", description)
            .putInt("max_players", maxPlayers)
            .apply()
        maxPlayersInput.setText(maxPlayers.toString())
        val cleanMotd = description.replace("\\r", " ").replace("\\n", "\\\\n")
        val props = """
motd=$cleanMotd
max-players=$maxPlayers
server-port=25565
online-mode=true
pvp=true
gamemode=survival
difficulty=normal
view-distance=6
simulation-distance=4
spawn-protection=16
""".trimIndent() + "\n"
        TermuxBridge.run(this, "mkdir -p ~/sliqserver; printf %s ${TermuxBridge.q(props)} > ~/sliqserver/server.properties")
    }

    private fun chooseIcon() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
        }
        startActivityForResult(intent, 4404)
    }

    @Deprecated("Deprecated in Android API, retained for minSdk compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 4404 || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        try {
            val src = contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) }
                ?: throw IllegalArgumentException("Could not open image")
            val side = minOf(src.width, src.height)
            val x = (src.width - side) / 2
            val y = (src.height - side) / 2
            val square = Bitmap.createBitmap(src, x, y, side, side)
            val icon = Bitmap.createScaledBitmap(square, 64, 64, true)
            val out = ByteArrayOutputStream()
            icon.compress(Bitmap.CompressFormat.PNG, 100, out)
            val encoded = android.util.Base64.encodeToString(out.toByteArray(), android.util.Base64.NO_WRAP)
            prefs.edit().putString("server_icon_b64", encoded).apply()
            TermuxBridge.run(this, "mkdir -p ~/sliqserver; printf %s ${TermuxBridge.q(encoded)} | base64 -d > ~/sliqserver/server-icon.png")
            iconText.text = "Server image: ✓ set"
            if (icon !== square && icon !== src) icon.recycle()
            if (square !== src) square.recycle()
            src.recycle()
        } catch (e: Exception) {
            toast("Image failed: ${e.message}")
        }
    }

    private val metricsRunnable = object : Runnable {
        override fun run() {
            refreshMetrics()
            handler.postDelayed(this, 4000)
        }
    }

    private fun refreshMetrics() {
        if (metricsBusy) return
        metricsBusy = true
        val cmd = """
ROOT="${'$'}HOME/sliqserver"
PID=${'$'}(pgrep -f '[j]ava .*server.jar' | head -n1)
if [ -n "${'$'}PID" ]; then
  if grep -q 'Done (' "${'$'}ROOT/console.log" 2>/dev/null; then echo STATUS=ONLINE; else echo STATUS=STARTING; fi
  printf 'list\n' >> "${'$'}ROOT/console.in" 2>/dev/null || true
  sleep 0.25
  LINE=${'$'}(grep -E 'There are [0-9]+ of a max of [0-9]+ players online' "${'$'}ROOT/console.log" 2>/dev/null | tail -n1)
  N=${'$'}(printf '%s' "${'$'}LINE" | sed -n 's/.*There are \([0-9][0-9]*\) of a max of \([0-9][0-9]*\).*/\1/p')
  [ -z "${'$'}N" ] && N=0
  echo PLAYER=${'$'}N
  U=${'$'}(ps -p "${'$'}PID" -o %cpu=,rss= 2>/dev/null | tail -n1)
  echo UTIL=${'$'}U
else
  echo STATUS=OFFLINE
  echo PLAYER=0
  echo UTIL=0 0
fi
""".trimIndent()
        val ok = TermuxBridge.runForResult(this, cmd) { r ->
            runOnUiThread {
                metricsBusy = false
                var status = "OFFLINE"
                var players = 0
                var cpu = 0.0
                var rss = 0.0
                r.stdout.lineSequence().forEach { line ->
                    when {
                        line.startsWith("STATUS=") -> status = line.substringAfter("=").trim()
                        line.startsWith("PLAYER=") -> players = line.substringAfter("=").trim().toIntOrNull() ?: 0
                        line.startsWith("UTIL=") -> {
                            val parts = line.substringAfter("=").trim().split(Regex("\\s+"))
                            cpu = parts.getOrNull(0)?.toDoubleOrNull() ?: 0.0
                            rss = parts.getOrNull(1)?.toDoubleOrNull() ?: 0.0
                        }
                    }
                }
                statusText.text = "● $status"
                statusText.setTextColor(if (status == "ONLINE") green else if (status == "STARTING") amber else red)
                playersText.text = "Players: $players / ${maxPlayersInput.text.toString().toIntOrNull() ?: 10}"
                cpuText.text = String.format("CPU: %.1f%%", cpu)
                ramText.text = String.format("RAM: %.0f MB", rss / 1024.0)
            }
        }
        if (!ok) metricsBusy = false
    }

    private fun refreshWifi() {
        if (!::wifiText.isInitialized) return
        val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork
        val caps = if (network != null) cm.getNetworkCapabilities(network) else null
        wifiText.text = when {
            caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true -> "Wi-Fi: connected ✓"
            caps?.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) == true -> "Network: Ethernet"
            else -> "Wi-Fi: not connected"
        }
    }

    private fun installAutomationScripts() {
        val manager = managerScript()
        val boot = """#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock 2>/dev/null || true
mkdir -p "${'$'}HOME/sliqserver"
rm -f "${'$'}HOME/sliqserver/manual-off"
if ! pgrep -f '[s]liqserver-manager.sh' >/dev/null 2>&1; then
  nohup bash "${'$'}HOME/sliqserver/sliqserver-manager.sh" >> "${'$'}HOME/sliqserver/manager.log" 2>&1 </dev/null &
fi
"""
        val cmd = "mkdir -p ~/sliqserver ~/.termux/boot; printf %s ${TermuxBridge.q(manager)} > ~/sliqserver/sliqserver-manager.sh; chmod +x ~/sliqserver/sliqserver-manager.sh; printf %s ${TermuxBridge.q(boot)} > ~/.termux/boot/sliqserver-boot.sh; chmod +x ~/.termux/boot/sliqserver-boot.sh"
        TermuxBridge.run(this, cmd)
    }

    private fun managerScript(): String = """#!/data/data/com.termux/files/usr/bin/bash
ROOT="${'$'}HOME/sliqserver"
UA='SliqServer/0.5 (https://sliqado.org)'
mkdir -p "${'$'}ROOT/backups"
touch "${'$'}ROOT/console.in" "${'$'}ROOT/console.log"
termux-wake-lock 2>/dev/null || true

ensure_tools() {
  local missing=0
  for x in curl jq java ps tar; do command -v "${'$'}x" >/dev/null 2>&1 || missing=1; done
  if [ "${'$'}missing" = 1 ]; then
    pkg update -y >>"${'$'}ROOT/manager.log" 2>&1 || true
    pkg install -y curl jq procps coreutils tar openjdk-25 >>"${'$'}ROOT/manager.log" 2>&1 || true
  fi
}

server_running() { pgrep -f '[j]ava .*server.jar' >/dev/null 2>&1; }

stop_server() {
  server_running || return 0
  printf 'stop\n' >> "${'$'}ROOT/console.in" 2>/dev/null || true
  local i=0
  while server_running && [ "${'$'}i" -lt 60 ]; do sleep 1; i=${'$'}((i+1)); done
  server_running && pkill -f '[j]ava .*server.jar' >/dev/null 2>&1 || true
}

start_server() {
  [ -f "${'$'}ROOT/manual-off" ] && return 0
  server_running && return 0
  [ -s "${'$'}ROOT/server.jar" ] || return 0
  [ -f "${'$'}ROOT/eula.txt" ] || printf 'eula=true\n' > "${'$'}ROOT/eula.txt"
  touch "${'$'}ROOT/console.in" "${'$'}ROOT/console.log"
  cd "${'$'}ROOT" || return 1
  nohup bash -lc 'cd "${'$'}HOME/sliqserver"; tail -n0 -F console.in | java -Xms512M -Xmx2048M -XX:+UseG1GC -jar server.jar nogui >> console.log 2>&1' >/dev/null 2>&1 &
}

latest_stable() {
  local project versions v builds url
  project=${'$'}(curl -fsSL -H "User-Agent: ${'$'}UA" https://fill.papermc.io/v3/projects/paper 2>/dev/null) || return 1
  versions=${'$'}(printf '%s' "${'$'}project" | jq -r '.versions | to_entries[] | .value[]' 2>/dev/null | sort -V -r)
  for v in ${'$'}versions; do
    builds=${'$'}(curl -fsSL -H "User-Agent: ${'$'}UA" "https://fill.papermc.io/v3/projects/paper/versions/${'$'}v/builds" 2>/dev/null) || continue
    url=${'$'}(printf '%s' "${'$'}builds" | jq -r 'first(.[] | select(.channel == "STABLE") | .downloads."server:default".url) // ""' 2>/dev/null)
    if [ -n "${'$'}url" ]; then printf '%s|%s\n' "${'$'}v" "${'$'}url"; return 0; fi
  done
  return 1
}

update_if_needed() {
  local found latest url current tmp stamp
  found=${'$'}(latest_stable) || return 0
  latest=${'$'}{found%%|*}
  url=${'$'}{found#*|}
  current=${'$'}(cat "${'$'}ROOT/.minecraft-version" 2>/dev/null || true)
  if [ "${'$'}latest" = "${'$'}current" ] && [ -s "${'$'}ROOT/server.jar" ]; then return 0; fi

  stamp=${'$'}(date +%Y%m%d-%H%M%S)
  if [ -d "${'$'}ROOT/world" ]; then
    tar -czf "${'$'}ROOT/backups/world-${'$'}stamp.tar.gz" -C "${'$'}ROOT" world world_nether world_the_end server.properties 2>/dev/null || true
  fi
  stop_server
  tmp="${'$'}ROOT/server.jar.new"
  if curl -fL -H "User-Agent: ${'$'}UA" "${'$'}url" -o "${'$'}tmp"; then
    mv "${'$'}tmp" "${'$'}ROOT/server.jar"
    printf '%s\n' "${'$'}latest" > "${'$'}ROOT/.minecraft-version"
  else
    rm -f "${'$'}tmp"
  fi
  start_server
}

ensure_tools
update_if_needed
start_server
last_check=${'$'}(date +%s)
while true; do
  if [ ! -f "${'$'}ROOT/manual-off" ]; then start_server; fi
  now=${'$'}(date +%s)
  if [ ${'$'}((now-last_check)) -ge 900 ]; then
    update_if_needed
    last_check=${'$'}now
  fi
  sleep 20
done
"""

    private fun section(parent: LinearLayout, title: String): LinearLayout {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(14))
            setBackgroundColor(panel)
        }
        val lp = LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, dp(16), 0, 0) }
        parent.addView(box, lp)
        box.addView(text(title, 12f, green, true))
        return box
    }

    private fun edit(parent: LinearLayout, hint: String, value: String, number: Boolean = false): EditText {
        val e = EditText(this).apply {
            this.hint = hint
            setText(value)
            setTextColor(white)
            setHintTextColor(muted)
            setBackgroundColor(field)
            setPadding(dp(12), 0, dp(12), 0)
            if (number) inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }
        val lp = LinearLayout.LayoutParams(-1, dp(52)).apply { setMargins(0, dp(8), 0, 0) }
        parent.addView(e, lp)
        return e
    }

    private fun button(label: String, color: Int, action: () -> Unit): Button = Button(this).apply {
        text = label
        setTextColor(white)
        setBackgroundColor(color)
        setOnClickListener { action() }
    }

    private fun text(value: String, size: Float, color: Int, bold: Boolean = false): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(color)
        setPadding(0, dp(5), 0, dp(5))
        if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
    }

    private fun weight() = LinearLayout.LayoutParams(0, -1, 1f).apply { setMargins(dp(3), 0, dp(3), 0) }
    private fun match(height: Int = -2) = LinearLayout.LayoutParams(-1, height)
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
}
