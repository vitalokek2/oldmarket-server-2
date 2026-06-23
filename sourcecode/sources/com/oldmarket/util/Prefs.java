package com.oldmarket.util;

import android.content.Context;
import android.content.SharedPreferences;

/* JADX INFO: loaded from: classes.dex */
public class Prefs {
    private static final String P = "oldmarket_prefs";

    private static SharedPreferences sp(Context c) {
        return c.getSharedPreferences(P, 0);
    }

    public static String getServer(Context c) {
        return sp(c).getString("server", "94.156.115.120");
    }

    public static void setServer(Context c, String host) {
        sp(c).edit().putString("server", host).commit();
    }

    public static int getPerPage(Context c) {
        return sp(c).getInt("per_page", 15);
    }

    public static void setPerPage(Context c, int v) {
        if (v < 5) {
            v = 5;
        }
        if (v > 200) {
            v = 200;
        }
        sp(c).edit().putInt("per_page", v).commit();
    }

    public static String getLang(Context c) {
        return sp(c).getString("lang", "ru");
    }

    public static void setLang(Context c, String lang) {
        if (lang == null) {
            lang = "ru";
        }
        sp(c).edit().putString("lang", lang).commit();
    }

    public static int getUserId(Context c) {
        return sp(c).getInt("user_id", 0);
    }

    public static String getUsername(Context c) {
        return sp(c).getString("username", "");
    }

    public static boolean isLoggedIn(Context c) {
        return getUserId(c) > 0;
    }

    public static void setAuth(Context c, int userId, String username) {
        SharedPreferences.Editor editorPutInt = sp(c).edit().putInt("user_id", userId);
        if (username == null) {
            username = "";
        }
        editorPutInt.putString("username", username).commit();
    }

    public static void logout(Context c) {
        sp(c).edit().remove("user_id").remove("username").commit();
    }

    public static boolean isBannerHidden(Context c) {
        return c.getSharedPreferences("prefs", 0).getBoolean("hide_banner", false);
    }

    public static void setBannerHidden(Context c, boolean v) {
        c.getSharedPreferences("prefs", 0).edit().putBoolean("hide_banner", v).commit();
    }

    public static boolean isApi25WarningShown(Context c) {
        return sp(c).getBoolean("api25_warning_shown", false);
    }

    public static void setApi25WarningShown(Context c, boolean v) {
        sp(c).edit().putBoolean("api25_warning_shown", v).commit();
    }

    public static boolean isAutoInstallRoot(Context c) {
        return sp(c).getBoolean("auto_install_root", false);
    }

    public static void setAutoInstallRoot(Context c, boolean v) {
        sp(c).edit().putBoolean("auto_install_root", v).commit();
    }

    public static boolean isRootGranted(Context c) {
        return sp(c).getBoolean("root_granted", false);
    }

    public static void setRootGranted(Context c, boolean v) {
        sp(c).edit().putBoolean("root_granted", v).commit();
    }

    public static String getIconPack(Context c) {
        return sp(c).getString("icon_pack", IconPack.PACK_DEFAULT);
    }

    public static void setIconPack(Context c, String v) {
        if (v == null || v.length() == 0) {
            v = IconPack.PACK_DEFAULT;
        }
        sp(c).edit().putString("icon_pack", v).commit();
    }

    public static long getLastClientUpdateCheckAt(Context c) {
        return sp(c).getLong("last_client_update_check_at", 0L);
    }

    public static void setLastClientUpdateCheckAt(Context c, long v) {
        sp(c).edit().putLong("last_client_update_check_at", v).commit();
    }

    public static long getLastAnalyticsSentAt(Context c) {
        return sp(c).getLong("last_analytics_sent_at", 0L);
    }

    public static void setLastAnalyticsSentAt(Context c, long v) {
        sp(c).edit().putLong("last_analytics_sent_at", v).commit();
    }
}
