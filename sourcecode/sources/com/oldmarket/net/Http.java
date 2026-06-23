package com.oldmarket.net;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.HashMap;
import java.util.Map;

/* JADX INFO: loaded from: classes.dex */
public class Http {
    private static final long CACHE_TTL_MS = 30000;
    private static final Map<String, CacheEntry> GET_CACHE = new HashMap();

    private static class CacheEntry {
        byte[] data;
        long time;

        private CacheEntry() {
        }

        /* synthetic */ CacheEntry(CacheEntry cacheEntry) {
            this();
        }
    }

    public static String getString(String url) throws Exception {
        byte[] b = getBytes(url);
        if (b == null) {
            return null;
        }
        return new String(b, "UTF-8");
    }

    public static byte[] getBytes(String urlStr) throws Exception {
        byte[] out = null;
        synchronized (GET_CACHE) {
            CacheEntry ce = GET_CACHE.get(urlStr);
            if (ce == null || ce.data == null || System.currentTimeMillis() - ce.time >= CACHE_TTL_MS) {
                HttpURLConnection conn = null;
                InputStream in = null;
                try {
                    URL url = new URL(urlStr);
                    conn = (HttpURLConnection) url.openConnection();
                    conn.setConnectTimeout(12000);
                    conn.setReadTimeout(30000);
                    conn.setUseCaches(false);
                    conn.connect();
                    int code = conn.getResponseCode();
                    in = (code < 200 || code >= 300) ? conn.getErrorStream() : conn.getInputStream();
                    if (in == null) {
                        if (in != null) {
                            try {
                                in.close();
                            } catch (Exception e) {
                            }
                        }
                        if (conn != null) {
                            try {
                                conn.disconnect();
                            } catch (Exception e2) {
                            }
                        }
                    } else {
                        ByteArrayOutputStream bos = new ByteArrayOutputStream();
                        byte[] buf = new byte[8192];
                        while (true) {
                            int r = in.read(buf);
                            if (r == -1) {
                                break;
                            }
                            bos.write(buf, 0, r);
                        }
                        out = bos.toByteArray();
                        if (out != null && out.length < 1048576) {
                            CacheEntry ce2 = new CacheEntry(null);
                            ce2.data = out;
                            ce2.time = System.currentTimeMillis();
                            synchronized (GET_CACHE) {
                                GET_CACHE.put(urlStr, ce2);
                            }
                        }
                        if (in != null) {
                            try {
                                in.close();
                            } catch (Exception e3) {
                            }
                        }
                        if (conn != null) {
                            try {
                                conn.disconnect();
                            } catch (Exception e4) {
                            }
                        }
                    }
                } catch (Throwable th) {
                    if (in != null) {
                        try {
                            in.close();
                        } catch (Exception e5) {
                        }
                    }
                    if (conn == null) {
                        throw th;
                    }
                    try {
                        conn.disconnect();
                        throw th;
                    } catch (Exception e6) {
                        throw th;
                    }
                }
            } else {
                out = ce.data;
            }
        }
        return out;
    }

    public static String postForm(String urlStr, String[][] fields) throws Exception {
        HttpURLConnection conn = null;
        OutputStream out = null;
        InputStream in = null;
        String body = buildForm(fields);
        byte[] bodyBytes = body.getBytes("UTF-8");
        try {
            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(12000);
            conn.setReadTimeout(30000);
            conn.setUseCaches(false);
            conn.setDoOutput(true);
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
            conn.setRequestProperty("Content-Length", String.valueOf(bodyBytes.length));
            out = conn.getOutputStream();
            out.write(bodyBytes);
            out.flush();
            int code = conn.getResponseCode();
            in = (code < 200 || code >= 300) ? conn.getErrorStream() : conn.getInputStream();
            if (in == null) {
                if (out != null) {
                    try {
                        out.close();
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
                return null;
            }
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            while (true) {
                int r = in.read(buf);
                if (r == -1) {
                    break;
                }
                bos.write(buf, 0, r);
            }
            String str = new String(bos.toByteArray(), "UTF-8");
            if (out != null) {
                try {
                    out.close();
                } catch (Exception e4) {
                }
            }
            if (in != null) {
                try {
                    in.close();
                } catch (Exception e5) {
                }
            }
            if (conn == null) {
                return str;
            }
            try {
                conn.disconnect();
                return str;
            } catch (Exception e6) {
                return str;
            }
        } catch (Throwable th) {
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
            if (conn == null) {
                throw th;
            }
            try {
                conn.disconnect();
                throw th;
            } catch (Exception e9) {
                throw th;
            }
        }
    }

    private static String buildForm(String[][] fields) throws Exception {
        if (fields == null || fields.length == 0) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < fields.length; i++) {
            if (i > 0) {
                sb.append("&");
            }
            String k = fields[i][0];
            String v = fields[i][1];
            if (k == null) {
                k = "";
            }
            if (v == null) {
                v = "";
            }
            sb.append(URLEncoder.encode(k, "UTF-8"));
            sb.append("=");
            sb.append(URLEncoder.encode(v, "UTF-8"));
        }
        return sb.toString();
    }

    public static String postJson(String urlStr, String json) throws Exception {
        return sendJson("POST", urlStr, json);
    }

    public static String putJson(String urlStr, String json) throws Exception {
        return sendJson("PUT", urlStr, json);
    }

    private static String sendJson(String method, String urlStr, String json) throws Exception {
        HttpURLConnection conn = null;
        OutputStream out = null;
        InputStream in = null;
        if (json == null) {
            json = "";
        }
        byte[] body = json.getBytes("UTF-8");
        try {
            URL url = new URL(urlStr);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(12000);
            conn.setReadTimeout(30000);
            conn.setUseCaches(false);
            conn.setDoOutput(true);
            conn.setRequestMethod(method);
            conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            conn.setRequestProperty("Content-Length", String.valueOf(body.length));
            out = conn.getOutputStream();
            out.write(body);
            out.flush();
            int code = conn.getResponseCode();
            in = (code < 200 || code >= 300) ? conn.getErrorStream() : conn.getInputStream();
            if (in == null) {
                if (out != null) {
                    try {
                        out.close();
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
                return null;
            }
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            while (true) {
                int r = in.read(buf);
                if (r == -1) {
                    break;
                }
                bos.write(buf, 0, r);
            }
            String str = new String(bos.toByteArray(), "UTF-8");
            if (out != null) {
                try {
                    out.close();
                } catch (Exception e4) {
                }
            }
            if (in != null) {
                try {
                    in.close();
                } catch (Exception e5) {
                }
            }
            if (conn == null) {
                return str;
            }
            try {
                conn.disconnect();
                return str;
            } catch (Exception e6) {
                return str;
            }
        } catch (Throwable th) {
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
            if (conn == null) {
                throw th;
            }
            try {
                conn.disconnect();
                throw th;
            } catch (Exception e9) {
                throw th;
            }
        }
    }
}
