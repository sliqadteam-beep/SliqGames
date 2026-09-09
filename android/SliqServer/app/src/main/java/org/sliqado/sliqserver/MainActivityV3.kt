package org.sliqado.sliqserver

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.WindowManager
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class MainActivityV3 : Activity() {
    private val bg = Color.rgb(7,17,31)
    private val panel = Color.rgb(13,27,45)
    private val field = Color.rgb(16,31,52)
    private val blue = Color.rgb(37,99,235)
    private val green = Color.rgb(57,255,136)
    private val red = Color.rgb(239,68,68)
    private val amber = Color.rgb(245,158,11)
    private val white = Color.WHITE
    private val muted = Color.rgb(142,160,184)
    private val handler = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("sliqserver_v3", MODE_PRIVATE) }

    private lateinit var statusValue: TextView
    private lateinit var playersValue: TextView
    private lateinit var cpuValue: TextView
    private lateinit var ramValue: TextView
    private lateinit var worldValue: TextView
    private lateinit var uptimeValue: TextView
    private lateinit var consoleView: TextView
    private lateinit var addressValue: TextView

    private lateinit var serverName: EditText
    private lateinit var maxPlayers: EditText
    private lateinit var viewDistance: EditText
    private lateinit var simDistance: EditText
    private lateinit var memoryMb: EditText
    private lateinit var javaPort: EditText
    private lateinit var bedrockPort: EditText
    private lateinit var spawnProtection: EditText
    private lateinit var customAddress: EditText
    private lateinit var commandInput: EditText

    private lateinit var softwareSpinner: Spinner
    private lateinit var versionSpinner: Spinner
    private lateinit var gamemodeSpinner: Spinner
    private lateinit var difficultySpinner: Spinner

    private lateinit var javaSwitch: Switch
    private lateinit var bedrockSwitch: Switch
    private lateinit var onlineSwitch: Switch
    private lateinit var pvpSwitch: Switch
    private lateinit var whitelistSwitch: Switch
    private lateinit var commandBlocksSwitch: Switch
    private lateinit var eulaSwitch: Switch
    private lateinit var screenOnSwitch: Switch

    private var startedAt = 0L
    private var refreshBusy = false

    private val versions = listOf("1.21.11","1.21.10","1.21.8","1.21.5","1.21.4","1.20.6")
    private val software = listOf("Paper","Fabric")
    private val gamemodes = listOf("survival","creative","adventure","spectator")
    private val difficulties = listOf("peaceful","easy","normal","hard")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "SliqServer"
        val scroll = ScrollView(this).apply { setBackgroundColor(bg); isFillViewport = true }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(18), dp(14), dp(36))
            setBackgroundColor(bg)
        }
        scroll.addView(page)
        setContentView(scroll)

        page.addView(TextView(this).apply {
            text = "SliqServer"
            textSize = 30f
            setTextColor(white)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        page.addView(label("Everything on one page · optimized for phones and tablets", muted, 13f))

        buildOverview(page)
        buildControls(page)
        buildSettings(page)
        buildAddress(page)
        buildAddons(page)
        buildWorld(page)
        buildConsole(page)

        loadSettings()
        applyScreenOn(screenOnSwitch.isChecked)
        updateAddress()
        screenOnSwitch.setOnCheckedChangeListener { _, enabled ->
            prefs.edit().putBoolean("screen_on", enabled).apply()
            applyScreenOn(enabled)
        }

        handler.post(refreshRunnable)
    }

    override fun onDestroy() {
        handler.removeCallbacks(refreshRunnable)
        super.onDestroy()
    }

    private val refreshRunnable = object : Runnable {
        override fun run() {
            refreshMetrics()
            handler.postDelayed(this, 4000)
        }
    }

    private fun buildOverview(page: LinearLayout) {
        val box = section(page, "Overview", "Live status, players and server utilization.")
        val row1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        statusValue = metricCard(row1, "STATUS", "● OFFLINE", 1f)
        playersValue = metricCard(row1, "PLAYERS", "0 / 10", 1f)
        box.addView(row1, match())
        val row2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        cpuValue = metricCard(row2, "SERVER CPU", "0%", 1f)
        ramValue = metricCard(row2, "SERVER RAM", "0 MB", 1f)
        box.addView(row2, match())
        val row3 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        worldValue = metricCard(row3, "WORLD SIZE", "0 MB", 1f)
        uptimeValue = metricCard(row3, "UPTIME", "00:00:00", 1f)
        box.addView(row3, match())
    }

    private fun buildControls(page: LinearLayout) {
        val box = section(page, "Server Control")
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(actionButton("▶ START", green) { startServer() }, weight())
        row.addView(actionButton("↻ RESTART", blue) { restartServer() }, weight())
        row.addView(actionButton("■ STOP", red) { stopServer() }, weight())
        box.addView(row, match())
    }

    private fun buildSettings(page: LinearLayout) {
        val box = section(page, "Server Settings", "All choices are real selectable controls.")
        serverName = edit(box, "Server name", "My Server")
        softwareSpinner = spinner(box, "Server software", software)
        versionSpinner = spinner(box, "Minecraft version", versions)
        maxPlayers = edit(box, "Max players", "10", true)
        gamemodeSpinner = spinner(box, "Gamemode", gamemodes)
        difficultySpinner = spinner(box, "Difficulty", difficulties)
        viewDistance = edit(box, "View distance", "6", true)
        simDistance = edit(box, "Simulation distance", "4", true)
        memoryMb = edit(box, "Server RAM (MB)", "2048", true)
        javaPort = edit(box, "Java port", "25565", true)
        bedrockPort = edit(box, "Bedrock port", "19132", true)
        spawnProtection = edit(box, "Spawn protection", "16", true)

        javaSwitch = switch(box, "Java players", true)
        bedrockSwitch = switch(box, "Bedrock players (Geyser)", false)
        onlineSwitch = switch(box, "Online mode", true)
        pvpSwitch = switch(box, "PvP", true)
        whitelistSwitch = switch(box, "Whitelist", false)
        commandBlocksSwitch = switch(box, "Command blocks", false)
        eulaSwitch = switch(box, "I accept the Minecraft EULA", false)
        screenOnSwitch = switch(box, "Screen Always On", true)

        box.addView(actionButton("SAVE SETTINGS", blue) {
            if (saveSettings()) toast("Settings saved")
        }, match(dp(52)))
        box.addView(actionButton("DOWNLOAD / UPDATE SERVER", field) {
            downloadServer()
        }, match(dp(52)))
    }

    private fun buildAddress(page: LinearLayout) {
        val box = section(page, "Address & Network")
        addressValue = label("", white, 16f).apply {
            setBackgroundColor(field); setPadding(dp(12),dp(12),dp(12),dp(12))
        }
        box.addView(addressValue, match())
        customAddress = edit(box, "Custom address (optional)", "")
        box.addView(actionButton("REFRESH ADDRESS", field) { updateAddress() }, match(dp(48)))
        box.addView(label("For public access, DNS and router/tunnel forwarding still have to point to this device.", muted, 12f))
    }

    private fun buildAddons(page: LinearLayout) {
        val box = section(page, "Mods & Plugins", "Paper = plugins · Fabric = mods.")
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(actionButton("PLUGINS", blue) { openAddons("plugin") }, weight())
        row.addView(actionButton("MODS", blue) { openAddons("mod") }, weight())
        box.addView(row, match())
    }

    private fun buildWorld(page: LinearLayout) {
        val box = section(page, "World & Storage")
        box.addView(actionButton("REFRESH WORLD SIZE", field) { refreshMetrics(true) }, match(dp(48)))
        box.addView(actionButton("CREATE BACKUP", blue) { createBackup() }, match(dp(48)))
        box.addView(actionButton("CLEAR WORLD", red) { confirmClearWorld() }, match(dp(48)))
    }

    private fun buildConsole(page: LinearLayout) {
        val box = section(page, "Console")
        consoleView = TextView(this).apply {
            text = "Console ready."
            setTextColor(Color.rgb(215,227,244))
            textSize = 11f
            setBackgroundColor(Color.rgb(5,10,16))
            setPadding(dp(10),dp(10),dp(10),dp(10))
            minHeight = dp(180)
        }
        box.addView(consoleView, match())
        commandInput = EditText(this).apply {
            hint = "Command, e.g. say Hello"
            setTextColor(white); setHintTextColor(muted); setBackgroundColor(field)
            setSingleLine(true); setPadding(dp(10),0,dp(10),0)
        }
        box.addView(commandInput, match(dp(48)))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        row.addView(actionButton("SEND", blue) { sendCommand() }, weight())
        row.addView(actionButton("REFRESH LOG", field) { refreshConsole() }, weight())
        box.addView(row, match())
    }

    private fun loadSettings() {
        serverName.setText(prefs.getString("server_name","My Server"))
        setSpinner(softwareSpinner, software, prefs.getString("software","Paper") ?: "Paper")
        setSpinner(versionSpinner, versions, prefs.getString("version","1.21.11") ?: "1.21.11")
        maxPlayers.setText(prefs.getInt("max_players",10).toString())
        setSpinner(gamemodeSpinner, gamemodes, prefs.getString("gamemode","survival") ?: "survival")
        setSpinner(difficultySpinner, difficulties, prefs.getString("difficulty","normal") ?: "normal")
        viewDistance.setText(prefs.getInt("view_distance",6).toString())
        simDistance.setText(prefs.getInt("sim_distance",4).toString())
        memoryMb.setText(prefs.getInt("memory_mb",2048).toString())
        javaPort.setText(prefs.getInt("java_port",25565).toString())
        bedrockPort.setText(prefs.getInt("bedrock_port",19132).toString())
        spawnProtection.setText(prefs.getInt("spawn_protection",16).toString())
        customAddress.setText(prefs.getString("custom_address",""))
        javaSwitch.isChecked = prefs.getBoolean("java_enabled",true)
        bedrockSwitch.isChecked = prefs.getBoolean("bedrock_enabled",false)
        onlineSwitch.isChecked = prefs.getBoolean("online_mode",true)
        pvpSwitch.isChecked = prefs.getBoolean("pvp",true)
        whitelistSwitch.isChecked = prefs.getBoolean("whitelist",false)
        commandBlocksSwitch.isChecked = prefs.getBoolean("command_blocks",false)
        eulaSwitch.isChecked = prefs.getBoolean("eula",false)
        screenOnSwitch.isChecked = prefs.getBoolean("screen_on",true)
    }

    private fun saveSettings(): Boolean {
        if (!javaSwitch.isChecked && !bedrockSwitch.isChecked) {
            toast("Enable Java players, Bedrock players, or both.")
            return false
        }
        prefs.edit()
            .putString("server_name", serverName.text.toString().trim().ifBlank { "My Server" })
            .putString("software", softwareSpinner.selectedItem.toString())
            .putString("version", versionSpinner.selectedItem.toString())
            .putInt("max_players", intOf(maxPlayers,10,1,200))
            .putString("gamemode", gamemodeSpinner.selectedItem.toString())
            .putString("difficulty", difficultySpinner.selectedItem.toString())
            .putInt("view_distance", intOf(viewDistance,6,2,32))
            .putInt("sim_distance", intOf(simDistance,4,2,32))
            .putInt("memory_mb", intOf(memoryMb,2048,512,16384))
            .putInt("java_port", intOf(javaPort,25565,1024,65535))
            .putInt("bedrock_port", intOf(bedrockPort,19132,1024,65535))
            .putInt("spawn_protection", intOf(spawnProtection,16,0,100))
            .putString("custom_address", customAddress.text.toString().trim())
            .putBoolean("java_enabled", javaSwitch.isChecked)
            .putBoolean("bedrock_enabled", bedrockSwitch.isChecked)
            .putBoolean("online_mode", onlineSwitch.isChecked)
            .putBoolean("pvp", pvpSwitch.isChecked)
            .putBoolean("whitelist", whitelistSwitch.isChecked)
            .putBoolean("command_blocks", commandBlocksSwitch.isChecked)
            .putBoolean("eula", eulaSwitch.isChecked)
            .putBoolean("screen_on", screenOnSwitch.isChecked)
            .apply()
        writeServerProperties()
        updateAddress()
        return true
    }

    private fun writeServerProperties() {
        val name = serverName.text.toString().trim().ifBlank { "My Server" }
        val props = """
motd=$name
max-players=${intOf(maxPlayers,10,1,200)}
gamemode=${gamemodeSpinner.selectedItem}
difficulty=${difficultySpinner.selectedItem}
server-port=${intOf(javaPort,25565,1024,65535)}
view-distance=${intOf(viewDistance,6,2,32)}
simulation-distance=${intOf(simDistance,4,2,32)}
online-mode=${onlineSwitch.isChecked}
white-list=${whitelistSwitch.isChecked}
pvp=${pvpSwitch.isChecked}
enable-command-block=${commandBlocksSwitch.isChecked}
spawn-protection=${intOf(spawnProtection,16,0,100)}
server-ip=${if(javaSwitch.isChecked) "" else "127.0.0.1"}
""".trimIndent() + "\n"
        val eula = if (eulaSwitch.isChecked) "eula=true\n" else "eula=false\n"
        val cmd = "mkdir -p ~/sliqserver; printf %s ${TermuxBridge.q(props)} > ~/sliqserver/server.properties; printf %s ${TermuxBridge.q(eula)} > ~/sliqserver/eula.txt"
        TermuxBridge.run(this, cmd)
    }

    private fun startServer() {
        if (!saveSettings()) return
        if (!eulaSwitch.isChecked) {
            toast("Accept the Minecraft EULA before starting.")
            return
        }
        val mem = intOf(memoryMb,2048,512,16384)
        val xms = minOf(1024, mem)
        val cmd = """
ROOT="${'$'}HOME/sliqserver"
mkdir -p "${'$'}ROOT"
if [ ! -f "${'$'}ROOT/server.jar" ]; then echo "MISSING"; exit 4; fi
if pgrep -f 'java .*server.jar' >/dev/null 2>&1; then echo "ALREADY"; exit 0; fi
rm -f "${'$'}ROOT/console.pipe"
mkfifo "${'$'}ROOT/console.pipe"
: > "${'$'}ROOT/console.log"
cd "${'$'}ROOT"
nohup sh -c 'while true; do cat "${'$'}HOME/sliqserver/console.pipe"; done | java -Xms${xms}M -Xmx${mem}M -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -jar server.jar nogui 2>&1 | tee -a "${'$'}HOME/sliqserver/console.log"' >/dev/null 2>&1 &
echo "STARTED"
""".trimIndent()
        statusValue.text = "● STARTING"; statusValue.setTextColor(amber)
        startedAt = System.currentTimeMillis()
        TermuxBridge.runForResult(this, cmd) { r ->
            runOnUiThread {
                if (r.stdout.contains("MISSING")) {
                    statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                    AlertDialog.Builder(this).setTitle("Server files missing")
                        .setMessage("Download the selected server version now?")
                        .setPositiveButton("Download") { _, _ -> downloadServer() }
                        .setNegativeButton("Cancel", null).show()
                } else if (r.exitCode != 0) {
                    toast("Start failed: ${r.stderr.ifBlank { r.errorMessage }}")
                }
            }
        }
    }

    private fun stopServer() {
        val cmd = "(printf 'stop\\n' > ~/sliqserver/console.pipe) >/dev/null 2>&1 &"
        TermuxBridge.run(this, cmd)
        toast("Stop requested")
    }

    private fun restartServer() {
        stopServer()
        handler.postDelayed({ startServer() }, 7000)
    }

    private fun sendCommand() {
        val text = commandInput.text.toString().trim()
        if (text.isBlank()) return
        val cmd = "(printf '%s\\n' ${TermuxBridge.q(text)} > ~/sliqserver/console.pipe) >/dev/null 2>&1 &"
        TermuxBridge.run(this, cmd)
        commandInput.setText("")
    }

    private fun refreshConsole() {
        TermuxBridge.runForResult(this, "tail -n 80 ~/sliqserver/console.log 2>/dev/null || true") { r ->
            runOnUiThread { consoleView.text = r.stdout.ifBlank { "No server log yet." } }
        }
    }

    private fun refreshMetrics(force: Boolean = false) {
        if (refreshBusy && !force) return
        refreshBusy = true
        val cmd = """
ROOT="${'$'}HOME/sliqserver"
PID=${'$'}(pgrep -f 'java .*server.jar' | head -n1)
if [ -z "${'$'}PID" ]; then
  echo STATUS=OFFLINE
  echo UTIL=0 0
  echo PLAYER=0
else
  if grep -q 'Done (' "${'$'}ROOT/console.log" 2>/dev/null; then echo STATUS=ONLINE; else echo STATUS=STARTING; fi
  (printf 'list\n' > "${'$'}ROOT/console.pipe") >/dev/null 2>&1 &
  sleep 0.35
  LINE=${'$'}(grep -E 'There are [0-9]+ of a max of [0-9]+ players online' "${'$'}ROOT/console.log" 2>/dev/null | tail -n1)
  N=${'$'}(printf '%s' "${'$'}LINE" | sed -n 's/.*There are \([0-9][0-9]*\) of a max of \([0-9][0-9]*\).*/\1/p')
  [ -z "${'$'}N" ] && N=0
  echo PLAYER=${'$'}N
  U=${'$'}(ps -p "${'$'}PID" -o %cpu=,rss= 2>/dev/null | tail -n1)
  echo UTIL=${'$'}U
fi
W=${'$'}(du -sk "${'$'}ROOT/world" "${'$'}ROOT/world_nether" "${'$'}ROOT/world_the_end" 2>/dev/null | awk '{s+=$1} END {print s+0}')
echo WORLDKB=${'$'}W
""".trimIndent()
        val ok = TermuxBridge.runForResult(this, cmd) { r ->
            runOnUiThread {
                refreshBusy = false
                parseMetrics(r.stdout)
            }
        }
        if (!ok) refreshBusy = false
    }

    private fun parseMetrics(out: String) {
        var status = "OFFLINE"
        var player = 0
        var cpu = 0.0
        var rssKb = 0.0
        var worldKb = 0.0
        out.lineSequence().forEach { line ->
            when {
                line.startsWith("STATUS=") -> status = line.substringAfter("=")
                line.startsWith("PLAYER=") -> player = line.substringAfter("=").trim().toIntOrNull() ?: 0
                line.startsWith("WORLDKB=") -> worldKb = line.substringAfter("=").trim().toDoubleOrNull() ?: 0.0
                line.startsWith("UTIL=") -> {
                    val bits = line.substringAfter("=").trim().split(Regex("\\s+"))
                    cpu = bits.getOrNull(0)?.toDoubleOrNull() ?: 0.0
                    rssKb = bits.getOrNull(1)?.toDoubleOrNull() ?: 0.0
                }
            }
        }
        statusValue.text = "● $status"
        statusValue.setTextColor(if(status=="ONLINE") green else if(status=="STARTING") amber else red)
        playersValue.text = "$player / ${intOf(maxPlayers,10,1,200)}"
        cpuValue.text = String.format("%.1f%%", cpu)
        ramValue.text = if(rssKb >= 1024) String.format("%.0f MB", rssKb/1024.0) else "${rssKb.toInt()} KB"
        worldValue.text = when {
            worldKb >= 1024*1024 -> String.format("%.2f GB", worldKb/1024.0/1024.0)
            worldKb >= 1024 -> String.format("%.1f MB", worldKb/1024.0)
            else -> "${worldKb.toInt()} KB"
        }
        if(status=="ONLINE" || status=="STARTING") {
            if(startedAt == 0L) startedAt = System.currentTimeMillis()
            val sec = ((System.currentTimeMillis()-startedAt)/1000).coerceAtLeast(0)
            uptimeValue.text = String.format("%02d:%02d:%02d", sec/3600, (sec%3600)/60, sec%60)
        } else {
            startedAt = 0L
            uptimeValue.text = "00:00:00"
        }
    }

    private fun downloadServer() {
        if (!saveSettings()) return
        val sw = softwareSpinner.selectedItem.toString()
        val version = versionSpinner.selectedItem.toString()
        toast("Preparing $sw $version…")
        Thread {
            try {
                val serverUrl = if(sw == "Paper") resolvePaper(version) else resolveFabric(version)
                val runtime = "pkg install -y openjdk-21 curl procps coreutils >/dev/null 2>&1 || true; mkdir -p ~/sliqserver"
                val bedrock = if(bedrockSwitch.isChecked) {
                    val kind = if(sw=="Paper") "spigot" else "fabric"
                    val folder = if(sw=="Paper") "plugins" else "mods"
                    "; mkdir -p ~/sliqserver/$folder" +
                    "; curl -fL ${TermuxBridge.q("https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/$kind")} -o ~/sliqserver/$folder/Geyser-$kind.jar" +
                    "; curl -fL ${TermuxBridge.q("https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/$kind")} -o ~/sliqserver/$folder/Floodgate-$kind.jar"
                } else ""
                val cmd = "$runtime; curl -fL ${TermuxBridge.q(serverUrl)} -o ~/sliqserver/server.jar$bedrock"
                TermuxBridge.runForResult(this, cmd) { r ->
                    runOnUiThread {
                        if(r.exitCode==0) toast("Server files ready")
                        else toast("Download failed: ${r.stderr.ifBlank { r.errorMessage }}")
                    }
                }
            } catch(e: Exception) {
                runOnUiThread { toast("Download failed: ${e.message}") }
            }
        }.start()
    }

    private fun resolvePaper(version: String): String {
        val arr = JSONArray(get("https://fill.papermc.io/v3/projects/paper/versions/${URLEncoder.encode(version,"UTF-8")}/builds"))
        if(arr.length()==0) throw Exception("No Paper build found for $version")
        var chosen: JSONObject? = null
        for(i in 0 until arr.length()) {
            val b = arr.getJSONObject(i)
            if(chosen==null) chosen=b
            if(b.optString("channel").equals("STABLE",true)) { chosen=b; break }
        }
        return chosen!!.getJSONObject("downloads").getJSONObject("server:default").getString("url")
    }

    private fun resolveFabric(version: String): String {
        val loaders = JSONArray(get("https://meta.fabricmc.net/v2/versions/loader/${URLEncoder.encode(version,"UTF-8")}"))
        val installers = JSONArray(get("https://meta.fabricmc.net/v2/versions/installer"))
        if(loaders.length()==0 || installers.length()==0) throw Exception("No Fabric build found for $version")
        val loader = loaders.getJSONObject(0).getJSONObject("loader").getString("version")
        var installer = installers.getJSONObject(0).getString("version")
        for(i in 0 until installers.length()) {
            val obj = installers.getJSONObject(i)
            if(obj.optBoolean("stable",false)) { installer=obj.getString("version"); break }
        }
        return "https://meta.fabricmc.net/v2/versions/loader/$version/$loader/$installer/server/jar"
    }

    private fun openAddons(kind: String) {
        saveSettings()
        startActivity(Intent(this, AddonActivity::class.java).apply {
            putExtra("kind", kind)
            putExtra("version", versionSpinner.selectedItem.toString())
        })
    }

    private fun createBackup() {
        val cmd = "mkdir -p ~/sliqserver/backups; cd ~/sliqserver; tar -czf backups/backup-\$(date +%Y%m%d-%H%M%S).tar.gz world world_nether world_the_end 2>/dev/null || true"
        TermuxBridge.run(this, cmd)
        toast("Backup requested")
    }

    private fun confirmClearWorld() {
        AlertDialog.Builder(this)
            .setTitle("Clear Minecraft World")
            .setMessage("Do You Realy Wanna Delete This World?\n\nThe map will be permanently deleted.")
            .setPositiveButton("Yes") { _, _ -> clearWorld() }
            .setNegativeButton("No", null)
            .show()
    }

    private fun clearWorld() {
        val cmd = """
(printf 'stop\n' > ~/sliqserver/console.pipe) >/dev/null 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10; do
  pgrep -f 'java .*server.jar' >/dev/null 2>&1 || break
  sleep 1
done
if pgrep -f 'java .*server.jar' >/dev/null 2>&1; then
  echo BUSY
else
  rm -rf ~/sliqserver/world ~/sliqserver/world_nether ~/sliqserver/world_the_end
  echo CLEARED
fi
""".trimIndent()
        TermuxBridge.runForResult(this, cmd) { r ->
            runOnUiThread {
                if(r.stdout.contains("CLEARED")) { worldValue.text="0 KB"; toast("World deleted") }
                else toast("Server is still running. Try again after it is offline.")
            }
        }
    }

    private fun updateAddress() {
        val custom = customAddress.text.toString().trim()
        val slug = serverName.text.toString().lowercase()
            .replace("_","-").replace(Regex("[^a-z0-9-]+"),"-")
            .replace(Regex("-+"),"-").trim('-').ifBlank { "my-server" }
        val addr = custom.ifBlank { "$slug.sliqado.org" }
        addressValue.text = "Server address\n$addr\n\nJava: ${intOf(javaPort,25565,1024,65535)}  ·  Bedrock: ${intOf(bedrockPort,19132,1024,65535)}"
    }

    private fun applyScreenOn(enabled: Boolean) {
        if(enabled) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }

    private fun get(url: String): String {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 12000
        c.readTimeout = 20000
        c.setRequestProperty("User-Agent","SliqServer/3.0 (https://sliqado.org/server/)")
        c.setRequestProperty("Accept","application/json")
        c.inputStream.bufferedReader().use { return it.readText() }
    }

    private fun intOf(e: EditText, def: Int, min: Int, max: Int): Int =
        (e.text.toString().toIntOrNull() ?: def).coerceIn(min,max)

    private fun section(page: LinearLayout, title: String, subtitle: String = ""): LinearLayout {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14),dp(14),dp(14),dp(14))
            setBackgroundColor(panel)
        }
        val lp = match().apply { setMargins(0,dp(10),0,0) }
        page.addView(box, lp)
        box.addView(label(title, white, 19f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) })
        if(subtitle.isNotBlank()) box.addView(label(subtitle, muted, 12f))
        return box
    }

    private fun metricCard(parent: LinearLayout, title: String, value: String, w: Float): TextView {
        val box = LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL; setBackgroundColor(field); setPadding(dp(10),dp(10),dp(10),dp(10))
        }
        val lp = LinearLayout.LayoutParams(0, dp(82), w).apply { setMargins(dp(3),dp(3),dp(3),dp(3)) }
        parent.addView(box,lp)
        box.addView(label(title, muted, 10f))
        val v = label(value, white, 17f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) }
        box.addView(v)
        return v
    }

    private fun edit(parent: LinearLayout, title: String, initial: String, numeric: Boolean = false): EditText {
        parent.addView(label(title, muted, 11f))
        val e = EditText(this).apply {
            setText(initial); setTextColor(white); setHintTextColor(muted); setBackgroundColor(field)
            setPadding(dp(10),0,dp(10),0); setSingleLine(true)
            if(numeric) inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }
        parent.addView(e, match(dp(48)).apply { setMargins(0,dp(3),0,dp(8)) })
        return e
    }

    private fun spinner(parent: LinearLayout, title: String, items: List<String>): Spinner {
        parent.addView(label(title, muted, 11f))
        val s = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivityV3, android.R.layout.simple_spinner_dropdown_item, items)
            setBackgroundColor(field)
        }
        parent.addView(s, match(dp(48)).apply { setMargins(0,dp(3),0,dp(8)) })
        return s
    }

    private fun switch(parent: LinearLayout, title: String, checked: Boolean): Switch {
        val s = Switch(this).apply { text=title; isChecked=checked; setTextColor(white); textSize=14f }
        parent.addView(s, match(dp(46)))
        return s
    }

    private fun actionButton(text: String, color: Int, action: () -> Unit): Button =
        Button(this).apply {
            this.text=text; setTextColor(if(color==green) Color.rgb(4,19,10) else white)
            setBackgroundColor(color); setOnClickListener { action() }
        }

    private fun label(text: String, color: Int, size: Float): TextView =
        TextView(this).apply { this.text=text; setTextColor(color); textSize=size; setPadding(0,dp(3),0,dp(3)) }

    private fun match(height: Int = LinearLayout.LayoutParams.WRAP_CONTENT) =
        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, height)

    private fun weight() =
        LinearLayout.LayoutParams(0, dp(52), 1f).apply { setMargins(dp(3),dp(3),dp(3),dp(3)) }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun setSpinner(s: Spinner, items: List<String>, value: String) {
        val i = items.indexOf(value)
        if(i >= 0) s.setSelection(i)
    }

    private fun toast(text: String) = Toast.makeText(this, text, Toast.LENGTH_LONG).show()
}
