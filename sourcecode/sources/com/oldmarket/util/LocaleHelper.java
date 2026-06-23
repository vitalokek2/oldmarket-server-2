package com.oldmarket.util;

import android.content.Context;
import android.content.res.Configuration;
import java.util.Locale;

/* JADX INFO: loaded from: classes.dex */
public class LocaleHelper {
    public static void applySavedLocale(Context context) {
        String lang = Prefs.getLang(context);
        if (lang != null && lang.length() != 0) {
            Locale locale = new Locale(lang);
            Locale.setDefault(locale);
            Configuration config = new Configuration();
            config.locale = locale;
            context.getResources().updateConfiguration(config, context.getResources().getDisplayMetrics());
        }
    }
}
