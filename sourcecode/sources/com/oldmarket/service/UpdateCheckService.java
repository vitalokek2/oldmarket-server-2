package com.oldmarket.service;

import android.R;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.IBinder;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.ui.AppDetailActivity;
import com.oldmarket.util.LocaleHelper;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class UpdateCheckService extends Service {
    @Override // android.app.Service
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override // android.app.Service
    public int onStartCommand(Intent intent, int flags, int startId) {
        LocaleHelper.applySavedLocale(this);
        new Thread(new Runnable() { // from class: com.oldmarket.service.UpdateCheckService.1
            @Override // java.lang.Runnable
            public void run() {
                UpdateCheckService.this.checkUpdates();
                UpdateCheckService.this.stopSelf();
            }
        }).start();
        return 2;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void checkUpdates() {
        try {
            HashMap<String, PackageInfo> installed = new HashMap<>();
            PackageManager pm = getPackageManager();
            List<PackageInfo> pkgs = pm.getInstalledPackages(0);
            for (int i = 0; i < pkgs.size(); i++) {
                PackageInfo pi = pkgs.get(i);
                if (pi != null && pi.packageName != null) {
                    installed.put(pi.packageName, pi);
                }
            }
            scanEndpoint("/api/apps?is_game=0", installed);
            scanEndpoint("/api/apps?is_game=1", installed);
        } catch (Exception e) {
        }
    }

    private void scanEndpoint(String endpoint, Map<String, PackageInfo> installed) {
        PackageInfo pi;
        int serverVersionCode;
        try {
            String s = Http.getString(String.valueOf(Api.baseUrl(this)) + endpoint);
            if (s != null) {
                JSONArray arr = new JSONArray(s);
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject o = arr.getJSONObject(i);
                    String pkg = o.optString("package", o.optString("package_name", ""));
                    if (pkg != null && pkg.length() != 0 && (pi = installed.get(pkg)) != null && (serverVersionCode = o.optInt("versionCode", o.optInt("version_code", 0))) > 0 && serverVersionCode > pi.versionCode) {
                        int appId = o.optInt("id", 0);
                        String appName = o.optString("name", pkg);
                        int lastNotified = notifiedPrefs().getInt("upd_" + pkg, 0);
                        if (serverVersionCode > lastNotified) {
                            showUpdateNotification(appId, appName);
                            notifiedPrefs().edit().putInt("upd_" + pkg, serverVersionCode).commit();
                        }
                    }
                }
            }
        } catch (Exception e) {
        }
    }

    private SharedPreferences notifiedPrefs() {
        return getSharedPreferences("update_notify_state", 0);
    }

    private void showUpdateNotification(int appId, String appName) {
        NotificationManager nm = (NotificationManager) getSystemService("notification");
        Intent open = new Intent(this, (Class<?>) AppDetailActivity.class);
        open.putExtra("app_id", appId);
        open.setFlags(335544320);
        PendingIntent pi = PendingIntent.getActivity(this, appId + 20000, open, 134217728);
        int iconRes = getResources().getIdentifier("stat_notify_marketplace_update", "drawable", getPackageName());
        if (iconRes == 0) {
            iconRes = R.drawable.stat_notify_more;
        }
        Notification n = new Notification(iconRes, null, System.currentTimeMillis());
        n.flags = 16;
        try {
            Method m = n.getClass().getMethod("setLatestEventInfo", Context.class, CharSequence.class, CharSequence.class, PendingIntent.class);
            m.invoke(n, this, getString(com.oldmarket.R.string.updates_available), getString(com.oldmarket.R.string.update_available_for_named, new Object[]{appName}), pi);
        } catch (Exception e) {
        }
        nm.notify(appId + 20000, n);
    }
}
