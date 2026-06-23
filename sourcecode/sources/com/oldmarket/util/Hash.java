package com.oldmarket.util;

import java.security.MessageDigest;

/* JADX INFO: loaded from: classes.dex */
public class Hash {
    public static String md5(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            md.update(s.getBytes("UTF-8"));
            byte[] b = md.digest();
            StringBuilder sb = new StringBuilder();
            for (byte b2 : b) {
                String h = Integer.toHexString(b2 & 255);
                if (h.length() == 1) {
                    sb.append('0');
                }
                sb.append(h);
            }
            return sb.toString();
        } catch (Exception e) {
            return String.valueOf(s.hashCode());
        }
    }
}
