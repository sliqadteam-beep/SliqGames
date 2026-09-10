import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_android_java_fallback_patch.py <MainActivityV4.kt>")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    helper = r'''    private fun java21FallbackVersion(): String? {
        val adapter = versionSpinner.adapter ?: return null
        val preferred = listOf("1.21.11", "1.21.10", "1.21.8", "1.21.5", "1.21.4", "1.20.6")
        for (candidate in preferred) {
            for (i in 0 until adapter.count) {
                val item = adapter.getItem(i)?.toString() ?: continue
                if (item == candidate && requiredJavaFor(item) <= 21) return item
            }
        }
        for (i in 0 until adapter.count) {
            val item = adapter.getItem(i)?.toString() ?: continue
            if (requiredJavaFor(item) <= 21) return item
        }
        return null
    }

    private fun selectVersion(version: String): Boolean {
        val adapter = versionSpinner.adapter ?: return false
        for (i in 0 until adapter.count) {
            if (adapter.getItem(i)?.toString() == version) {
                versionSpinner.setSelection(i)
                prefs.edit().putString("version", version).apply()
                return true
            }
        }
        return false
    }

    private fun fallbackFromJava25(selectedVersion: String): Boolean {
        val fallback = java21FallbackVersion() ?: return false
        if (fallback == selectedVersion) return false
        if (!selectVersion(fallback)) return false

        statusValue.text = "● STARTING"
        statusValue.setTextColor(amber)
        if (::startEtaValue.isInitialized) {
            startEtaValue.text = "Java 25 unavailable · switching to $fallback (Java 21)…"
        }
        toast("Java 25 is unavailable on this Android device. SliqServer is switching to $fallback with Java 21.")
        handler.postDelayed({ downloadServer(true) }, 600)
        return true
    }

'''

    marker = "    private fun startServer() {\n"
    if "private fun java21FallbackVersion()" not in text:
        if marker not in text:
            raise SystemExit("Could not find Android startServer() insertion point")
        text = text.replace(marker, helper + marker, 1)

    # Replace the Java failure dialog with automatic Java-21/Minecraft fallback
    # when the selected server version requires Java 25.
    pattern = re.compile(
        r'''                    r\.stdout\.contains\("NOJAVA"\) -> \{\n'''
        r'''(?P<body>.*?)'''
        r'''                    \}\n''',
        re.S,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit("Could not find Android NOJAVA result branch")

    replacement = r'''                    r.stdout.contains("NOJAVA") -> {
                        if (requiredJava >= 25 && fallbackFromJava25(selectedVersion)) {
                            // The fallback downloader will install Java 21, replace server.jar,
                            // and call Start again automatically.
                        } else {
                            statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                            finishStartupUi(false)
                            val details = r.stdout.trim().ifBlank { "Java runtime unavailable" }
                            AlertDialog.Builder(this).setTitle("Java runtime setup failed")
                                .setMessage("SliqServer could not prepare a compatible Java runtime on this device. Details: $details\n\nOpen Termux once, make sure it has internet access, and enable allow-external-apps=true.")
                                .setPositiveButton("OK", null).show()
                        }
                    }
'''
    text = text[:match.start()] + replacement + text[match.end():]

    # Add a lightweight architecture check to the generated Termux shell script.
    # We only hard-stop old 32-bit x86, where current Termux OpenJDK packages are not viable.
    java_check_anchor = "CURRENT=0\nif command -v java >/dev/null 2>&1; then"
    arch_check = '''ARCH=$(uname -m 2>/dev/null || echo unknown)\ncase "$ARCH" in\n  i386|i486|i586|i686) echo "UNSUPPORTED_ARCH:$ARCH"; exit 6 ;;\nesac\nCURRENT=0\nif command -v java >/dev/null 2>&1; then'''
    if "UNSUPPORTED_ARCH:" not in text:
        if java_check_anchor not in text:
            # The Kotlin escaping step may already have rewritten shell variables.
            escaped_anchor = "CURRENT=0\nif command -v java >/dev/null 2>&1; then"
            if escaped_anchor not in text:
                raise SystemExit("Could not find Android Java preflight shell block")
        text = text.replace(java_check_anchor, arch_check, 1)

    # Handle the architecture error explicitly if it occurs.
    nojava_pos = text.find('r.stdout.contains("NOJAVA") ->')
    if nojava_pos < 0:
        raise SystemExit("NOJAVA branch vanished after patch")
    branch_anchor = '                    r.stdout.contains("NOJAVA") -> {'
    arch_branch = '''                    r.stdout.contains("UNSUPPORTED_ARCH") -> {
                        statusValue.text = "● OFFLINE"; statusValue.setTextColor(red)
                        finishStartupUi(false)
                        AlertDialog.Builder(this).setTitle("Android device not supported")
                            .setMessage("This Android device uses an old 32-bit x86 CPU architecture that cannot run the required current Java runtime. A 64-bit ARM/ARM64 or x86_64 Android device is required.")
                            .setPositiveButton("OK", null).show()
                    }
'''
    if 'r.stdout.contains("UNSUPPORTED_ARCH") ->' not in text:
        text = text.replace(branch_anchor, arch_branch + branch_anchor, 1)

    path.write_text(text, encoding="utf-8")
    print(f"Applied Android Java 25 -> Java 21 fallback patch: {path}")


if __name__ == "__main__":
    main()
