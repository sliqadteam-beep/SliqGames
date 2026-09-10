package org.sliqado.sliqserver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class ServerBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED && intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        val prefs = context.getSharedPreferences("sliqserver_v3", Context.MODE_PRIVATE)
        if (!prefs.getBoolean("server_enabled", true)) return

        val pending = goAsync()
        Thread {
            try {
                // The Termux:Boot script is the primary boot path. This is an extra immediate retry
                // from SliqServer itself after Android boot or an APK update.
                val cmd = "mkdir -p ~/sliqserver; rm -f ~/sliqserver/manual-off; if [ -f ~/sliqserver/sliqserver-manager.sh ] && ! pgrep -f '[s]liqserver-manager.sh' >/dev/null 2>&1; then nohup bash ~/sliqserver/sliqserver-manager.sh >> ~/sliqserver/manager.log 2>&1 </dev/null & fi"
                TermuxBridge.run(context, cmd, true)
            } finally {
                pending.finish()
            }
        }.start()
    }
}
