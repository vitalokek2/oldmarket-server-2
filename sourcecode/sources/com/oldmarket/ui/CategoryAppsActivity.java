package com.oldmarket.ui;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Typeface;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.view.LayoutInflater;
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
import com.oldmarket.util.ImageLoader;
import com.oldmarket.util.LocaleHelper;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Random;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class CategoryAppsActivity extends Activity {
    private AppListAdapter adapter;
    private Button btnTopDownloads;
    private Button btnTopFree;
    private ListView list;
    private View loadingOverlay;
    private AppItem promoApp;
    private ImageView promoIcon;
    private View promoRoot;
    private TextView promoText;
    private TextView subtitleView;
    private TextView titleView;
    private ArrayList<AppItem> items = new ArrayList<>();
    private ArrayList<AppItem> originalItems = new ArrayList<>();
    private boolean sortDownloads = false;

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_category_apps);
        String title = getIntent().getStringExtra("title");
        String category = getIntent().getStringExtra("category");
        boolean isGame = getIntent().getBooleanExtra("is_game", false);
        this.titleView = (TextView) findViewById(R.id.txtTitle);
        this.subtitleView = (TextView) findViewById(R.id.txtSubtitle);
        this.list = (ListView) findViewById(R.id.list);
        this.loadingOverlay = findViewById(R.id.loadingOverlay);
        this.btnTopFree = (Button) findViewById(R.id.btnTopFree);
        this.btnTopDownloads = (Button) findViewById(R.id.btnTopDownloads);
        if (this.list == null) {
            Toast.makeText(this, "list not found", 1).show();
            finish();
            return;
        }
        View promoHeader = LayoutInflater.from(this).inflate(R.layout.view_promotion_app, (ViewGroup) this.list, false);
        this.promoRoot = promoHeader.findViewById(R.id.promoRoot);
        this.promoIcon = (ImageView) promoHeader.findViewById(R.id.promoIcon);
        this.promoText = (TextView) promoHeader.findViewById(R.id.promoText);
        this.list.addHeaderView(promoHeader, null, false);
        try {
            ImageButton btnHome = (ImageButton) findViewById(R.id.btnHome);
            if (btnHome != null) {
                btnHome.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryAppsActivity.1
                    @Override // android.view.View.OnClickListener
                    public void onClick(View v) {
                        Intent i = new Intent(CategoryAppsActivity.this, (Class<?>) MainActivity.class);
                        i.addFlags(67108864);
                        CategoryAppsActivity.this.startActivity(i);
                        CategoryAppsActivity.this.finish();
                    }
                });
            }
            ((ImageButton) findViewById(R.id.btnSearch)).setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryAppsActivity.2
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    CategoryAppsActivity.this.startActivity(new Intent(CategoryAppsActivity.this, (Class<?>) SearchActivity.class));
                }
            });
            Typeface tf = Typeface.createFromAsset(getAssets(), "fonts/storopia.ttf");
            if (this.titleView != null) {
                this.titleView.setTypeface(tf);
            }
        } catch (Exception e) {
        }
        if (this.titleView != null) {
            this.titleView.setText(getString(isGame ? R.string.games1 : R.string.apps1));
        }
        if (this.subtitleView != null) {
            TextView textView = this.subtitleView;
            if (title == null || title.length() == 0) {
                title = getString(isGame ? R.string.all_games : R.string.all_apps);
            }
            textView.setText(title);
        }
        this.adapter = new AppListAdapter(this, this.items);
        this.list.setAdapter((ListAdapter) this.adapter);
        this.list.setOnItemClickListener(new AdapterView.OnItemClickListener() { // from class: com.oldmarket.ui.CategoryAppsActivity.3
            @Override // android.widget.AdapterView.OnItemClickListener
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                int idx = position - CategoryAppsActivity.this.list.getHeaderViewsCount();
                if (idx >= 0 && idx < CategoryAppsActivity.this.items.size()) {
                    AppItem it = (AppItem) CategoryAppsActivity.this.items.get(idx);
                    Intent i = new Intent(CategoryAppsActivity.this, (Class<?>) AppDetailActivity.class);
                    i.putExtra("app_id", it.id);
                    CategoryAppsActivity.this.startActivity(i);
                }
            }
        });
        if (this.btnTopFree != null) {
            this.btnTopFree.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryAppsActivity.4
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    CategoryAppsActivity.this.sortDownloads = false;
                    CategoryAppsActivity.this.applySort();
                    CategoryAppsActivity.this.updateTabButtons();
                }
            });
        }
        if (this.btnTopDownloads != null) {
            this.btnTopDownloads.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryAppsActivity.5
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    CategoryAppsActivity.this.sortDownloads = true;
                    CategoryAppsActivity.this.applySort();
                    CategoryAppsActivity.this.updateTabButtons();
                }
            });
        }
        if (this.promoRoot != null) {
            this.promoRoot.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryAppsActivity.6
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    if (CategoryAppsActivity.this.promoApp != null) {
                        Intent i = new Intent(CategoryAppsActivity.this, (Class<?>) AppDetailActivity.class);
                        i.putExtra("app_id", CategoryAppsActivity.this.promoApp.id);
                        CategoryAppsActivity.this.startActivity(i);
                    }
                }
            });
        }
        updateTabButtons();
        loadApps(category, isGame);
    }

    @Override // android.app.Activity
    protected void onResume() {
        super.onResume();
        if (this.adapter != null) {
            this.adapter.refreshInstalledPackages();
            this.adapter.notifyDataSetChanged();
        }
    }

    /* JADX WARN: Type inference failed for: r0v1, types: [com.oldmarket.ui.CategoryAppsActivity$7] */
    private void loadApps(final String category, final boolean isGame) {
        showLoading(true);
        new AsyncTask<Void, Void, ArrayList<AppItem>>() { // from class: com.oldmarket.ui.CategoryAppsActivity.7
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public ArrayList<AppItem> doInBackground(Void... v) {
                try {
                    String url = String.valueOf(Api.baseUrl(CategoryAppsActivity.this)) + "/api/apps?is_game=" + (isGame ? "1" : "0");
                    if (category != null && category.length() > 0) {
                        url = String.valueOf(url) + "&category=" + URLEncoder.encode(category, "UTF-8");
                    }
                    String s = Http.getString(url);
                    if (s == null) {
                        return null;
                    }
                    JSONArray arr = new JSONArray(s);
                    ArrayList<AppItem> out = new ArrayList<>();
                    int deviceApi = Build.VERSION.SDK_INT;
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject o = arr.getJSONObject(i);
                        AppItem a = new AppItem();
                        a.id = o.optInt("id", 0);
                        a.name = o.optString("name", "");
                        a.developer = o.optString("developer", o.optString("author", ""));
                        a.icon = o.optString("icon", "");
                        a.api = o.optInt("api", 1);
                        a.packageName = o.optString("package", o.optString("package_name", ""));
                        a.isGame = o.optBoolean("is_game", false);
                        a.categoryCode = o.optString("category_code", o.optString("category", ""));
                        a.categoryLabel = o.optString("category_label", a.categoryCode);
                        a.rating = (float) o.optDouble("rating", 0.0d);
                        a.downloads = o.optInt("downloads", 0);
                        a.description = o.optString("description", "");
                        if (a.api <= deviceApi) {
                            out.add(a);
                        }
                    }
                    return out;
                } catch (Exception e) {
                    return null;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(ArrayList<AppItem> out) {
                CategoryAppsActivity.this.showLoading(false);
                if (out != null) {
                    CategoryAppsActivity.this.originalItems.clear();
                    CategoryAppsActivity.this.originalItems.addAll(out);
                    CategoryAppsActivity.this.bindPromotion();
                    CategoryAppsActivity.this.applySort();
                    CategoryAppsActivity.this.updateTabButtons();
                    return;
                }
                Toast.makeText(CategoryAppsActivity.this, R.string.error_network, 0).show();
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void applySort() {
        this.items.clear();
        this.items.addAll(this.originalItems);
        if (this.sortDownloads) {
            Collections.sort(this.items, new Comparator<AppItem>() { // from class: com.oldmarket.ui.CategoryAppsActivity.8
                @Override // java.util.Comparator
                public int compare(AppItem a, AppItem b) {
                    return b.downloads - a.downloads;
                }
            });
        } else {
            Collections.sort(this.items, new Comparator<AppItem>() { // from class: com.oldmarket.ui.CategoryAppsActivity.9
                @Override // java.util.Comparator
                public int compare(AppItem a, AppItem b) {
                    int r = Float.compare(b.rating, a.rating);
                    return r != 0 ? r : AppItem.safe(a.name).compareToIgnoreCase(AppItem.safe(b.name));
                }
            });
        }
        this.adapter.refreshInstalledPackages();
        this.adapter.notifyDataSetChanged();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void bindPromotion() {
        if (this.promoRoot != null && this.promoIcon != null && this.promoText != null) {
            if (this.originalItems.isEmpty()) {
                this.promoRoot.setVisibility(8);
                return;
            }
            this.promoRoot.setVisibility(0);
            this.promoApp = this.originalItems.get(new Random().nextInt(this.originalItems.size()));
            ImageLoader.load(this, Api.iconUrl(this, this.promoApp.icon), this.promoIcon, R.drawable.icon_placeholder);
            String text = this.promoApp.description == null ? this.promoApp.name : this.promoApp.description;
            if (text.length() == 0) {
                text = this.promoApp.name;
            }
            if (text.length() > 90) {
                text = String.valueOf(text.substring(0, 90)) + "...";
            }
            this.promoText.setText(text);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void updateTabButtons() {
        int i = R.drawable.btn_strip_mark_on;
        if (this.btnTopFree != null) {
            this.btnTopFree.setCompoundDrawablePadding(6);
            this.btnTopFree.setCompoundDrawablesWithIntrinsicBounds(this.sortDownloads ? R.drawable.btn_strip_mark_off : R.drawable.btn_strip_mark_on, 0, 0, 0);
        }
        if (this.btnTopDownloads != null) {
            this.btnTopDownloads.setCompoundDrawablePadding(6);
            Button button = this.btnTopDownloads;
            if (!this.sortDownloads) {
                i = R.drawable.btn_strip_mark_off;
            }
            button.setCompoundDrawablesWithIntrinsicBounds(i, 0, 0, 0);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showLoading(boolean show) {
        if (this.loadingOverlay != null) {
            this.loadingOverlay.setVisibility(show ? 0 : 8);
        }
    }
}
