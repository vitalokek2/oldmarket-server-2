package com.oldmarket.net;

import android.content.Context;
import com.oldmarket.util.Prefs;
import java.net.URLEncoder;

/* JADX INFO: loaded from: classes.dex */
public class Api {
    public static String baseUrl(Context c) {
        String host = Prefs.getServer(c);
        if (host == null) {
            host = "";
        }
        String host2 = host.trim();
        if (host2.length() == 0) {
            host2 = "94.156.115.120";
        }
        while (host2.endsWith("/")) {
            host2 = host2.substring(0, host2.length() - 1);
        }
        if (host2.endsWith("/api")) {
            host2 = host2.substring(0, host2.length() - 4);
        }
        while (host2.endsWith("/")) {
            host2 = host2.substring(0, host2.length() - 1);
        }
        if (!host2.startsWith("http://") && !host2.startsWith("https://")) {
            if (host2.indexOf(58) >= 0) {
                return "http://" + host2;
            }
            return "http://" + host2 + ":5000";
        }
        return host2;
    }

    public static String iconUrl(Context c, String iconFile) {
        return String.valueOf(baseUrl(c)) + "/html/apps/" + iconFile;
    }

    public static String bannerUrl(Context c, String bannerFile) {
        return String.valueOf(baseUrl(c)) + "/html/banners/" + bannerFile;
    }

    public static String screenshotUrl(Context c, String file) {
        return String.valueOf(baseUrl(c)) + "/html/screenshots/" + file;
    }

    public static String avatarUrl(Context c, String avatarFile) {
        return String.valueOf(baseUrl(c)) + "/html/avatars/" + avatarFile;
    }

    public static String loginUrl(Context c) {
        return String.valueOf(baseUrl(c)) + "/api/login";
    }

    public static String avatarsUrl(Context c) {
        return String.valueOf(baseUrl(c)) + "/api/avatars";
    }

    public static String userProfileUrl(Context c, int userId) {
        return String.valueOf(baseUrl(c)) + "/api/user/" + userId + "/profile";
    }

    public static String appVersionsUrl(Context c, int appId) {
        return String.valueOf(baseUrl(c)) + "/api/app/" + appId + "/versions";
    }

    public static String downloadUrl(Context c, int appId, String version, int userId) {
        String url;
        if (version != null && version.length() > 0) {
            String enc = version;
            try {
                enc = URLEncoder.encode(version, "UTF-8");
            } catch (Exception e) {
            }
            url = String.valueOf(baseUrl(c)) + "/api/download/" + appId + "/" + enc;
        } else {
            url = String.valueOf(baseUrl(c)) + "/api/download/" + appId;
        }
        return userId > 0 ? String.valueOf(url) + "?user_id=" + userId : url;
    }

    public static String appReviewsUrl(Context c, int appId, int viewerId) {
        String url = String.valueOf(baseUrl(c)) + "/api/app/" + appId + "/reviews";
        return viewerId > 0 ? String.valueOf(url) + "?viewer_id=" + viewerId : url;
    }

    public static String reviewReactionUrl(Context c, int reviewId) {
        return String.valueOf(baseUrl(c)) + "/api/review/" + reviewId + "/reaction";
    }

    public static String reviewCommentsUrl(Context c, int reviewId) {
        return String.valueOf(baseUrl(c)) + "/api/review/" + reviewId + "/comments";
    }

    public static String reviewAddCommentUrl(Context c, int reviewId) {
        return String.valueOf(baseUrl(c)) + "/api/review/" + reviewId + "/comment";
    }

    public static String reviewReportUrl(Context c, int reviewId) {
        return String.valueOf(baseUrl(c)) + "/api/review/" + reviewId + "/report";
    }

    public static String logoUrl(Context c) {
        return String.valueOf(baseUrl(c)) + "/logo.png";
    }

    public static String clientLatestUrl(Context c) {
        return String.valueOf(baseUrl(c)) + "/api/client/latest";
    }

    public static String clientAnalyticsUrl(Context c) {
        return String.valueOf(baseUrl(c)) + "/api/client/analytics";
    }
}
