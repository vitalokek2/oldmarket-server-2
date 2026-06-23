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
import android.widget.ArrayAdapter;
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
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Random;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class CategoryListActivity extends Activity {
    private ArrayAdapter<CategoryItem> adapter;
    private boolean isGame;
    private ListView list;
    private View loadingOverlay;
    private AppItem promoApp;
    private View promoHeader;
    private ImageView promoIcon;
    private View promoRoot;
    private TextView promoText;
    private TextView titleView;
    private ArrayList<CategoryItem> items = new ArrayList<>();
    private ArrayList<AppItem> allApps = new ArrayList<>();

    private static class CategoryItem {
        public final String code;
        public final String label;
        public String preview = "";

        public CategoryItem(String code, String label) {
            this.code = code;
            this.label = label;
        }

        public String toString() {
            return this.label;
        }
    }

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_category_list);
        this.isGame = getIntent().getBooleanExtra("is_game", false);
        this.titleView = (TextView) findViewById(R.id.txtTitle);
        this.list = (ListView) findViewById(R.id.list);
        this.loadingOverlay = findViewById(R.id.loadingOverlay);
        ImageButton btnHome = (ImageButton) findViewById(R.id.btnHome);
        ImageButton btnSearch = (ImageButton) findViewById(R.id.btnSearch);
        if (btnHome != null) {
            btnHome.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryListActivity.1
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    Intent i = new Intent(CategoryListActivity.this, (Class<?>) MainActivity.class);
                    i.addFlags(67108864);
                    CategoryListActivity.this.startActivity(i);
                    CategoryListActivity.this.finish();
                }
            });
        }
        if (btnSearch != null) {
            btnSearch.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryListActivity.2
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    CategoryListActivity.this.startActivity(new Intent(CategoryListActivity.this, (Class<?>) SearchActivity.class));
                }
            });
        }
        if (this.titleView != null) {
            this.titleView.setText(getString(this.isGame ? R.string.games1 : R.string.apps1));
            try {
                Typeface tf = Typeface.createFromAsset(getAssets(), "fonts/storopia.ttf");
                this.titleView.setTypeface(tf);
            } catch (Exception e) {
            }
        }
        LayoutInflater inf = LayoutInflater.from(this);
        this.promoHeader = inf.inflate(R.layout.view_promotion_app, (ViewGroup) this.list, false);
        this.promoRoot = this.promoHeader.findViewById(R.id.promoRoot);
        this.promoIcon = (ImageView) this.promoHeader.findViewById(R.id.promoIcon);
        this.promoText = (TextView) this.promoHeader.findViewById(R.id.promoText);
        if (this.promoRoot != null) {
            this.promoRoot.setVisibility(8);
            this.promoRoot.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.CategoryListActivity.3
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    if (CategoryListActivity.this.promoApp != null) {
                        Intent i = new Intent(CategoryListActivity.this, (Class<?>) AppDetailActivity.class);
                        i.putExtra("app_id", CategoryListActivity.this.promoApp.id);
                        CategoryListActivity.this.startActivity(i);
                    }
                }
            });
        }
        if (this.list != null) {
            this.list.addHeaderView(this.promoHeader, null, false);
        }
        this.adapter = new ArrayAdapter<CategoryItem>(this, R.layout.list_item_category, R.id.text1, this.items) { // from class: com.oldmarket.ui.CategoryListActivity.4
            @Override // android.widget.ArrayAdapter, android.widget.Adapter
            public View getView(int position, View convertView, ViewGroup parent) {
                View v = super.getView(position, convertView, parent);
                TextView tv = (TextView) v.findViewById(R.id.text1);
                TextView tvSub = (TextView) v.findViewById(R.id.text2);
                CategoryItem item = (CategoryItem) CategoryListActivity.this.items.get(position);
                if (tv != null) {
                    tv.setText(item.label);
                    tv.setTypeface(Typeface.DEFAULT_BOLD);
                }
                if (tvSub != null) {
                    tvSub.setText(item.preview == null ? "" : item.preview);
                    tvSub.setVisibility((item.preview == null || item.preview.length() <= 0) ? 8 : 0);
                }
                return v;
            }
        };
        if (this.list != null) {
            this.list.setAdapter((ListAdapter) this.adapter);
            this.list.setOnItemClickListener(new AdapterView.OnItemClickListener() { // from class: com.oldmarket.ui.CategoryListActivity.5
                @Override // android.widget.AdapterView.OnItemClickListener
                public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                    int idx = position - CategoryListActivity.this.list.getHeaderViewsCount();
                    if (idx >= 0 && idx < CategoryListActivity.this.items.size()) {
                        CategoryItem item = (CategoryItem) CategoryListActivity.this.items.get(idx);
                        Intent i = new Intent(CategoryListActivity.this, (Class<?>) CategoryAppsActivity.class);
                        i.putExtra("is_game", CategoryListActivity.this.isGame);
                        i.putExtra("category", item.code);
                        i.putExtra("title", item.label);
                        CategoryListActivity.this.startActivity(i);
                    }
                }
            });
        }
        loadData();
    }

    /* JADX WARN: Type inference failed for: r0v1, types: [com.oldmarket.ui.CategoryListActivity$6] */
    private void loadData() {
        showLoading(true);
        new AsyncTask<Void, Void, Boolean>() { // from class: com.oldmarket.ui.CategoryListActivity.6
            ArrayList<CategoryItem> outCats = new ArrayList<>();
            ArrayList<AppItem> outApps = new ArrayList<>();

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public Boolean doInBackground(Void... params) {
                try {
                    String s = Http.getString(String.valueOf(Api.baseUrl(CategoryListActivity.this)) + "/api/categories?is_game=" + (CategoryListActivity.this.isGame ? "1" : "0"));
                    String appsStr = Http.getString(String.valueOf(Api.baseUrl(CategoryListActivity.this)) + "/api/apps?is_game=" + (CategoryListActivity.this.isGame ? "1" : "0"));
                    if (s == null || appsStr == null) {
                        return false;
                    }
                    JSONArray arr = new JSONArray(s);
                    JSONArray appsArr = new JSONArray(appsStr);
                    this.outCats.add(new CategoryItem("", CategoryListActivity.this.getString(CategoryListActivity.this.isGame ? R.string.all_games : R.string.all_apps)));
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject o = arr.getJSONObject(i);
                        this.outCats.add(new CategoryItem(o.optString("code", ""), o.optString("label", "")));
                    }
                    int deviceApi = Build.VERSION.SDK_INT;
                    for (int i2 = 0; i2 < appsArr.length(); i2++) {
                        JSONObject o2 = appsArr.getJSONObject(i2);
                        AppItem a = new AppItem();
                        a.id = o2.optInt("id", 0);
                        a.name = o2.optString("name", "");
                        a.developer = o2.optString("developer", o2.optString("author", ""));
                        a.icon = o2.optString("icon", "");
                        a.api = o2.optInt("api", 1);
                        a.packageName = o2.optString("package", o2.optString("package_name", ""));
                        a.isGame = o2.optBoolean("is_game", false);
                        a.categoryCode = o2.optString("category_code", o2.optString("category", ""));
                        a.categoryLabel = o2.optString("category_label", a.categoryCode);
                        a.rating = (float) o2.optDouble("rating", 0.0d);
                        a.downloads = o2.optInt("downloads", 0);
                        a.description = o2.optString("description", "");
                        if (a.api <= deviceApi) {
                            this.outApps.add(a);
                        }
                    }
                    HashMap<String, ArrayList<String>> previews = new HashMap<>();
                    for (int i3 = 0; i3 < this.outApps.size(); i3++) {
                        AppItem a2 = this.outApps.get(i3);
                        String key = a2.categoryCode == null ? "" : a2.categoryCode;
                        ArrayList<String> names = previews.get(key);
                        if (names == null) {
                            names = new ArrayList<>();
                            previews.put(key, names);
                        }
                        if (names.size() < 3) {
                            names.add(a2.name);
                        }
                    }
                    ArrayList<String> allNames = new ArrayList<>();
                    for (int i4 = 0; i4 < this.outApps.size() && allNames.size() < 3; i4++) {
                        allNames.add(this.outApps.get(i4).name);
                    }
                    for (int i5 = 0; i5 < this.outCats.size(); i5++) {
                        CategoryItem c = this.outCats.get(i5);
                        ArrayList<String> names2 = c.code.length() == 0 ? allNames : previews.get(c.code);
                        if (names2 != null && names2.size() > 0) {
                            StringBuilder sb = new StringBuilder();
                            for (int j = 0; j < names2.size(); j++) {
                                if (j > 0) {
                                    sb.append(", ");
                                }
                                sb.append(names2.get(j));
                            }
                            c.preview = sb.toString();
                        } else {
                            c.preview = "";
                        }
                    }
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(Boolean ok) {
                CategoryListActivity.this.showLoading(false);
                if (ok.booleanValue()) {
                    CategoryListActivity.this.items.clear();
                    CategoryListActivity.this.items.addAll(this.outCats);
                    CategoryListActivity.this.allApps.clear();
                    CategoryListActivity.this.allApps.addAll(this.outApps);
                    CategoryListActivity.this.adapter.notifyDataSetChanged();
                    CategoryListActivity.this.bindPromotion();
                    return;
                }
                Toast.makeText(CategoryListActivity.this, R.string.error_network, 0).show();
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void bindPromotion() {
        if (this.promoRoot != null && this.promoIcon != null && this.promoText != null) {
            if (this.allApps.isEmpty()) {
                this.promoRoot.setVisibility(8);
                return;
            }
            this.promoRoot.setVisibility(0);
            this.promoApp = this.allApps.get(new Random().nextInt(this.allApps.size()));
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
    public void showLoading(boolean show) {
        if (this.loadingOverlay != null) {
            this.loadingOverlay.setVisibility(show ? 0 : 8);
        }
    }
}
