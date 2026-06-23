package com.oldmarket.ui;

import android.app.Activity;
import android.content.Intent;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.widget.AdapterView;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;
import com.oldmarket.R;
import com.oldmarket.model.AppItem;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.util.LocaleHelper;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class SearchActivity extends Activity {
    private AppListAdapter adapter;
    private ImageButton btn;
    private ArrayList<AppItem> data = new ArrayList<>();
    private EditText edt;
    private ListView list;
    private View loadingOverlay;
    private SearchTask searchTask;

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_search);
        this.edt = (EditText) findViewById(R.id.edtQuery);
        this.btn = (ImageButton) findViewById(R.id.btnDoSearch);
        this.list = (ListView) findViewById(R.id.list);
        this.loadingOverlay = findViewById(R.id.loadingOverlay);
        this.adapter = new AppListAdapter(this, this.data);
        this.list.setAdapter((ListAdapter) this.adapter);
        this.list.setOnItemClickListener(new AdapterView.OnItemClickListener() { // from class: com.oldmarket.ui.SearchActivity.1
            @Override // android.widget.AdapterView.OnItemClickListener
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                AppItem it = (AppItem) SearchActivity.this.data.get(position);
                Intent i = new Intent(SearchActivity.this, (Class<?>) AppDetailActivity.class);
                i.putExtra("app_id", it.id);
                SearchActivity.this.startActivity(i);
            }
        });
        this.btn.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.SearchActivity.2
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                SearchActivity.this.doSearch();
            }
        });
        this.edt.setOnEditorActionListener(new TextView.OnEditorActionListener() { // from class: com.oldmarket.ui.SearchActivity.3
            @Override // android.widget.TextView.OnEditorActionListener
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                if (actionId != 3 && actionId != 6) {
                    return false;
                }
                SearchActivity.this.doSearch();
                return true;
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void doSearch() {
        String q = this.edt.getText().toString().trim();
        if (q.length() != 0) {
            if (this.searchTask != null) {
                this.searchTask.cancel(true);
            }
            this.searchTask = new SearchTask(q);
            this.searchTask.execute(new Void[0]);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showLoading(boolean show) {
        if (this.loadingOverlay != null) {
            this.loadingOverlay.setVisibility(show ? 0 : 8);
        }
    }

    private class SearchTask extends AsyncTask<Void, Void, Object> {
        private final String q;
        private String url;

        SearchTask(String q) {
            this.q = q;
        }

        @Override // android.os.AsyncTask
        protected void onPreExecute() {
            SearchActivity.this.showLoading(true);
        }

        /* JADX INFO: Access modifiers changed from: protected */
        @Override // android.os.AsyncTask
        public Object doInBackground(Void... v) {
            try {
                this.url = String.valueOf(Api.baseUrl(SearchActivity.this)) + "/api/apps/search?q=" + URLEncoder.encode(this.q, "UTF-8") + "&limit=200&offset=0";
                String s = Http.getString(this.url);
                if (s == null) {
                    return "HTTP returned null\nURL=" + this.url;
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
                    a.isGame = o.optBoolean("is_game", false);
                    a.packageName = o.optString("package", o.optString("package_name", ""));
                    a.rating = (float) o.optDouble("rating", 0.0d);
                    if (a.api <= deviceApi) {
                        out.add(a);
                    }
                }
                return out;
            } catch (Exception e) {
                return "URL=" + this.url + "\n" + e.toString();
            }
        }

        @Override // android.os.AsyncTask
        protected void onPostExecute(Object out) {
            SearchActivity.this.showLoading(false);
            if (out instanceof String) {
                Toast.makeText(SearchActivity.this, "Search error: " + out, 1).show();
                return;
            }
            List<AppItem> listOut = (List) out;
            SearchActivity.this.data.clear();
            SearchActivity.this.data.addAll(listOut);
            SearchActivity.this.adapter.refreshInstalledPackages();
            SearchActivity.this.adapter.notifyDataSetChanged();
            if (listOut.size() == 0) {
                Toast.makeText(SearchActivity.this, R.string.nothing_found, 0).show();
            }
        }

        @Override // android.os.AsyncTask
        protected void onCancelled() {
            SearchActivity.this.showLoading(false);
        }
    }
}
