package com.oldmarket.ui;

import android.app.Activity;
import android.app.AlarmManager;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;
import com.oldmarket.R;
import com.oldmarket.model.AppItem;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.service.UpdateCheckService;
import com.oldmarket.util.ImageLoader;
import com.oldmarket.util.LocaleHelper;
import com.oldmarket.util.Prefs;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Locale;
import java.util.Random;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class MainActivity extends Activity {
    private static ArrayList<AppItem> CACHE_ITEMS = new ArrayList<>();
    private static ArrayList<AppItem> CACHE_PROMO_SOURCE = new ArrayList<>();
    private static long CACHE_TIME = 0;
    private AppListAdapter adapter;
    private Button btnApps;
    private Button btnDownloads;
    private Button btnGames;
    private ImageButton btnSearch;
    private PromoCategory currentPromoCategory;
    private ArrayList<AppItem> items = new ArrayList<>();
    private ListView list;
    private View loadingOverlay;
    private ImageButton logo;
    private ImageView promoIcon1;
    private ImageView promoIcon2;
    private ImageView promoIcon3;
    private View promoMainRoot;
    private ImageView promoMirror1;
    private ImageView promoMirror2;
    private ImageView promoMirror3;
    private TextView txtBrowseCategory;
    private TextView txtMarket;
    private TextView txtPromoType;
    private TextView txtSection;

    private static class PromoCategory {
        ArrayList<AppItem> apps;
        String code;
        boolean isGame;
        String label;

        private PromoCategory() {
            this.apps = new ArrayList<>();
        }

        /* synthetic */ PromoCategory(PromoCategory promoCategory) {
            this();
        }
    }

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setRequestedOrientation(4);
        setContentView(R.layout.activity_main);
        this.loadingOverlay = findViewById(R.id.loadingOverlay);
        this.logo = (ImageButton) findViewById(R.id.logo);
        this.list = (ListView) findViewById(R.id.list);
        this.btnApps = (Button) findViewById(R.id.btnApps);
        this.btnGames = (Button) findViewById(R.id.btnGames);
        this.btnDownloads = (Button) findViewById(R.id.btnDownloads);
        this.btnSearch = (ImageButton) findViewById(R.id.btnSearch);
        this.txtMarket = (TextView) findViewById(R.id.txtMarket);
        View header = getLayoutInflater().inflate(R.layout.main_list_header, (ViewGroup) this.list, false);
        this.promoMainRoot = header.findViewById(R.id.promoMainRoot);
        this.promoIcon1 = (ImageView) header.findViewById(R.id.promoIcon1);
        this.promoIcon2 = (ImageView) header.findViewById(R.id.promoIcon2);
        this.promoIcon3 = (ImageView) header.findViewById(R.id.promoIcon3);
        this.promoMirror1 = (ImageView) header.findViewById(R.id.promoMirror1);
        this.promoMirror2 = (ImageView) header.findViewById(R.id.promoMirror2);
        this.promoMirror3 = (ImageView) header.findViewById(R.id.promoMirror3);
        this.txtPromoType = (TextView) header.findViewById(R.id.txtPromoType);
        this.txtBrowseCategory = (TextView) header.findViewById(R.id.txtBrowseCategory);
        this.txtSection = (TextView) header.findViewById(R.id.txtSection);
        this.list.addHeaderView(header, null, false);
        try {
            Typeface tf = Typeface.createFromAsset(getAssets(), "fonts/storopia.ttf");
            this.txtMarket.setTypeface(tf);
            this.txtPromoType.setTypeface(tf);
        } catch (Exception e) {
        }
        this.adapter = new AppListAdapter(this, this.items);
        this.list.setAdapter((ListAdapter) this.adapter);
        this.list.setOnItemClickListener(new AdapterView.OnItemClickListener() { // from class: com.oldmarket.ui.MainActivity.1
            @Override // android.widget.AdapterView.OnItemClickListener
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                int idx = position - MainActivity.this.list.getHeaderViewsCount();
                if (idx >= 0 && idx < MainActivity.this.items.size()) {
                    AppItem it = (AppItem) MainActivity.this.items.get(idx);
                    Intent i = new Intent(MainActivity.this, (Class<?>) AppDetailActivity.class);
                    i.putExtra("app_id", it.id);
                    MainActivity.this.startActivity(i);
                }
            }
        });
        this.btnSearch.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.2
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                MainActivity.this.startActivity(new Intent(MainActivity.this, (Class<?>) SearchActivity.class));
            }
        });
        this.btnApps.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.3
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                MainActivity.this.openCategories(false);
            }
        });
        this.btnGames.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.4
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                MainActivity.this.openCategories(true);
            }
        });
        this.btnDownloads.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.5
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                MainActivity.this.openDownloads();
            }
        });
        this.logo.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.6
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                try {
                    MainActivity.this.openOptionsMenu();
                } catch (Exception e2) {
                }
            }
        });
        this.promoMainRoot.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.7
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                if (MainActivity.this.currentPromoCategory != null) {
                    Intent i = new Intent(MainActivity.this, (Class<?>) CategoryAppsActivity.class);
                    i.putExtra("category", MainActivity.this.currentPromoCategory.code);
                    i.putExtra("title", MainActivity.this.currentPromoCategory.label);
                    i.putExtra("is_game", MainActivity.this.currentPromoCategory.isGame);
                    MainActivity.this.startActivity(i);
                }
            }
        });
        this.txtMarket.setText(isRu() ? "маркет" : "market");
        try {
            int androidLogoRes = getResources().getIdentifier("market_android_logo", "drawable", getPackageName());
            ImageView iw = (ImageView) findViewById(R.id.imgAndroidWord);
            if (iw != null && androidLogoRes != 0) {
                iw.setImageResource(androidLogoRes);
            }
        } catch (Exception e2) {
        }
        if (!restoreFromCache()) {
            loadTopContent();
        }
        checkClientUpdateIfNeeded();
        sendAnalyticsIfNeeded();
        scheduleUpdateChecks();
    }

    private boolean isRu() {
        String lang = Locale.getDefault().getLanguage();
        return lang != null && lang.toLowerCase().startsWith("ru");
    }

    private void scheduleUpdateChecks() {
        try {
            AlarmManager am = (AlarmManager) getSystemService("alarm");
            Intent i = new Intent(this, (Class<?>) UpdateCheckService.class);
            PendingIntent pi = PendingIntent.getService(this, 30001, i, 134217728);
            long first = System.currentTimeMillis() + 15000;
            am.setInexactRepeating(0, first, 300000L, pi);
        } catch (Exception e) {
        }
    }

    @Override // android.app.Activity
    protected void onResume() {
        super.onResume();
        this.adapter.refreshInstalledPackages();
        this.adapter.notifyDataSetChanged();
    }

    @Override // android.app.Activity
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuItem downloads = menu.add(0, 3, 0, getString(R.string.downloads));
        downloads.setIcon(R.drawable.ic_menu_downloads);
        MenuItem profile = menu.add(0, 1, 1, Prefs.isLoggedIn(this) ? getString(R.string.profile) : getString(R.string.login));
        profile.setIcon(R.drawable.ic_menu_account);
        MenuItem settings = menu.add(0, 2, 2, getString(R.string.settings));
        settings.setIcon(R.drawable.ic_menu_settings_custom);
        return true;
    }

    @Override // android.app.Activity
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == 1) {
            startActivity(new Intent(this, (Class<?>) (Prefs.isLoggedIn(this) ? ProfileActivity.class : LoginActivity.class)));
            return true;
        }
        if (item.getItemId() == 2) {
            startActivity(new Intent(this, (Class<?>) SettingsActivity.class));
            return true;
        }
        if (item.getItemId() == 3) {
            openDownloads();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void openCategories(boolean isGame) {
        Intent i = new Intent(this, (Class<?>) CategoryListActivity.class);
        i.putExtra("is_game", isGame);
        startActivity(i);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void openDownloads() {
        startActivity(new Intent(this, (Class<?>) DownloadsActivity.class));
    }

    private boolean restoreFromCache() {
        if (CACHE_ITEMS == null || CACHE_ITEMS.isEmpty() || System.currentTimeMillis() - CACHE_TIME > 120000) {
            return false;
        }
        this.items.clear();
        this.items.addAll(CACHE_ITEMS);
        this.adapter.refreshInstalledPackages();
        this.adapter.notifyDataSetChanged();
        if (CACHE_PROMO_SOURCE != null && !CACHE_PROMO_SOURCE.isEmpty()) {
            bindPromo(CACHE_PROMO_SOURCE);
        }
        showLoading(false);
        return true;
    }

    /* JADX WARN: Type inference failed for: r1v1, types: [com.oldmarket.ui.MainActivity$8] */
    private void loadTopContent() {
        showLoading(true);
        final int deviceApi = Build.VERSION.SDK_INT;
        new AsyncTask<Void, Void, ArrayList<AppItem>>() { // from class: com.oldmarket.ui.MainActivity.8
            ArrayList<AppItem> promoSource = new ArrayList<>();

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public ArrayList<AppItem> doInBackground(Void... v) {
                ArrayList<AppItem> out = new ArrayList<>();
                MainActivity.this.loadEndpoint("/api/top-apps", false, deviceApi, out);
                MainActivity.this.loadEndpoint("/api/top-games", true, deviceApi, out);
                MainActivity.this.loadEndpoint("/api/apps?is_game=0", false, deviceApi, this.promoSource);
                MainActivity.this.loadEndpoint("/api/apps?is_game=1", true, deviceApi, this.promoSource);
                return out;
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(ArrayList<AppItem> out) {
                MainActivity.this.showLoading(false);
                if (out != null) {
                    MainActivity.this.items.clear();
                    MainActivity.this.items.addAll(out);
                    MainActivity.CACHE_ITEMS.clear();
                    MainActivity.CACHE_ITEMS.addAll(out);
                    MainActivity.CACHE_PROMO_SOURCE.clear();
                    MainActivity.CACHE_PROMO_SOURCE.addAll(this.promoSource);
                    MainActivity.CACHE_TIME = System.currentTimeMillis();
                    MainActivity.this.adapter.refreshInstalledPackages();
                    MainActivity.this.adapter.notifyDataSetChanged();
                    MainActivity.this.bindPromo(this.promoSource);
                    return;
                }
                Toast.makeText(MainActivity.this, R.string.error_network, 0).show();
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void loadEndpoint(String endpoint, boolean isGame, int deviceApi, ArrayList<AppItem> out) {
        try {
            String s = Http.getString(String.valueOf(Api.baseUrl(this)) + endpoint);
            if (s != null) {
                JSONArray arr = new JSONArray(s);
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject o = arr.getJSONObject(i);
                    AppItem a = new AppItem();
                    a.id = o.optInt("id", 0);
                    a.name = o.optString("name", "");
                    a.developer = o.optString("developer", o.optString("author", ""));
                    a.icon = o.optString("icon", "");
                    a.api = o.optInt("api", 1);
                    a.packageName = o.optString("package", o.optString("package_name", ""));
                    a.isGame = isGame || o.optBoolean("is_game", false);
                    a.categoryCode = o.optString("category_code", o.optString("category", ""));
                    a.categoryLabel = o.optString("category_label", a.categoryCode);
                    a.rating = (float) o.optDouble("rating", 0.0d);
                    a.downloads = o.optInt("downloads", 0);
                    if (a.api <= deviceApi) {
                        out.add(a);
                    }
                }
            }
        } catch (Exception e) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void bindPromo(ArrayList<AppItem> source) {
        if (source != null && source.size() != 0) {
            HashMap<String, PromoCategory> map = new HashMap<>();
            for (int i = 0; i < source.size(); i++) {
                AppItem a = source.get(i);
                if (a.categoryCode != null && a.categoryCode.length() != 0) {
                    String key = String.valueOf(a.categoryCode) + "|" + a.isGame;
                    PromoCategory pc = map.get(key);
                    if (pc == null) {
                        pc = new PromoCategory(null);
                        pc.code = a.categoryCode;
                        pc.label = a.categoryLabel;
                        pc.isGame = a.isGame;
                        map.put(key, pc);
                    }
                    if (pc.apps.size() < 6) {
                        pc.apps.add(a);
                    }
                }
            }
            if (map.size() != 0) {
                ArrayList<PromoCategory> cats = new ArrayList<>(map.values());
                this.currentPromoCategory = cats.get(new Random().nextInt(cats.size()));
                this.txtPromoType.setText(this.currentPromoCategory.isGame ? getString(R.string.games).toLowerCase() : getString(R.string.apps).toLowerCase());
                this.txtBrowseCategory.setText(String.valueOf(isRu() ? "Обзор " : "Browse ") + this.currentPromoCategory.label);
                bindPromoIcon(this.promoIcon1, this.promoMirror1, this.currentPromoCategory.apps, 0);
                bindPromoIcon(this.promoIcon2, this.promoMirror2, this.currentPromoCategory.apps, 1);
                bindPromoIcon(this.promoIcon3, this.promoMirror3, this.currentPromoCategory.apps, 2);
            }
        }
    }

    private void bindPromoIcon(final ImageView iv, final ImageView mirror, ArrayList<AppItem> apps, int idx) {
        if (apps.size() <= idx) {
            iv.setImageResource(R.drawable.icon_placeholder);
            mirror.setImageResource(R.drawable.icon_placeholder);
        } else {
            AppItem a = apps.get(idx);
            String url = Api.iconUrl(this, a.icon);
            ImageLoader.load(this, url, iv, R.drawable.icon_placeholder);
            iv.postDelayed(new Runnable() { // from class: com.oldmarket.ui.MainActivity.9
                @Override // java.lang.Runnable
                public void run() {
                    MainActivity.this.updateMirrorFromImageView(iv, mirror, 0);
                }
            }, 250L);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void updateMirrorFromImageView(final ImageView source, final ImageView mirror, final int attempt) {
        Bitmap reflected;
        try {
            Drawable d = source.getDrawable();
            if (d == null) {
                if (attempt < 8) {
                    source.postDelayed(new Runnable() { // from class: com.oldmarket.ui.MainActivity.10
                        @Override // java.lang.Runnable
                        public void run() {
                            MainActivity.this.updateMirrorFromImageView(source, mirror, attempt + 1);
                        }
                    }, 200L);
                }
            } else {
                Bitmap original = drawableToBitmap(d, source.getWidth() > 0 ? source.getWidth() : 44, source.getHeight() > 0 ? source.getHeight() : 44);
                if (original == null || (reflected = createReflectionBitmap(original)) == null) {
                    return;
                }
                mirror.setImageBitmap(reflected);
            }
        } catch (Throwable th) {
        }
    }

    private Bitmap drawableToBitmap(Drawable drawable, int reqW, int reqH) {
        Bitmap b;
        try {
            if (!(drawable instanceof BitmapDrawable) || (b = ((BitmapDrawable) drawable).getBitmap()) == null) {
                int w = reqW > 0 ? reqW : 44;
                int h = reqH > 0 ? reqH : 44;
                Bitmap bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(bitmap);
                drawable.setBounds(0, 0, w, h);
                drawable.draw(canvas);
                return bitmap;
            }
            return b;
        } catch (Throwable th) {
            return null;
        }
    }

    private Bitmap createReflectionBitmap(Bitmap original) {
        try {
            int width = original.getWidth();
            int height = original.getHeight();
            if (width <= 0 || height <= 1) {
                return null;
            }
            int reflectionHeight = Math.max(8, height / 2);
            Matrix matrix = new Matrix();
            matrix.preScale(1.0f, -1.0f);
            Bitmap reflection = Bitmap.createBitmap(original, 0, height - reflectionHeight, width, reflectionHeight, matrix, false);
            Bitmap bitmapWithReflection = Bitmap.createBitmap(width, reflectionHeight, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(bitmapWithReflection);
            canvas.drawBitmap(reflection, 0.0f, 0.0f, (Paint) null);
            Paint paint = new Paint();
            LinearGradient shader = new LinearGradient(0.0f, 0.0f, 0.0f, reflectionHeight, 1728053247, 16777215, Shader.TileMode.CLAMP);
            paint.setShader(shader);
            paint.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.DST_IN));
            canvas.drawRect(0.0f, 0.0f, width, reflectionHeight, paint);
            return bitmapWithReflection;
        } catch (Throwable th) {
            return null;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showLoading(boolean show) {
        if (this.loadingOverlay != null) {
            this.loadingOverlay.setVisibility(show ? 0 : 8);
        }
    }

    /* JADX WARN: Type inference failed for: r1v0, types: [com.oldmarket.ui.MainActivity$11] */
    private void checkClientUpdateIfNeeded() {
        final boolean ru = isRu();
        new AsyncTask<Void, Void, JSONObject>() { // from class: com.oldmarket.ui.MainActivity.11
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public JSONObject doInBackground(Void... params) {
                try {
                    String s = Http.getString(Api.clientLatestUrl(MainActivity.this));
                    if (s == null || s.length() == 0) {
                        return null;
                    }
                    return new JSONObject(s);
                } catch (Exception e) {
                    return null;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(JSONObject o) {
                if (o != null) {
                    try {
                        int latestCode = o.optInt("version_code", 0);
                        String latestName = o.optString("version_name", "");
                        final String updateUrl = o.optString("update_url", "");
                        String notes = ru ? o.optString("notes_ru", "") : o.optString("notes_en", "");
                        PackageInfo pi = MainActivity.this.getPackageManager().getPackageInfo(MainActivity.this.getPackageName(), 0);
                        if (latestCode > pi.versionCode && updateUrl != null && updateUrl.length() > 0) {
                            StringBuilder msg = new StringBuilder(MainActivity.this.getString(R.string.client_update_message));
                            if (latestName != null && latestName.length() > 0) {
                                msg.append("\\n\\n").append(ru ? "Версия: " : "Version: ").append(latestName);
                            }
                            if (notes != null && notes.length() > 0) {
                                msg.append("\\n\\n").append(MainActivity.this.getString(R.string.client_update_note_prefix)).append(notes);
                            }
                            new AlertDialog.Builder(MainActivity.this).setTitle(MainActivity.this.getString(R.string.client_update_title)).setMessage(msg.toString()).setPositiveButton(MainActivity.this.getString(R.string.update_now), new DialogInterface.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.11.1
                                @Override // android.content.DialogInterface.OnClickListener
                                public void onClick(DialogInterface dialog, int which) {
                                    try {
                                        MainActivity.this.startActivity(new Intent("android.intent.action.VIEW", Uri.parse(updateUrl)));
                                    } catch (Exception e) {
                                    }
                                }
                            }).setNegativeButton(MainActivity.this.getString(R.string.later), (DialogInterface.OnClickListener) null).show();
                        }
                    } catch (Exception e) {
                    }
                }
            }
        }.execute(new Void[0]);
    }

    /* JADX WARN: Type inference failed for: r2v3, types: [com.oldmarket.ui.MainActivity$12] */
    private void sendAnalyticsIfNeeded() {
        long now = System.currentTimeMillis();
        if (now - Prefs.getLastAnalyticsSentAt(this) >= 43200000) {
            Prefs.setLastAnalyticsSentAt(this, now);
            new AsyncTask<Void, Void, Void>() { // from class: com.oldmarket.ui.MainActivity.12
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public Void doInBackground(Void... params) {
                    try {
                        PackageInfo pi = MainActivity.this.getPackageManager().getPackageInfo(MainActivity.this.getPackageName(), 0);
                        JSONObject o = new JSONObject();
                        o.put("api_level", Build.VERSION.SDK_INT);
                        o.put("app_version_code", pi.versionCode);
                        o.put("app_version_name", pi.versionName == null ? "" : pi.versionName);
                        o.put("device_model", Build.MODEL == null ? "" : Build.MODEL);
                        o.put("manufacturer", Build.MANUFACTURER == null ? "" : Build.MANUFACTURER);
                        o.put("lang", Locale.getDefault().getLanguage());
                        Http.postJson(Api.clientAnalyticsUrl(MainActivity.this), o.toString());
                        return null;
                    } catch (Exception e) {
                        return null;
                    }
                }
            }.execute(new Void[0]);
        }
    }

    private void showApi25WarningIfNeeded() {
        if (Build.VERSION.SDK_INT == 25) {
            new AlertDialog.Builder(this).setTitle("Warning").setMessage("OldMarket can work badly on newer devices.").setPositiveButton("OK", new DialogInterface.OnClickListener() { // from class: com.oldmarket.ui.MainActivity.13
                @Override // android.content.DialogInterface.OnClickListener
                public void onClick(DialogInterface dialog, int which) {
                }
            }).show();
        }
    }
}
