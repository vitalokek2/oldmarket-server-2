package com.oldmarket.service;

import android.R;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Environment;
import android.os.IBinder;
import android.widget.RemoteViews;
import com.oldmarket.ui.AppDetailActivity;
import com.oldmarket.util.LocaleHelper;
import com.oldmarket.util.Prefs;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class DownloadService extends Service {
    public static final String ACTION_CANCEL = "com.oldmarket.DOWNLOAD_CANCEL";
    public static final String ACTION_PROGRESS = "com.oldmarket.DOWNLOAD_PROGRESS";
    public static final String ACTION_START = "com.oldmarket.DOWNLOAD_START";
    private static final String PREFS = "download_state";
    private static final Class<?>[] START_FOREGROUND_SIG = {Integer.TYPE, Notification.class};
    private static final Class<?>[] STOP_FOREGROUND_SIG = {Boolean.TYPE};
    private static final ConcurrentHashMap<Integer, TaskInfo> TASKS = new ConcurrentHashMap<>();
    private Method mSetForeground;
    private Method mStartForeground;
    private Method mStopForeground;
    private final Object[] mStartForegroundArgs = new Object[2];
    private final Object[] mStopForegroundArgs = new Object[1];
    private final Object[] mSetForegroundArgs = new Object[1];

    private static class TaskInfo {
        int appId;
        String appName;
        volatile boolean cancel;
        String fileName;
        String filePath;
        String icon;
        boolean installing;
        int percent;
        long speed;
        String statusText;

        private TaskInfo() {
            this.appName = "";
            this.icon = "";
            this.cancel = false;
            this.percent = 0;
            this.speed = 0L;
            this.installing = false;
            this.statusText = "0%";
            this.fileName = "";
            this.filePath = "";
        }

        /* synthetic */ TaskInfo(TaskInfo taskInfo) {
            this();
        }
    }

    @Override // android.app.Service
    public void onCreate() {
        super.onCreate();
        try {
            this.mStartForeground = getClass().getMethod("startForeground", START_FOREGROUND_SIG);
            this.mStopForeground = getClass().getMethod("stopForeground", STOP_FOREGROUND_SIG);
        } catch (NoSuchMethodException e) {
            this.mStartForeground = null;
            this.mStopForeground = null;
        }
        try {
            this.mSetForeground = getClass().getMethod("setForeground", Boolean.TYPE);
        } catch (NoSuchMethodException e2) {
            this.mSetForeground = null;
        }
    }

    @Override // android.app.Service
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override // android.app.Service
    public int onStartCommand(Intent intent, int flags, int startId) {
        LocaleHelper.applySavedLocale(this);
        if (intent == null) {
            return 2;
        }
        String action = intent.getAction();
        if (ACTION_CANCEL.equals(action)) {
            int id = intent.getIntExtra("app_id", -1);
            TaskInfo t = TASKS.get(Integer.valueOf(id));
            if (t != null) {
                t.cancel = true;
            }
            return 2;
        }
        if (ACTION_START.equals(action)) {
            int appId = intent.getIntExtra("app_id", -1);
            final String url = intent.getStringExtra("url");
            String fileName = intent.getStringExtra("file_name");
            String appName = intent.getStringExtra("app_name");
            String icon = intent.getStringExtra("icon");
            if (appId < 0 || url == null || url.length() == 0) {
                return 2;
            }
            if (TASKS.containsKey(Integer.valueOf(appId))) {
                return 1;
            }
            final TaskInfo t2 = new TaskInfo(null);
            t2.appId = appId;
            if (appName == null) {
                appName = "";
            }
            t2.appName = appName;
            if (icon == null) {
                icon = "";
            }
            t2.icon = icon;
            if (fileName == null) {
                fileName = "oldmarket_" + appId + ".apk";
            }
            t2.fileName = fileName;
            TASKS.put(Integer.valueOf(appId), t2);
            persistTasks();
            sendStateBroadcast(t2, false, false, false);
            new Thread(new Runnable() { // from class: com.oldmarket.service.DownloadService.1
                @Override // java.lang.Runnable
                public void run() throws Throwable {
                    DownloadService.this.runDownload(t2, url);
                }
            }).start();
        }
        return 1;
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, 0);
    }

    private int getCompleteNotifIcon() {
        int id = getResources().getIdentifier("stat_sys_install_complete", "drawable", getPackageName());
        return id != 0 ? id : R.drawable.stat_sys_download_done;
    }

    private synchronized void persistTasks() {
        JSONArray arr = new JSONArray();
        try {
            for (Map.Entry<Integer, TaskInfo> e : TASKS.entrySet()) {
                TaskInfo t = e.getValue();
                JSONObject o = new JSONObject();
                o.put("app_id", t.appId);
                o.put("app_name", t.appName);
                o.put("icon", t.icon);
                o.put("percent", t.percent);
                o.put("speed_bps", t.speed);
                o.put("installing", t.installing);
                o.put("status_text", t.statusText);
                o.put("file_name", t.fileName);
                o.put("file_path", t.filePath);
                arr.put(o);
            }
        } catch (Exception e2) {
        }
        prefs().edit().putString("tasks_json", arr.toString()).commit();
    }

    private void sendStateBroadcast(TaskInfo t, boolean done, boolean error, boolean cancelled) {
        Intent p = new Intent(ACTION_PROGRESS);
        p.putExtra("app_id", t.appId);
        p.putExtra("percent", t.percent);
        p.putExtra("speed_bps", t.speed);
        p.putExtra("done", done);
        p.putExtra("error", error);
        p.putExtra("cancelled", cancelled);
        p.putExtra("active", (done || error || cancelled) ? false : true);
        p.putExtra("installing", t.installing);
        p.putExtra("app_name", t.appName);
        p.putExtra("status_text", t.statusText);
        p.putExtra("icon", t.icon);
        if (t.filePath != null && t.filePath.length() > 0) {
            p.putExtra("file_path", t.filePath);
        }
        sendBroadcast(p);
    }

    private File outFile(String fileName) {
        File dir;
        if (Environment.getExternalStorageState().equals("mounted")) {
            dir = new File(Environment.getExternalStorageDirectory(), "OldMarket");
        } else {
            dir = getCacheDir();
        }
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return new File(dir, fileName);
    }

    private PendingIntent progressPendingIntent(int appId) {
        Intent open = new Intent(this, (Class<?>) AppDetailActivity.class);
        open.putExtra("app_id", appId);
        open.setFlags(603979776);
        return PendingIntent.getActivity(this, appId, open, 134217728);
    }

    private PendingIntent completePendingIntent(String filePath, int appId) {
        Intent open = new Intent("android.intent.action.VIEW");
        open.setDataAndType(Uri.fromFile(new File(filePath)), "application/vnd.android.package-archive");
        open.setFlags(268435456);
        return PendingIntent.getActivity(this, appId + 10000, open, 134217728);
    }

    private Notification makeProgressNotification(TaskInfo t) {
        Notification n = new Notification(R.drawable.stat_sys_download, null, System.currentTimeMillis());
        n.flags = 10;
        n.contentIntent = progressPendingIntent(t.appId);
        RemoteViews rv = new RemoteViews(getPackageName(), com.oldmarket.R.layout.notification_download);
        rv.setTextViewText(com.oldmarket.R.id.notifTitle, (t.appName == null || t.appName.length() == 0) ? getString(com.oldmarket.R.string.downloading) : t.appName);
        rv.setTextViewText(com.oldmarket.R.id.notifText, t.statusText);
        rv.setProgressBar(com.oldmarket.R.id.notifProgress, 100, Math.max(0, Math.min(100, t.percent)), t.installing);
        n.contentView = rv;
        return n;
    }

    private Notification makeSimpleNotification(String title, String text, PendingIntent pi, int iconRes) {
        Notification n = new Notification(iconRes, null, System.currentTimeMillis());
        n.flags = 24;
        n.contentIntent = pi;
        RemoteViews rv = new RemoteViews(getPackageName(), com.oldmarket.R.layout.notification_simple);
        rv.setTextViewText(com.oldmarket.R.id.notifTitle, title);
        rv.setTextViewText(com.oldmarket.R.id.notifText, text);
        n.contentView = rv;
        return n;
    }

    private void compatStartForeground(int id, Notification notification) {
        if (this.mStartForeground != null) {
            this.mStartForegroundArgs[0] = Integer.valueOf(id);
            this.mStartForegroundArgs[1] = notification;
            try {
                this.mStartForeground.invoke(this, this.mStartForegroundArgs);
                return;
            } catch (Exception e) {
            }
        }
        if (this.mSetForeground != null) {
            try {
                this.mSetForegroundArgs[0] = Boolean.TRUE;
                this.mSetForeground.invoke(this, this.mSetForegroundArgs);
            } catch (Exception e2) {
            }
        }
        NotificationManager nm = (NotificationManager) getSystemService("notification");
        nm.notify(id, notification);
    }

    private void compatStopForeground(int id) {
        if (this.mStopForeground != null) {
            this.mStopForegroundArgs[0] = Boolean.TRUE;
            try {
                this.mStopForeground.invoke(this, this.mStopForegroundArgs);
                return;
            } catch (Exception e) {
            }
        }
        NotificationManager nm = (NotificationManager) getSystemService("notification");
        nm.cancel(id);
        if (this.mSetForeground != null) {
            try {
                this.mSetForegroundArgs[0] = Boolean.FALSE;
                this.mSetForeground.invoke(this, this.mSetForegroundArgs);
            } catch (Exception e2) {
            }
        }
    }

    private void notifyProgress(TaskInfo t) {
        NotificationManager nm = (NotificationManager) getSystemService("notification");
        Notification n = makeProgressNotification(t);
        nm.notify(t.appId + 1000, n);
        compatStartForeground(t.appId + 1000, n);
    }

    private void notifyComplete(TaskInfo t) {
        NotificationManager nm = (NotificationManager) getSystemService("notification");
        nm.notify(t.appId + 1000, makeSimpleNotification(getString(com.oldmarket.R.string.download_complete), getString(com.oldmarket.R.string.download_complete), completePendingIntent(t.filePath, t.appId), getCompleteNotifIcon()));
    }

    private void notifyInstalled(TaskInfo t) {
        String text;
        NotificationManager nm = (NotificationManager) getSystemService("notification");
        if (t.appName == null || t.appName.length() == 0) {
            text = getString(com.oldmarket.R.string.app_installed);
        } else {
            text = getString(com.oldmarket.R.string.app_installed_named, new Object[]{t.appName});
        }
        nm.notify(t.appId + 1000, makeSimpleNotification(getString(com.oldmarket.R.string.app_installed), text, progressPendingIntent(t.appId), getCompleteNotifIcon()));
    }

    private void launchPackageInstaller(String filePath) {
        try {
            Intent open = new Intent("android.intent.action.VIEW");
            open.setDataAndType(Uri.fromFile(new File(filePath)), "application/vnd.android.package-archive");
            open.setFlags(268435456);
            startActivity(open);
        } catch (Exception e) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void runDownload(TaskInfo t, String urlStr) throws Throwable {
        HttpURLConnection conn = null;
        InputStream in = null;
        FileOutputStream out = null;
        File f = outFile(t.fileName);
        long lastNotifyTime = 0;
        int lastNotifyPercent = -1;
        int lastBroadcastPercent = -1;
        try {
            try {
                notifyProgress(t);
                URL url = new URL(urlStr);
                conn = (HttpURLConnection) url.openConnection();
                conn.setInstanceFollowRedirects(true);
                conn.setConnectTimeout(12000);
                conn.setReadTimeout(30000);
                conn.connect();
                int len = conn.getContentLength();
                in = conn.getInputStream();
                FileOutputStream out2 = new FileOutputStream(f);
                try {
                    byte[] buf = new byte[8192];
                    long total = 0;
                    long speedWindowStartTime = System.currentTimeMillis();
                    long speedWindowStartBytes = 0;
                    while (true) {
                        int r = in.read(buf);
                        if (r == -1) {
                            t.filePath = f.getAbsolutePath();
                            if (Prefs.isAutoInstallRoot(this)) {
                                t.installing = true;
                                t.statusText = getString(com.oldmarket.R.string.installing);
                                persistTasks();
                                notifyProgress(t);
                                sendStateBroadcast(t, false, false, false);
                                boolean installed = installSilently(t.filePath);
                                TASKS.remove(Integer.valueOf(t.appId));
                                persistTasks();
                                if (installed) {
                                    notifyInstalled(t);
                                    sendStateBroadcast(t, true, false, false);
                                } else {
                                    notifyComplete(t);
                                    launchPackageInstaller(t.filePath);
                                    sendStateBroadcast(t, true, false, false);
                                }
                            } else {
                                TASKS.remove(Integer.valueOf(t.appId));
                                persistTasks();
                                notifyComplete(t);
                                launchPackageInstaller(t.filePath);
                                sendStateBroadcast(t, true, false, false);
                            }
                            if (out2 != null) {
                                try {
                                    out2.close();
                                } catch (Exception e) {
                                }
                            }
                            if (in != null) {
                                try {
                                    in.close();
                                } catch (Exception e2) {
                                }
                            }
                            if (conn != null) {
                                try {
                                    conn.disconnect();
                                } catch (Exception e3) {
                                }
                            }
                            try {
                                compatStopForeground(t.appId + 1000);
                            } catch (Exception e4) {
                            }
                            stopSelf();
                            return;
                        }
                        if (t.cancel) {
                            throw new RuntimeException("cancel");
                        }
                        out2.write(buf, 0, r);
                        total += (long) r;
                        int percent = len > 0 ? (int) ((100 * total) / ((long) len)) : 0;
                        if (percent < t.percent) {
                            int i = t.percent;
                        } else {
                            t.percent = percent;
                        }
                        long now = System.currentTimeMillis();
                        long dt = now - speedWindowStartTime;
                        long db = total - speedWindowStartBytes;
                        if (dt > 0) {
                            t.speed = (1000 * db) / dt;
                        }
                        String speedText = t.speed >= 1048576 ? String.format("%.1f MB/s", Float.valueOf((t.speed / 1024.0f) / 1024.0f)) : String.valueOf(Math.max(1L, t.speed / 1024)) + " KB/s";
                        t.statusText = String.valueOf(t.percent) + "%  -  " + speedText;
                        if (t.percent >= 100 || (now - lastNotifyTime >= 2500 && t.percent >= lastNotifyPercent + 5)) {
                            lastNotifyTime = now;
                            lastNotifyPercent = t.percent;
                            notifyProgress(t);
                        }
                        if (t.percent >= 100 || t.percent >= lastBroadcastPercent + 1) {
                            lastBroadcastPercent = t.percent;
                            persistTasks();
                            sendStateBroadcast(t, false, false, false);
                        }
                        if (dt >= 1000) {
                            speedWindowStartTime = now;
                            speedWindowStartBytes = total;
                        }
                    }
                } catch (Exception e5) {
                    out = out2;
                    TASKS.remove(Integer.valueOf(t.appId));
                    persistTasks();
                    try {
                        ((NotificationManager) getSystemService("notification")).cancel(t.appId + 1000);
                    } catch (Exception e6) {
                    }
                    sendStateBroadcast(t, false, !t.cancel, t.cancel);
                    if (out != null) {
                        try {
                            out.close();
                        } catch (Exception e7) {
                        }
                    }
                    if (in != null) {
                        try {
                            in.close();
                        } catch (Exception e8) {
                        }
                    }
                    if (conn != null) {
                        try {
                            conn.disconnect();
                        } catch (Exception e9) {
                        }
                    }
                    try {
                        compatStopForeground(t.appId + 1000);
                    } catch (Exception e10) {
                    }
                    stopSelf();
                } catch (Throwable th) {
                    th = th;
                    out = out2;
                    if (out != null) {
                        try {
                            out.close();
                        } catch (Exception e11) {
                        }
                    }
                    if (in != null) {
                        try {
                            in.close();
                        } catch (Exception e12) {
                        }
                    }
                    if (conn != null) {
                        try {
                            conn.disconnect();
                        } catch (Exception e13) {
                        }
                    }
                    try {
                        compatStopForeground(t.appId + 1000);
                    } catch (Exception e14) {
                    }
                    stopSelf();
                    throw th;
                }
            } catch (Throwable th2) {
                th = th2;
            }
        } catch (Exception e15) {
        }
    }

    private boolean installSilently(String apkPath) throws Throwable {
        String safePath;
        DataOutputStream os;
        Process p = null;
        DataOutputStream os2 = null;
        try {
            safePath = apkPath.replace("'", "'\\''");
            p = Runtime.getRuntime().exec("su");
            os = new DataOutputStream(p.getOutputStream());
        } catch (Exception e) {
        } catch (Throwable th) {
            th = th;
        }
        try {
            os.writeBytes("pm install -r '" + safePath + "'\n");
            os.writeBytes("exit\n");
            os.flush();
            int rc = p.waitFor();
            z = rc == 0;
            if (os != null) {
                try {
                    os.close();
                } catch (Exception e2) {
                }
            }
            if (p != null) {
                try {
                    p.destroy();
                } catch (Exception e3) {
                }
            }
        } catch (Exception e4) {
            os2 = os;
            if (os2 != null) {
                try {
                    os2.close();
                } catch (Exception e5) {
                }
            }
            if (p != null) {
                try {
                    p.destroy();
                } catch (Exception e6) {
                }
            }
        } catch (Throwable th2) {
            th = th2;
            os2 = os;
            if (os2 != null) {
                try {
                    os2.close();
                } catch (Exception e7) {
                }
            }
            if (p == null) {
                throw th;
            }
            try {
                p.destroy();
                throw th;
            } catch (Exception e8) {
                throw th;
            }
        }
        return z;
    }
}
