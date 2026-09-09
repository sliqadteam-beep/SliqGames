package org.sliqado.sliqserver

import android.content.Context
import android.content.Intent
import android.widget.Toast

object TermuxBridge {
    private const val TERMUX_SERVICE = "com.termux.app.RunCommandService"
    private const val TERMUX_PACKAGE = "com.termux"

    fun run(context: Context, command: String, background: Boolean = true): Boolean {
        return try {
            val intent = Intent().apply {
                setClassName(TERMUX_PACKAGE, TERMUX_SERVICE)
                action = "com.termux.RUN_COMMAND"
                putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash")
                putExtra("com.termux.RUN_COMMAND_ARGUMENTS", arrayOf("-lc", command))
                putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home")
                putExtra("com.termux.RUN_COMMAND_BACKGROUND", background)
            }
            context.startService(intent)
            true
        } catch (e: Exception) {
            Toast.makeText(context, "Termux is required. Install Termux and enable allow-external-apps.", Toast.LENGTH_LONG).show()
            false
        }
    }

    fun q(value: String): String = "'" + value.replace("'", "'\\''") + "'"
}
