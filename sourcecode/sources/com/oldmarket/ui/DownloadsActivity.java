package com.oldmarket.ui;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.BaseAdapter;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.ProgressBar;
import android.widget.RatingBar;
import android.widget.TextView;
import android.widget.Toast;
import com.oldmarket.R;
import com.oldmarket.model.AppItem;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.service.DownloadService;
import com.oldmarket.util.ImageLoader;
import com.oldmarket.util.LocaleHelper;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class DownloadsActivity extends Activity {
    private static final int TYPE_APP = 1;
    private static final int TYPE_SECTION = 0;
    private DownloadsAdapter adapter;
    private LinearLayout currentDownloadsContainer;
    private View currentDownloadsHeader;
    private ListView list;
    private View loadingOverlay;
    private TextView titleView;
    private TextView txtCurrentSection;
    private ArrayList<RowItem> rows = new ArrayList<>();
    private final BroadcastReceiver dlReceiver = new BroadcastReceiver() { // from class: com.oldmarket.ui.DownloadsActivity.1
        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            if (!DownloadService.ACTION_PROGRESS.equals(intent.getAction())) {
                return;
            }
            DownloadsActivity.this.refreshCurrentDownloads();
            boolean done = intent.getBooleanExtra("done", false);
            boolean error = intent.getBooleanExtra("error", false);
            boolean cancelled = intent.getBooleanExtra("cancelled", false);
            if (!done && !error && !cancelled) {
                return;
            }
            DownloadsActivity.this.loadInstalledMarketApps();
        }
    };

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        DownloadsAdapter downloadsAdapter = null;
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_downloads);
        this.titleView = (TextView) findViewById(R.id.txtTitle);
        this.list = (ListView) findViewById(R.id.list);
        this.loadingOverlay = findViewById(R.id.loadingOverlay);
        LinearLayout headerRoot = new LinearLayout(this);
        headerRoot.setOrientation(TYPE_APP);
        this.txtCurrentSection = new TextView(this);
        this.txtCurrentSection.setLayoutParams(new LinearLayout.LayoutParams(-1, -2));
        this.txtCurrentSection.setBackgroundResource(R.drawable.market_header);
        this.txtCurrentSection.setPadding(7, 7, 7, 7);
        this.txtCurrentSection.setText(getString(R.string.currently_downloading));
        this.txtCurrentSection.setTextColor(-1);
        this.currentDownloadsContainer = new LinearLayout(this);
        this.currentDownloadsContainer.setLayoutParams(new LinearLayout.LayoutParams(-1, -2));
        this.currentDownloadsContainer.setOrientation(TYPE_APP);
        headerRoot.addView(this.txtCurrentSection);
        headerRoot.addView(this.currentDownloadsContainer);
        this.currentDownloadsHeader = headerRoot;
        this.list.addHeaderView(this.currentDownloadsHeader, null, false);
        try {
            ((ImageButton) findViewById(R.id.btnHome)).setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.DownloadsActivity.2
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    Intent i = new Intent(DownloadsActivity.this, (Class<?>) MainActivity.class);
                    i.addFlags(67108864);
                    DownloadsActivity.this.startActivity(i);
                    DownloadsActivity.this.finish();
                }
            });
            ((ImageButton) findViewById(R.id.btnSearch)).setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.DownloadsActivity.3
                @Override // android.view.View.OnClickListener
                public void onClick(View v) {
                    DownloadsActivity.this.startActivity(new Intent(DownloadsActivity.this, (Class<?>) SearchActivity.class));
                }
            });
            Typeface tf = Typeface.createFromAsset(getAssets(), "fonts/storopia.ttf");
            this.titleView.setTypeface(tf);
        } catch (Exception e) {
        }
        if (this.currentDownloadsHeader != null) {
            this.currentDownloadsHeader.setVisibility(8);
        }
        this.adapter = new DownloadsAdapter(this, downloadsAdapter);
        this.list.setAdapter((ListAdapter) this.adapter);
        this.list.setOnItemClickListener(new AdapterView.OnItemClickListener() { // from class: com.oldmarket.ui.DownloadsActivity.4
            @Override // android.widget.AdapterView.OnItemClickListener
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                int headers = DownloadsActivity.this.list.getHeaderViewsCount();
                int index = position - headers;
                if (index >= 0 && index < DownloadsActivity.this.rows.size()) {
                    RowItem row = (RowItem) DownloadsActivity.this.rows.get(index);
                    if (row.type == DownloadsActivity.TYPE_APP && row.app != null) {
                        Intent i = new Intent(DownloadsActivity.this, (Class<?>) AppDetailActivity.class);
                        i.putExtra("app_id", row.app.id);
                        DownloadsActivity.this.startActivity(i);
                    }
                }
            }
        });
        refreshCurrentDownloads();
        loadInstalledMarketApps();
    }

    @Override // android.app.Activity
    protected void onResume() {
        super.onResume();
        registerReceiver(this.dlReceiver, new IntentFilter(DownloadService.ACTION_PROGRESS));
        refreshCurrentDownloads();
        if (this.adapter != null) {
            this.adapter.notifyDataSetChanged();
        }
        if (this.rows.isEmpty()) {
            loadInstalledMarketApps();
        }
    }

    @Override // android.app.Activity
    protected void onPause() {
        super.onPause();
        try {
            unregisterReceiver(this.dlReceiver);
        } catch (Exception e) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void refreshCurrentDownloads() {
        this.currentDownloadsContainer.removeAllViews();
        SharedPreferences p = getSharedPreferences("download_state", 0);
        String json = p.getString("tasks_json", "[]");
        try {
            JSONArray arr = new JSONArray(json);
            LayoutInflater inf = LayoutInflater.from(this);
            for (int i = 0; i < arr.length(); i += TYPE_APP) {
                JSONObject o = arr.getJSONObject(i);
                final int appId = o.optInt("app_id", -1);
                String appName = o.optString("app_name", "");
                String statusText = o.optString("status_text", "");
                int percent = o.optInt("percent", 0);
                boolean installing = o.optBoolean("installing", false);
                String icon = o.optString("icon", "");
                View row = inf.inflate(R.layout.list_item_current_download, (ViewGroup) this.currentDownloadsContainer, false);
                ImageView img = (ImageView) row.findViewById(R.id.imgCurrent);
                TextView title = (TextView) row.findViewById(R.id.txtCurrentTitle);
                TextView status = (TextView) row.findViewById(R.id.txtCurrentStatus);
                ProgressBar progress = (ProgressBar) row.findViewById(R.id.progressCurrent);
                title.setText(appName);
                status.setText(statusText);
                if (installing) {
                    progress.setIndeterminate(true);
                } else {
                    progress.setIndeterminate(false);
                    progress.setProgress(percent);
                }
                if (icon == null || icon.length() <= 0) {
                    img.setImageResource(R.drawable.icon_placeholder);
                } else {
                    ImageLoader.load(this, Api.iconUrl(this, icon), img, R.drawable.icon_placeholder);
                }
                row.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.DownloadsActivity.5
                    @Override // android.view.View.OnClickListener
                    public void onClick(View v) {
                        if (appId > 0) {
                            Intent i2 = new Intent(DownloadsActivity.this, (Class<?>) AppDetailActivity.class);
                            i2.putExtra("app_id", appId);
                            DownloadsActivity.this.startActivity(i2);
                        }
                    }
                });
                this.currentDownloadsContainer.addView(row);
            }
            int vis = arr.length() > 0 ? 0 : 8;
            if (this.currentDownloadsHeader != null) {
                this.currentDownloadsHeader.setVisibility(vis);
            }
        } catch (Exception e) {
            if (this.currentDownloadsHeader != null) {
                this.currentDownloadsHeader.setVisibility(8);
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r0v1, types: [com.oldmarket.ui.DownloadsActivity$6] */
    public void loadInstalledMarketApps() {
        showLoading(true);
        new AsyncTask<Void, Void, ArrayList<RowItem>>() { // from class: com.oldmarket.ui.DownloadsActivity.6
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public ArrayList<RowItem> doInBackground(Void... params) {
                try {
                    HashMap<String, Integer> installed = new HashMap<>();
                    PackageManager pm = DownloadsActivity.this.getPackageManager();
                    List<PackageInfo> pkgs = pm.getInstalledPackages(0);
                    for (int i = 0; i < pkgs.size(); i += DownloadsActivity.TYPE_APP) {
                        PackageInfo pi = pkgs.get(i);
                        if (pi != null && pi.packageName != null) {
                            installed.put(pi.packageName, Integer.valueOf(pi.versionCode));
                        }
                    }
                    ArrayList<AppItem> all = new ArrayList<>();
                    DownloadsActivity.this.loadEndpoint("/api/apps?is_game=0", Build.VERSION.SDK_INT, installed, all);
                    DownloadsActivity.this.loadEndpoint("/api/apps?is_game=1", Build.VERSION.SDK_INT, installed, all);
                    ArrayList<AppItem> updates = new ArrayList<>();
                    ArrayList<AppItem> installedOnly = new ArrayList<>();
                    for (int i2 = 0; i2 < all.size(); i2 += DownloadsActivity.TYPE_APP) {
                        AppItem a = all.get(i2);
                        if (a.versionCode <= 0 || a.installedVersionCode <= 0 || a.versionCode <= a.installedVersionCode) {
                            installedOnly.add(a);
                        } else {
                            updates.add(a);
                        }
                    }
                    Comparator<AppItem> cmp = new Comparator<AppItem>() { // from class: com.oldmarket.ui.DownloadsActivity.6.1
                        @Override // java.util.Comparator
                        public int compare(AppItem a1, AppItem a2) {
                            return AppItem.safe(a1.name).compareToIgnoreCase(AppItem.safe(a2.name));
                        }
                    };
                    Collections.sort(updates, cmp);
                    Collections.sort(installedOnly, cmp);
                    ArrayList<RowItem> out = new ArrayList<>();
                    if (!updates.isEmpty()) {
                        RowItem sec = new RowItem(null);
                        sec.type = 0;
                        sec.title = DownloadsActivity.this.getString(R.string.available_updates);
                        out.add(sec);
                        for (int i3 = 0; i3 < updates.size(); i3 += DownloadsActivity.TYPE_APP) {
                            RowItem ri = new RowItem(null);
                            ri.type = DownloadsActivity.TYPE_APP;
                            ri.app = updates.get(i3);
                            out.add(ri);
                        }
                    }
                    RowItem sec2 = new RowItem(null);
                    sec2.type = 0;
                    sec2.title = DownloadsActivity.this.getString(R.string.downloads1);
                    out.add(sec2);
                    for (int i4 = 0; i4 < installedOnly.size(); i4 += DownloadsActivity.TYPE_APP) {
                        RowItem ri2 = new RowItem(null);
                        ri2.type = DownloadsActivity.TYPE_APP;
                        ri2.app = installedOnly.get(i4);
                        out.add(ri2);
                    }
                    return out;
                } catch (Exception e) {
                    return null;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(ArrayList<RowItem> out) {
                DownloadsActivity.this.showLoading(false);
                if (out != null) {
                    DownloadsActivity.this.rows.clear();
                    DownloadsActivity.this.rows.addAll(out);
                    DownloadsActivity.this.adapter.notifyDataSetChanged();
                    if (DownloadsActivity.this.rows.size() == 0) {
                        Toast.makeText(DownloadsActivity.this, R.string.no_downloads, 0).show();
                        return;
                    }
                    return;
                }
                Toast.makeText(DownloadsActivity.this, R.string.error_network, 0).show();
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void loadEndpoint(String endpoint, int deviceApi, Map<String, Integer> installed, ArrayList<AppItem> out) {
        try {
            String s = Http.getString(String.valueOf(Api.baseUrl(this)) + endpoint);
            if (s != null) {
                JSONArray arr = new JSONArray(s);
                for (int i = 0; i < arr.length(); i += TYPE_APP) {
                    JSONObject o = arr.getJSONObject(i);
                    AppItem a = new AppItem();
                    a.id = o.optInt("id", 0);
                    a.name = o.optString("name", "");
                    a.developer = o.optString("developer", o.optString("author", ""));
                    a.icon = o.optString("icon", "");
                    a.api = o.optInt("api", TYPE_APP);
                    a.packageName = o.optString("package", o.optString("package_name", ""));
                    a.isGame = o.optBoolean("is_game", false);
                    a.categoryCode = o.optString("category_code", o.optString("category", ""));
                    a.categoryLabel = o.optString("category_label", a.categoryCode);
                    a.rating = (float) o.optDouble("rating", 0.0d);
                    a.downloads = o.optInt("downloads", 0);
                    a.versionCode = o.optInt("versionCode", o.optInt("version_code", 0));
                    Integer iv = installed.get(a.packageName);
                    a.installedVersionCode = iv == null ? 0 : iv.intValue();
                    a.description = o.optString("description", "");
                    if (a.api <= deviceApi && a.packageName != null && installed.containsKey(a.packageName)) {
                        out.add(a);
                    }
                }
            }
        } catch (Exception e) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showLoading(boolean show) {
        if (this.loadingOverlay != null) {
            this.loadingOverlay.setVisibility(show ? 0 : 8);
        }
    }

    private static class RowItem {
        AppItem app;
        String title;
        int type;

        private RowItem() {
        }

        /* synthetic */ RowItem(RowItem rowItem) {
            this();
        }
    }

    private class DownloadsAdapter extends BaseAdapter {
        private DownloadsAdapter() {
        }

        /* synthetic */ DownloadsAdapter(DownloadsActivity downloadsActivity, DownloadsAdapter downloadsAdapter) {
            this();
        }

        @Override // android.widget.Adapter
        public int getCount() {
            return DownloadsActivity.this.rows.size();
        }

        @Override // android.widget.Adapter
        public Object getItem(int position) {
            return DownloadsActivity.this.rows.get(position);
        }

        @Override // android.widget.Adapter
        public long getItemId(int position) {
            return position;
        }

        @Override // android.widget.BaseAdapter, android.widget.Adapter
        public int getViewTypeCount() {
            return 2;
        }

        @Override // android.widget.BaseAdapter, android.widget.Adapter
        public int getItemViewType(int position) {
            return ((RowItem) DownloadsActivity.this.rows.get(position)).type;
        }

        @Override // android.widget.Adapter
        public View getView(int position, View convertView, ViewGroup parent) {
            RowItem row = (RowItem) DownloadsActivity.this.rows.get(position);
            if (row.type == 0) {
                View v = convertView;
                if (v == null || v.findViewById(R.id.sectionTitle) == null) {
                    v = LayoutInflater.from(DownloadsActivity.this).inflate(R.layout.list_item_section, parent, false);
                }
                TextView tv = (TextView) v.findViewById(R.id.sectionTitle);
                tv.setText(row.title);
                return v;
            }
            View v2 = convertView;
            if (v2 == null || v2.findViewById(R.id.title) == null) {
                v2 = LayoutInflater.from(DownloadsActivity.this).inflate(R.layout.list_item_app, parent, false);
            }
            ImageView img = (ImageView) v2.findViewById(R.id.img);
            TextView title = (TextView) v2.findViewById(R.id.title);
            TextView subtitle = (TextView) v2.findViewById(R.id.subtitle);
            TextView status = (TextView) v2.findViewById(R.id.txtStatus);
            RatingBar ratingBar = (RatingBar) v2.findViewById(R.id.ratingBar);
            AppItem a = row.app;
            title.setText(AppItem.safe(a.name));
            subtitle.setText(AppItem.safe(a.developer));
            ratingBar.setRating(a.rating);
            if (a.versionCode > 0 && a.installedVersionCode > 0 && a.versionCode > a.installedVersionCode) {
                status.setText(DownloadsActivity.this.getString(R.string.updates_available));
                status.setTextColor(-881640);
            } else {
                status.setText(DownloadsActivity.this.getString(R.string.installed));
                status.setTextColor(-13619152);
            }
            String iconUrl = a.icon == null ? "" : Api.iconUrl(DownloadsActivity.this, a.icon);
            ImageLoader.load(DownloadsActivity.this, iconUrl, img, R.drawable.icon_placeholder);
            return v2;
        }
    }
}
