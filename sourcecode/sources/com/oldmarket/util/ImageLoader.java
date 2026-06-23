package com.oldmarket.util;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.AsyncTask;
import android.widget.ImageView;
import com.oldmarket.net.Http;
import java.io.File;
import java.io.FileOutputStream;
import java.util.LinkedHashMap;
import java.util.Map;

/* JADX INFO: loaded from: classes.dex */
public class ImageLoader {
    private static final int MAX_MEM_ITEMS = 40;
    private static final LinkedHashMap<String, Bitmap> mem = new LinkedHashMap<String, Bitmap>(MAX_MEM_ITEMS, 0.75f, true) { // from class: com.oldmarket.util.ImageLoader.1
        @Override // java.util.LinkedHashMap
        protected boolean removeEldestEntry(Map.Entry<String, Bitmap> eldest) {
            return size() > ImageLoader.MAX_MEM_ITEMS;
        }
    };

    private static File iconCacheDir(Context c) {
        File d = new File(c.getCacheDir(), "icons");
        if (!d.exists()) {
            d.mkdirs();
        }
        return d;
    }

    private static Bitmap memGet(String k) {
        Bitmap bitmap;
        synchronized (mem) {
            bitmap = mem.get(k);
        }
        return bitmap;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static void memPut(String k, Bitmap b) {
        synchronized (mem) {
            mem.put(k, b);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static int calcInSampleSize(BitmapFactory.Options options, int reqWidth, int reqHeight) {
        int height = options.outHeight;
        int width = options.outWidth;
        int inSampleSize = 1;
        if (reqWidth <= 0) {
            reqWidth = 64;
        }
        if (reqHeight <= 0) {
            reqHeight = 64;
        }
        while (true) {
            if (height / inSampleSize <= reqHeight * 2 && width / inSampleSize <= reqWidth * 2) {
                break;
            }
            inSampleSize *= 2;
        }
        if (inSampleSize < 1) {
            return 1;
        }
        return inSampleSize;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public static Bitmap decodeSampled(byte[] data, int reqWidth, int reqHeight) {
        try {
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(data, 0, data.length, bounds);
            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inSampleSize = calcInSampleSize(bounds, reqWidth, reqHeight);
            opts.inPreferredConfig = Bitmap.Config.RGB_565;
            opts.inDither = true;
            return BitmapFactory.decodeByteArray(data, 0, data.length, opts);
        } catch (OutOfMemoryError e) {
            try {
                BitmapFactory.Options opts2 = new BitmapFactory.Options();
                opts2.inSampleSize = 8;
                opts2.inPreferredConfig = Bitmap.Config.RGB_565;
                return BitmapFactory.decodeByteArray(data, 0, data.length, opts2);
            } catch (Throwable th) {
                return null;
            }
        } catch (Throwable th2) {
            return null;
        }
    }

    private static Bitmap decodeSampledFile(String path, int reqWidth, int reqHeight) {
        try {
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeFile(path, bounds);
            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inSampleSize = calcInSampleSize(bounds, reqWidth, reqHeight);
            opts.inPreferredConfig = Bitmap.Config.RGB_565;
            opts.inDither = true;
            return BitmapFactory.decodeFile(path, opts);
        } catch (OutOfMemoryError e) {
            try {
                BitmapFactory.Options opts2 = new BitmapFactory.Options();
                opts2.inSampleSize = 8;
                opts2.inPreferredConfig = Bitmap.Config.RGB_565;
                return BitmapFactory.decodeFile(path, opts2);
            } catch (Throwable th) {
                return null;
            }
        } catch (Throwable th2) {
            return null;
        }
    }

    /* JADX WARN: Type inference failed for: r0v3, types: [com.oldmarket.util.ImageLoader$2] */
    public static void load(Context c, final String url, final ImageView iv, final int placeholderRes) {
        Bitmap fb;
        iv.setImageResource(placeholderRes);
        iv.setTag(url);
        if (url != null && url.length() != 0) {
            Bitmap cached = memGet(url);
            if (cached != null) {
                Object tag = iv.getTag();
                if (tag != null && url.equals(tag.toString())) {
                    iv.setImageBitmap(cached);
                    return;
                }
                return;
            }
            final int reqW = (iv.getLayoutParams() == null || iv.getLayoutParams().width <= 0) ? 96 : iv.getLayoutParams().width;
            final int reqH = (iv.getLayoutParams() == null || iv.getLayoutParams().height <= 0) ? 96 : iv.getLayoutParams().height;
            String key = Hash.md5(url);
            final File f = new File(iconCacheDir(c), String.valueOf(key) + ".img");
            if (f.exists() && (fb = decodeSampledFile(f.getAbsolutePath(), reqW, reqH)) != null) {
                memPut(url, fb);
                Object tag2 = iv.getTag();
                if (tag2 != null && url.equals(tag2.toString())) {
                    iv.setImageBitmap(fb);
                    return;
                }
                return;
            }
            new AsyncTask<Void, Void, Bitmap>() { // from class: com.oldmarket.util.ImageLoader.2
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public Bitmap doInBackground(Void... v) {
                    try {
                        try {
                            byte[] data = Http.getBytes(url);
                            if (data == null) {
                                return null;
                            }
                            Bitmap bmp = ImageLoader.decodeSampled(data, reqW, reqH);
                            if (bmp == null) {
                                return null;
                            }
                            try {
                                FileOutputStream fos = new FileOutputStream(f);
                                fos.write(data);
                                fos.close();
                                return bmp;
                            } catch (Throwable th) {
                                return bmp;
                            }
                        } catch (OutOfMemoryError e) {
                            return null;
                        }
                    } catch (Throwable th2) {
                        return null;
                    }
                }

                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public void onPostExecute(Bitmap bmp) {
                    if (bmp != null) {
                        ImageLoader.memPut(url, bmp);
                        Object tag3 = iv.getTag();
                        if (tag3 != null && url.equals(tag3.toString())) {
                            try {
                                iv.setImageBitmap(bmp);
                                return;
                            } catch (Throwable th) {
                                iv.setImageResource(placeholderRes);
                                return;
                            }
                        }
                        return;
                    }
                    Object tag4 = iv.getTag();
                    if (tag4 != null && url.equals(tag4.toString())) {
                        iv.setImageResource(placeholderRes);
                    }
                }
            }.execute(new Void[0]);
        }
    }

    /* JADX WARN: Type inference failed for: r4v4, types: [com.oldmarket.util.ImageLoader$3] */
    public static void loadBanner(Context c, final String url, final ImageView iv, final int placeholderRes) {
        iv.setImageResource(placeholderRes);
        iv.setTag(url);
        if (url != null && url.length() != 0) {
            Bitmap cached = memGet("banner:" + url);
            if (cached != null) {
                Object tag = iv.getTag();
                if (tag != null && url.equals(tag.toString())) {
                    iv.setImageBitmap(cached);
                    return;
                }
                return;
            }
            new AsyncTask<Void, Void, Bitmap>() { // from class: com.oldmarket.util.ImageLoader.3
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public Bitmap doInBackground(Void... v) {
                    try {
                        byte[] data = Http.getBytes(url);
                        if (data == null) {
                            return null;
                        }
                        BitmapFactory.Options bounds = new BitmapFactory.Options();
                        bounds.inJustDecodeBounds = true;
                        BitmapFactory.decodeByteArray(data, 0, data.length, bounds);
                        BitmapFactory.Options opts = new BitmapFactory.Options();
                        opts.inSampleSize = ImageLoader.calcInSampleSize(bounds, 1024, 400);
                        opts.inPreferredConfig = Bitmap.Config.RGB_565;
                        opts.inDither = true;
                        return BitmapFactory.decodeByteArray(data, 0, data.length, opts);
                    } catch (Throwable th) {
                        return null;
                    }
                }

                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public void onPostExecute(Bitmap bmp) {
                    if (bmp != null) {
                        ImageLoader.memPut("banner:" + url, bmp);
                        Object tag2 = iv.getTag();
                        if (tag2 != null && url.equals(tag2.toString())) {
                            iv.setImageBitmap(bmp);
                            return;
                        }
                        return;
                    }
                    iv.setImageResource(placeholderRes);
                }
            }.execute(new Void[0]);
        }
    }
}
