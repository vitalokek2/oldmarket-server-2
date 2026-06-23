package com.oldmarket.model;

/* JADX INFO: loaded from: classes.dex */
public class AppItem {
    public int api;
    public String categoryCode;
    public String categoryLabel;
    public String description;
    public String developer;
    public int downloads;
    public String icon;
    public int id;
    public int installedVersionCode;
    public boolean isGame;
    public String name;
    public String packageName;
    public float rating;
    public String version;
    public int versionCode;

    public static String safe(String s) {
        return s == null ? "" : s;
    }
}
