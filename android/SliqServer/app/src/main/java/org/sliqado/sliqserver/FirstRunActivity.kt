package org.sliqado.sliqserver

import android.app.Activity
import android.content.Intent
import android.os.Bundle

class FirstRunActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("sliqserver_v3", MODE_PRIVATE)
        if (!prefs.contains("eula_accepted")) {
            prefs.edit().putBoolean("server_enabled", false).apply()
        }
        startActivity(Intent(this, DedicatedServerActivity::class.java))
        finish()
    }
}
