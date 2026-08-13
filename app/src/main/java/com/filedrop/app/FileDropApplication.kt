package com.filedrop.app

import android.app.Application
import android.os.Build
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags

class FileDropApplication : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        container.notifications.ensureChannels()

        FdLog.i(
            LogTags.APP,
            "FileDrop ${BuildConfig.VERSION_NAME} démarré sur Android ${Build.VERSION.RELEASE} " +
                "(API ${Build.VERSION.SDK_INT}), appareil « ${container.settings.deviceName.value} », " +
                "empreinte ${container.identityStore.identity.fingerprint}",
        )
    }
}
