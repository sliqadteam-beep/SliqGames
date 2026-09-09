package org.sliqado.sliqserver

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class AddonActivity : Activity() {
    private val bg = Color.rgb(7,17,31)
    private val panel = Color.rgb(13,27,45)
    private val blue = Color.rgb(37,99,235)
    private val white = Color.WHITE
    private val muted = Color.rgb(159,176,199)
    private lateinit var list: LinearLayout
    private lateinit var search: EditText
    private var kind = "plugin"
    private var version = "26.2"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        kind = intent.getStringExtra("kind") ?: "plugin"
        version = intent.getStringExtra("version") ?: "26.2"
        val outer = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(bg) }
        val top = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12),dp(12),dp(12),dp(12)) }
        top.addView(Button(this).apply { text="‹"; setOnClickListener{finish()} }, LinearLayout.LayoutParams(dp(52),dp(46)))
        top.addView(TextView(this).apply { text = if(kind=="plugin") "Plugins" else "Mods"; textSize=24f; setTextColor(white); setPadding(dp(12),0,0,0) }, LinearLayout.LayoutParams(0,LinearLayout.LayoutParams.WRAP_CONTENT,1f))
        outer.addView(top)
        val searchRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(dp(12),0,dp(12),dp(10)) }
        search = EditText(this).apply { hint = "Search Modrinth…"; setTextColor(white); setHintTextColor(muted); setBackgroundColor(panel) }
        searchRow.addView(search, LinearLayout.LayoutParams(0,dp(52),1f))
        searchRow.addView(Button(this).apply { text="SEARCH"; setTextColor(white); setBackgroundColor(blue); setOnClickListener{doSearch()} }, LinearLayout.LayoutParams(dp(110),dp(52)))
        outer.addView(searchRow)
        val scroll = ScrollView(this)
        list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12),0,dp(12),dp(24)) }
        scroll.addView(list); outer.addView(scroll,LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,0,1f))
        setContentView(outer)
        doSearch()
    }

    private fun doSearch() {
        val q = search.text.toString().trim()
        list.removeAllViews(); list.addView(label("Searching…", muted, 14f))
        Thread {
            try {
                val facets = if (kind == "plugin") "[[\"project_type:plugin\"]]" else "[[\"project_type:mod\"],[\"categories:fabric\"]]"
                val url = "https://api.modrinth.com/v2/search?query=${URLEncoder.encode(q,"UTF-8")}&limit=20&facets=${URLEncoder.encode(facets,"UTF-8")}"
                val json = JSONObject(get(url)); val hits = json.getJSONArray("hits")
                runOnUiThread { render(hits) }
            } catch (e: Exception) { runOnUiThread { list.removeAllViews(); list.addView(label("Search failed: ${e.message}", muted, 14f)) } }
        }.start()
    }

    private fun render(hits: JSONArray) {
        list.removeAllViews()
        for (i in 0 until hits.length()) {
            val p = hits.getJSONObject(i)
            val id = p.optString("project_id")
            val title = p.optString("title")
            val desc = p.optString("description")
            val card = LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(dp(14),dp(14),dp(14),dp(14)); setBackgroundColor(panel) }
            card.addView(label(title,white,18f)); card.addView(label(desc,muted,12f))
            card.addView(Button(this).apply { text="INSTALL"; setTextColor(white); setBackgroundColor(blue); setOnClickListener{ install(id,title,this) } })
            val lp = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,LinearLayout.LayoutParams.WRAP_CONTENT); lp.setMargins(0,0,0,dp(10)); list.addView(card,lp)
        }
        if (hits.length()==0) list.addView(label("No results",muted,14f))
    }

    private fun install(projectId: String, title: String, button: Button) {
        button.isEnabled=false; button.text="INSTALLING…"
        Thread {
            try {
                val versions = JSONArray(get("https://api.modrinth.com/v2/project/$projectId/version"))
                var chosen: JSONObject? = null
                for (i in 0 until versions.length()) {
                    val v = versions.getJSONObject(i)
                    val loaders = v.optJSONArray("loaders") ?: JSONArray()
                    val games = v.optJSONArray("game_versions") ?: JSONArray()
                    val loaderOk = contains(loaders, if(kind=="plugin") "paper" else "fabric") || (kind=="plugin" && contains(loaders,"spigot"))
                    if (loaderOk && (contains(games,version) || chosen==null)) { chosen=v; if(contains(games,version)) break }
                }
                if (chosen==null) throw Exception("No compatible ${if(kind=="plugin") "Paper" else "Fabric"} version found")
                val files = chosen!!.getJSONArray("files")
                var file = files.getJSONObject(0)
                for (i in 0 until files.length()) if (files.getJSONObject(i).optBoolean("primary",false)) file=files.getJSONObject(i)
                val url=file.getString("url"); val filename=file.getString("filename").replace(Regex("[^A-Za-z0-9._-]"),"_")
                val folder=if(kind=="plugin") "plugins" else "mods"
                val cmd="mkdir -p ~/sliqserver/$folder; curl -fL ${TermuxBridge.q(url)} -o ~/sliqserver/$folder/${TermuxBridge.q(filename)}"
                TermuxBridge.run(this,cmd)
                runOnUiThread { button.text="INSTALLED"; Toast.makeText(this,"$title install requested",Toast.LENGTH_SHORT).show() }
            } catch(e:Exception){ runOnUiThread { button.isEnabled=true; button.text="RETRY"; Toast.makeText(this,e.message ?: "Install failed",Toast.LENGTH_LONG).show() } }
        }.start()
    }

    private fun contains(a: JSONArray, s: String): Boolean { for(i in 0 until a.length()) if(a.optString(i).equals(s,true)) return true; return false }
    private fun get(url:String):String { val c=URL(url).openConnection() as HttpURLConnection; c.connectTimeout=10000;c.readTimeout=15000;c.setRequestProperty("User-Agent","SliqServer/0.2 (https://sliqado.org)"); c.inputStream.bufferedReader().use{return it.readText()} }
    private fun label(s:String,color:Int,size:Float)=TextView(this).apply{text=s;setTextColor(color);textSize=size;setPadding(0,dp(4),0,dp(4))}
    private fun dp(v:Int)=(v*resources.displayMetrics.density).toInt()
}
