package com.oldmarket.ui;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.ProgressBar;
import android.widget.RatingBar;
import android.widget.TextView;
import android.widget.Toast;
import com.oldmarket.R;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.service.DownloadService;
import com.oldmarket.util.AndroidVersions;
import com.oldmarket.util.ImageLoader;
import com.oldmarket.util.LocaleHelper;
import com.oldmarket.util.Prefs;
import java.io.File;
import java.util.ArrayList;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class AppDetailActivity extends Activity {
    private ReviewAdapter adapter;
    private int appId;
    private Button btnCancelDownload;
    private Button btnInstall;
    private Button btnOpen;
    private Button btnUninstall;
    private LinearLayout downloadPanel;
    private View header;
    private ImageView imgAndroidHeaderLogo;
    private ImageView imgIcon;
    private LinearLayout installButtons;
    private ListView list;
    private View loadingOverlay;
    private ProgressBar progressDownload;
    private RatingBar ratingAddReview;
    private RatingBar ratingHeader;
    private LinearLayout screensContainer;
    private HorizontalScrollView screensScroll;
    private TextView txtAuthor;
    private TextView txtDesc;
    private TextView txtDownloadProgress;
    private TextView txtDownloadsInfo;
    private TextView txtHeaderRating;
    private TextView txtLoading;
    private TextView txtMeta;
    private TextView txtName;
    private TextView txtReviewsInfo;
    private TextView txtReviewsTitle;
    private TextView txtScreensTitle;
    private TextView txtreviewinfo;
    private ArrayList<ReviewItem> reviews = new ArrayList<>();
    private String pkgName = "";
    private String selectedVersion = "";
    private int currentMinApi = 1;
    private boolean hasOwnReview = false;
    private String currentIconFile = "";
    private final BroadcastReceiver dlReceiver = new BroadcastReceiver() { // from class: com.oldmarket.ui.AppDetailActivity.1
        @Override // android.content.BroadcastReceiver
        public void onReceive(Context context, Intent intent) {
            int id = intent.getIntExtra("app_id", -1);
            if (id == AppDetailActivity.this.appId) {
                int percent = intent.getIntExtra("percent", 0);
                long speed = intent.getLongExtra("speed_bps", 0L);
                boolean done = intent.getBooleanExtra("done", false);
                boolean error = intent.getBooleanExtra("error", false);
                boolean cancelled = intent.getBooleanExtra("cancelled", false);
                boolean active = intent.getBooleanExtra("active", false);
                if (active) {
                    AppDetailActivity.this.showDownloadUi(percent, speed);
                }
                if (done) {
                    AppDetailActivity.this.hideDownloadUi();
                    String path = intent.getStringExtra("file_path");
                    if (path != null && AppDetailActivity.this.hasWindowFocus()) {
                        AppDetailActivity.this.openInstaller(path);
                    }
                }
                if (!error && !cancelled) {
                    return;
                }
                AppDetailActivity.this.hideDownloadUi();
            }
        }
    };

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_app_detail);
        this.appId = getIntent().getIntExtra("app_id", 0);
        this.loadingOverlay = findViewById(R.id.loadingOverlay);
        this.txtLoading = (TextView) findViewById(R.id.txtLoading);
        this.list = (ListView) findViewById(R.id.listReviews);
        this.header = LayoutInflater.from(this).inflate(R.layout.app_detail_header, (ViewGroup) this.list, false);
        this.list.addHeaderView(this.header, null, false);
        this.imgIcon = (ImageView) findViewById(R.id.imgIcon);
        this.txtName = (TextView) findViewById(R.id.txtName);
        this.txtAuthor = (TextView) findViewById(R.id.txtAuthor);
        this.txtHeaderRating = (TextView) findViewById(R.id.txtHeaderRating);
        this.ratingHeader = (RatingBar) findViewById(R.id.ratingHeader);
        this.txtDownloadsInfo = (TextView) this.header.findViewById(R.id.txtDownloadsInfo);
        this.txtReviewsInfo = (TextView) this.header.findViewById(R.id.txtReviewsInfo);
        this.txtMeta = (TextView) this.header.findViewById(R.id.txtMeta);
        this.txtDesc = (TextView) this.header.findViewById(R.id.txtDesc);
        this.txtScreensTitle = (TextView) this.header.findViewById(R.id.txtScreensTitle);
        this.screensScroll = (HorizontalScrollView) this.header.findViewById(R.id.screensScroll);
        this.screensContainer = (LinearLayout) this.header.findViewById(R.id.screensContainer);
        this.txtReviewsTitle = (TextView) this.header.findViewById(R.id.txtReviewsTitle);
        this.ratingAddReview = (RatingBar) this.header.findViewById(R.id.ratingAddReview);
        this.txtreviewinfo = (TextView) this.header.findViewById(R.id.txtreviewinfo);
        this.btnInstall = (Button) findViewById(R.id.btnInstall);
        this.btnOpen = (Button) findViewById(R.id.btnOpen);
        this.btnUninstall = (Button) findViewById(R.id.btnUninstall);
        this.btnCancelDownload = (Button) findViewById(R.id.btnCancelDownload);
        this.txtDownloadProgress = (TextView) findViewById(R.id.txtDownloadProgress);
        this.progressDownload = (ProgressBar) findViewById(R.id.progressDownload);
        this.downloadPanel = (LinearLayout) findViewById(R.id.downloadPanel);
        this.installButtons = (LinearLayout) findViewById(R.id.installButtons);
        this.adapter = new ReviewAdapter(this, null);
        this.list.setAdapter((ListAdapter) this.adapter);
        this.list.setOnItemClickListener(new AdapterView.OnItemClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.2
            @Override // android.widget.AdapterView.OnItemClickListener
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                int idx = position - 1;
                if (idx < 0 || idx >= AppDetailActivity.this.reviews.size()) {
                    return;
                }
                AppDetailActivity.this.showReviewActionsDialog((ReviewItem) AppDetailActivity.this.reviews.get(idx));
            }
        });
        this.btnInstall.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.3
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                AppDetailActivity.this.chooseVersionAndDownload();
            }
        });
        this.btnOpen.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.4
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                AppDetailActivity.this.openApp();
            }
        });
        this.btnUninstall.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.5
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                AppDetailActivity.this.uninstallApp();
            }
        });
        this.btnCancelDownload.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.6
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                Intent i = new Intent(AppDetailActivity.this, (Class<?>) DownloadService.class);
                i.setAction(DownloadService.ACTION_CANCEL);
                i.putExtra("app_id", AppDetailActivity.this.appId);
                AppDetailActivity.this.startService(i);
            }
        });
        this.ratingAddReview.setOnTouchListener(new View.OnTouchListener() { // from class: com.oldmarket.ui.AppDetailActivity.7
            @Override // android.view.View.OnTouchListener
            public boolean onTouch(View v, MotionEvent event) {
                if (event.getAction() == 1) {
                    if (Prefs.isLoggedIn(AppDetailActivity.this)) {
                        if (!AppDetailActivity.this.hasOwnReview) {
                            RatingBar rb = (RatingBar) v;
                            float stars = (rb.getNumStars() * event.getX()) / Math.max(1.0f, rb.getWidth());
                            int rating = (int) Math.ceil(stars);
                            if (rating < 1) {
                                rating = 1;
                            }
                            if (rating > 5) {
                                rating = 5;
                            }
                            rb.setRating(rating);
                            AppDetailActivity.this.showAddReviewDialog(rating);
                            rb.setRating(0.0f);
                        }
                    } else {
                        AppDetailActivity.this.startActivity(new Intent(AppDetailActivity.this, (Class<?>) LoginActivity.class));
                    }
                }
                return true;
            }
        });
        try {
            int androidLogoRes = getResources().getIdentifier("market_android_logo", "drawable", getPackageName());
            if (this.imgAndroidHeaderLogo != null && androidLogoRes != 0) {
                this.imgAndroidHeaderLogo.setImageResource(androidLogoRes);
            }
        } catch (Exception e) {
        }
        showLoading(true, getString(R.string.loading));
        loadDetails();
        loadScreenshots();
        loadReviews();
    }

    @Override // android.app.Activity
    protected void onResume() {
        super.onResume();
        registerReceiver(this.dlReceiver, new IntentFilter(DownloadService.ACTION_PROGRESS));
        refreshInstalledButtons();
        restoreDownloadState();
    }

    @Override // android.app.Activity
    protected void onPause() {
        super.onPause();
        try {
            unregisterReceiver(this.dlReceiver);
        } catch (Exception e) {
        }
    }

    private SharedPreferences downloadPrefs() {
        return getSharedPreferences("download_state", 0);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void restoreDownloadState() {
        SharedPreferences p = downloadPrefs();
        if (p.getBoolean("active", false) && p.getInt("app_id", -1) == this.appId) {
            showDownloadUi(p.getInt("percent", 0), p.getLong("speed_bps", 0L));
        } else {
            hideDownloadUi();
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showDownloadUi(int percent, long speed) {
        String speedText;
        this.downloadPanel.setVisibility(0);
        this.installButtons.setVisibility(8);
        this.progressDownload.setProgress(percent);
        if (speed >= 1048576) {
            speedText = String.format(Locale.US, "%.1f MB/s", Float.valueOf((speed / 1024.0f) / 1024.0f));
        } else {
            speedText = String.valueOf(Math.max(1L, speed / 1024)) + " KB/s";
        }
        this.txtDownloadProgress.setText(String.valueOf(percent) + "%  •  " + speedText);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void hideDownloadUi() {
        this.downloadPanel.setVisibility(8);
        this.installButtons.setVisibility(0);
        this.progressDownload.setProgress(0);
        this.txtDownloadProgress.setText("0%");
        refreshInstalledButtons();
    }

    /* JADX WARN: Type inference failed for: r1v2, types: [com.oldmarket.ui.AppDetailActivity$8] */
    private void loadDetails() {
        try {
            int androidLogoRes = getResources().getIdentifier("market_android_logo", "drawable", getPackageName());
            if (this.imgAndroidHeaderLogo != null && androidLogoRes != 0) {
                this.imgAndroidHeaderLogo.setImageResource(androidLogoRes);
            }
        } catch (Exception e) {
        }
        showLoading(true, getString(R.string.loading));
        new AsyncTask<Void, Void, JSONObject>() { // from class: com.oldmarket.ui.AppDetailActivity.8
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public JSONObject doInBackground(Void... v) {
                try {
                    String s = Http.getString(String.valueOf(Api.baseUrl(AppDetailActivity.this)) + "/api/app/" + AppDetailActivity.this.appId);
                    if (s == null) {
                        return null;
                    }
                    return new JSONObject(s);
                } catch (Exception e2) {
                    return null;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(JSONObject o) {
                AppDetailActivity.this.showLoading(false, null);
                if (o != null) {
                    String name = o.optString("name", "");
                    String dev = o.optString("developer", o.optString("author", ""));
                    String desc = o.optString("description", "");
                    String icon = o.optString("icon", "");
                    AppDetailActivity.this.currentIconFile = icon;
                    int api = o.optInt("api", 1);
                    int downloads = o.optInt("downloads", 0);
                    int reviewCount = o.optInt("review_count", 0);
                    float avgRating = (float) o.optDouble("rating", 0.0d);
                    String version = o.optString("version", "");
                    AppDetailActivity.this.pkgName = o.optString("package", o.optString("package_name", ""));
                    AppDetailActivity.this.currentMinApi = api;
                    AppDetailActivity.this.txtName.setText(name);
                    AppDetailActivity.this.txtAuthor.setText(dev);
                    AppDetailActivity.this.txtDesc.setText(desc);
                    AppDetailActivity.this.txtMeta.setText("Android " + AndroidVersions.apiToAndroid(api) + "   Package: " + AppDetailActivity.this.pkgName + "   Version: " + version);
                    AppDetailActivity.this.txtDownloadsInfo.setText(String.valueOf(downloads) + " " + AppDetailActivity.this.getString(R.string.downloads_count));
                    AppDetailActivity.this.txtReviewsInfo.setText(String.valueOf(reviewCount) + " " + AppDetailActivity.this.getString(R.string.reviews_count));
                    AppDetailActivity.this.txtHeaderRating.setText(String.format(Locale.US, "%.1f", Float.valueOf(avgRating)));
                    AppDetailActivity.this.ratingHeader.setRating(avgRating);
                    AppDetailActivity.this.txtReviewsTitle.setText(String.valueOf(AppDetailActivity.this.getString(R.string.reviews)) + " (" + reviewCount + ")");
                    if (icon == null || icon.length() <= 0) {
                        AppDetailActivity.this.imgIcon.setImageResource(R.drawable.icon_placeholder);
                    } else {
                        ImageLoader.load(AppDetailActivity.this, Api.iconUrl(AppDetailActivity.this, icon), AppDetailActivity.this.imgIcon, R.drawable.icon_placeholder);
                    }
                    AppDetailActivity.this.refreshInstalledButtons();
                    AppDetailActivity.this.restoreDownloadState();
                    return;
                }
                AppDetailActivity.this.msg(AppDetailActivity.this.getString(R.string.error_network));
            }
        }.execute(new Void[0]);
    }

    /* JADX WARN: Type inference failed for: r0v0, types: [com.oldmarket.ui.AppDetailActivity$9] */
    private void loadScreenshots() {
        new AsyncTask<Void, Void, JSONArray>() { // from class: com.oldmarket.ui.AppDetailActivity.9
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public JSONArray doInBackground(Void... v) {
                try {
                    String s = Http.getString(String.valueOf(Api.baseUrl(AppDetailActivity.this)) + "/api/app/" + AppDetailActivity.this.appId + "/screenshots");
                    if (s == null) {
                        return null;
                    }
                    return new JSONArray(s);
                } catch (Exception e) {
                    return null;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(JSONArray arr) {
                if (arr == null || arr.length() == 0) {
                    AppDetailActivity.this.txtScreensTitle.setVisibility(8);
                    AppDetailActivity.this.screensScroll.setVisibility(8);
                    return;
                }
                AppDetailActivity.this.txtScreensTitle.setVisibility(0);
                AppDetailActivity.this.screensScroll.setVisibility(0);
                AppDetailActivity.this.screensContainer.removeAllViews();
                for (int i = 0; i < arr.length(); i++) {
                    String file = arr.optString(i, "");
                    if (file != null && file.length() != 0) {
                        ImageView iv = new ImageView(AppDetailActivity.this);
                        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(240, 400);
                        lp.rightMargin = 10;
                        iv.setLayoutParams(lp);
                        iv.setScaleType(ImageView.ScaleType.CENTER_CROP);
                        AppDetailActivity.this.screensContainer.addView(iv);
                        ImageLoader.load(AppDetailActivity.this, Api.screenshotUrl(AppDetailActivity.this, file), iv, R.drawable.banner_placeholder);
                    }
                }
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r0v0, types: [com.oldmarket.ui.AppDetailActivity$10] */
    public void loadReviews() {
        new AsyncTask<Void, Void, Object>() { // from class: com.oldmarket.ui.AppDetailActivity.10
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public Object doInBackground(Void... v) {
                try {
                    int viewerId = Prefs.getUserId(AppDetailActivity.this);
                    String s = Http.getString(Api.appReviewsUrl(AppDetailActivity.this, AppDetailActivity.this.appId, viewerId));
                    if (s == null) {
                        return "null response";
                    }
                    JSONArray arr = new JSONArray(s);
                    ArrayList<ReviewItem> out = new ArrayList<>();
                    for (int i = 0; i < arr.length(); i++) {
                        out.add(AppDetailActivity.this.parseReview(arr.getJSONObject(i)));
                    }
                    return out;
                } catch (Exception e) {
                    return e.toString();
                }
            }

            @Override // android.os.AsyncTask
            protected void onPostExecute(Object out) {
                if (out instanceof String) {
                    AppDetailActivity.this.txtReviewsTitle.setText(String.valueOf(AppDetailActivity.this.getString(R.string.reviews)) + " (0)");
                    AppDetailActivity.this.txtReviewsInfo.setText("0 " + AppDetailActivity.this.getString(R.string.reviews_count));
                    AppDetailActivity.this.hasOwnReview = false;
                    AppDetailActivity.this.ratingAddReview.setVisibility(0);
                    AppDetailActivity.this.txtreviewinfo.setVisibility(0);
                    return;
                }
                ArrayList<ReviewItem> listOut = (ArrayList) out;
                AppDetailActivity.this.reviews.clear();
                AppDetailActivity.this.reviews.addAll(listOut);
                AppDetailActivity.this.hasOwnReview = false;
                int myId = Prefs.getUserId(AppDetailActivity.this);
                int i = 0;
                while (true) {
                    if (i >= AppDetailActivity.this.reviews.size()) {
                        break;
                    }
                    if (((ReviewItem) AppDetailActivity.this.reviews.get(i)).userId == myId && myId > 0) {
                        AppDetailActivity.this.hasOwnReview = true;
                        break;
                    }
                    i++;
                }
                AppDetailActivity.this.txtReviewsTitle.setText(String.valueOf(AppDetailActivity.this.getString(R.string.reviews)) + " (" + AppDetailActivity.this.reviews.size() + ")");
                AppDetailActivity.this.txtReviewsInfo.setText(String.valueOf(AppDetailActivity.this.reviews.size()) + " " + AppDetailActivity.this.getString(R.string.reviews_count));
                AppDetailActivity.this.ratingAddReview.setVisibility(AppDetailActivity.this.hasOwnReview ? 8 : 0);
                AppDetailActivity.this.txtreviewinfo.setVisibility(AppDetailActivity.this.hasOwnReview ? 8 : 0);
                AppDetailActivity.this.adapter.notifyDataSetChanged();
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public ReviewItem parseReview(JSONObject r) {
        ReviewItem ri = new ReviewItem(null);
        ri.id = r.optInt("id", 0);
        ri.userId = r.optInt("user_id", 0);
        ri.username = r.optString("username", "User");
        ri.avatar = r.optString("avatar", "default_avatar.png");
        ri.rating = r.optInt("rating", 0);
        ri.text = r.optString("comment", r.optString("text", ""));
        ri.createdAt = r.optString("created_at", "");
        ri.likes = r.optInt("likes", 0);
        ri.dislikes = r.optInt("dislikes", 0);
        ri.commentsCount = r.optInt("comments_count", 0);
        ri.userReaction = r.optInt("user_reaction", 0);
        return ri;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showAddReviewDialog(final int presetRating) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(1);
        int pad = (int) (10.0f * getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, pad);
        TextView lbl = new TextView(this);
        lbl.setText(isRu() ? "Оценка: " + presetRating : "Rating: " + presetRating);
        layout.addView(lbl);
        final EditText edt = new EditText(this);
        edt.setHint(isRu() ? "Ваш отзыв" : "Your review");
        edt.setMinLines(3);
        layout.addView(edt);
        new AlertDialog.Builder(this).setTitle(isRu() ? "Оставить отзыв" : "Add review").setView(layout).setPositiveButton(isRu() ? "Отправить" : "Send", new DialogInterface.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.11
            @Override // android.content.DialogInterface.OnClickListener
            public void onClick(DialogInterface dialog, int which) {
                String text = edt.getText().toString().trim();
                AppDetailActivity.this.sendReview(text, presetRating);
            }
        }).setNegativeButton(isRu() ? "Отмена" : "Cancel", (DialogInterface.OnClickListener) null).show();
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r1v0, types: [com.oldmarket.ui.AppDetailActivity$12] */
    public void sendReview(final String text, final int rating) {
        final int uid = Prefs.getUserId(this);
        if (uid <= 0) {
            msg("Login required");
        } else {
            new AsyncTask<Void, Void, String>() { // from class: com.oldmarket.ui.AppDetailActivity.12
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public String doInBackground(Void... v) {
                    try {
                        String url = String.valueOf(Api.baseUrl(AppDetailActivity.this)) + "/api/app/" + AppDetailActivity.this.appId + "/review";
                        JSONObject o = new JSONObject();
                        o.put("user_id", uid);
                        o.put("rating", rating);
                        o.put("comment", text);
                        return Http.postJson(url, o.toString());
                    } catch (Exception e) {
                        return null;
                    }
                }

                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public void onPostExecute(String s) {
                    if (s != null) {
                        AppDetailActivity.this.loadReviews();
                        Toast.makeText(AppDetailActivity.this, AppDetailActivity.this.isRu() ? "Отправлено" : "Sent", 0).show();
                    } else {
                        AppDetailActivity.this.msg("Network error");
                    }
                }
            }.execute(new Void[0]);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r0v0, types: [com.oldmarket.ui.AppDetailActivity$13] */
    public void showCommentsDialog(final int reviewId) {
        new AsyncTask<Void, Void, Object>() { // from class: com.oldmarket.ui.AppDetailActivity.13
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public Object doInBackground(Void... v) {
                try {
                    String s = Http.getString(Api.reviewCommentsUrl(AppDetailActivity.this, reviewId));
                    return s == null ? "null response" : new JSONArray(s);
                } catch (Exception e) {
                    return e.toString();
                }
            }

            @Override // android.os.AsyncTask
            protected void onPostExecute(Object out) {
                if (!(out instanceof String)) {
                    JSONArray arr = (JSONArray) out;
                    String[] items = new String[arr.length()];
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject c = arr.optJSONObject(i);
                        if (c == null) {
                            items[i] = String.valueOf(arr.opt(i));
                        } else {
                            String u = c.optString("username", "User");
                            String t = c.optString("text", "");
                            String d = c.optString("created_at", "");
                            items[i] = String.valueOf(u) + ": " + t + (d.length() > 0 ? "  (" + d + ")" : "");
                        }
                    }
                    AlertDialog.Builder items2 = new AlertDialog.Builder(AppDetailActivity.this).setTitle(AppDetailActivity.this.isRu() ? "Комментарии" : "Comments").setItems(items, (DialogInterface.OnClickListener) null);
                    String str = AppDetailActivity.this.isRu() ? "Добавить" : "Add";
                    final int i2 = reviewId;
                    items2.setPositiveButton(str, new DialogInterface.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.13.1
                        @Override // android.content.DialogInterface.OnClickListener
                        public void onClick(DialogInterface dialog, int which) {
                            if (!Prefs.isLoggedIn(AppDetailActivity.this)) {
                                AppDetailActivity.this.startActivity(new Intent(AppDetailActivity.this, (Class<?>) LoginActivity.class));
                            } else {
                                AppDetailActivity.this.showAddCommentDialog(i2);
                            }
                        }
                    }).setNegativeButton(AppDetailActivity.this.isRu() ? "Закрыть" : "Close", (DialogInterface.OnClickListener) null).show();
                    return;
                }
                AppDetailActivity.this.msg("Comments error: " + out);
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showAddCommentDialog(final int reviewId) {
        final EditText edt = new EditText(this);
        edt.setHint(isRu() ? "Комментарий" : "Comment");
        new AlertDialog.Builder(this).setTitle(isRu() ? "Добавить комментарий" : "Add comment").setView(edt).setPositiveButton(isRu() ? "Отправить" : "Send", new DialogInterface.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.14
            @Override // android.content.DialogInterface.OnClickListener
            public void onClick(DialogInterface d, int w) {
                String text = edt.getText().toString().trim();
                if (text.length() == 0) {
                    return;
                }
                AppDetailActivity.this.addReviewComment(reviewId, text);
            }
        }).setNegativeButton(isRu() ? "Отмена" : "Cancel", (DialogInterface.OnClickListener) null).show();
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r1v0, types: [com.oldmarket.ui.AppDetailActivity$15] */
    public void addReviewComment(final int reviewId, final String text) {
        final int uid = Prefs.getUserId(this);
        if (uid <= 0) {
            msg("Login required");
        } else {
            new AsyncTask<Void, Void, String>() { // from class: com.oldmarket.ui.AppDetailActivity.15
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public String doInBackground(Void... v) {
                    try {
                        JSONObject o = new JSONObject();
                        o.put("user_id", uid);
                        o.put("text", text);
                        return Http.postJson(Api.reviewAddCommentUrl(AppDetailActivity.this, reviewId), o.toString());
                    } catch (Exception e) {
                        return null;
                    }
                }

                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public void onPostExecute(String s) {
                    if (s != null) {
                        AppDetailActivity.this.loadReviews();
                    } else {
                        AppDetailActivity.this.msg("Network error");
                    }
                }
            }.execute(new Void[0]);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r1v0, types: [com.oldmarket.ui.AppDetailActivity$16] */
    public void sendReaction(final int reviewId, final int value) {
        final int uid = Prefs.getUserId(this);
        if (uid <= 0) {
            msg("Login required");
        } else {
            new AsyncTask<Void, Void, String>() { // from class: com.oldmarket.ui.AppDetailActivity.16
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public String doInBackground(Void... v) {
                    try {
                        JSONObject o = new JSONObject();
                        o.put("user_id", uid);
                        o.put("value", value);
                        return Http.postJson(Api.reviewReactionUrl(AppDetailActivity.this, reviewId), o.toString());
                    } catch (Exception e) {
                        return null;
                    }
                }

                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public void onPostExecute(String s) {
                    if (s != null) {
                        AppDetailActivity.this.loadReviews();
                    } else {
                        AppDetailActivity.this.msg("Network error");
                    }
                }
            }.execute(new Void[0]);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r1v0, types: [com.oldmarket.ui.AppDetailActivity$17] */
    public void reportReview(final int reviewId) {
        final int uid = Prefs.getUserId(this);
        if (uid <= 0) {
            msg("Login required");
        } else {
            new AsyncTask<Void, Void, String>() { // from class: com.oldmarket.ui.AppDetailActivity.17
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public String doInBackground(Void... v) {
                    try {
                        JSONObject o = new JSONObject();
                        o.put("user_id", uid);
                        return Http.postJson(Api.reviewReportUrl(AppDetailActivity.this, reviewId), o.toString());
                    } catch (Exception e) {
                        return null;
                    }
                }

                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public void onPostExecute(String s) {
                    if (s == null) {
                        AppDetailActivity.this.msg("Network error");
                    } else {
                        AppDetailActivity.this.msg(AppDetailActivity.this.isRu() ? "Отправлено" : "Reported");
                    }
                }
            }.execute(new Void[0]);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r0v3, types: [com.oldmarket.ui.AppDetailActivity$18] */
    public void chooseVersionAndDownload() {
        if (this.btnInstall.isEnabled()) {
            showLoading(true, getString(R.string.loading_versions));
            new AsyncTask<Void, Void, Object>() { // from class: com.oldmarket.ui.AppDetailActivity.18
                /* JADX INFO: Access modifiers changed from: protected */
                @Override // android.os.AsyncTask
                public Object doInBackground(Void... v) {
                    try {
                        String s = Http.getString(Api.appVersionsUrl(AppDetailActivity.this, AppDetailActivity.this.appId));
                        return s == null ? "null" : new JSONArray(s);
                    } catch (Exception e) {
                        return e.toString();
                    }
                }

                @Override // android.os.AsyncTask
                protected void onPostExecute(Object out) {
                    AppDetailActivity.this.showLoading(false, null);
                    if (!(out instanceof String)) {
                        JSONArray arr = (JSONArray) out;
                        if (arr.length() != 0) {
                            ArrayList<String> versList = new ArrayList<>();
                            final ArrayList<String> versValue = new ArrayList<>();
                            for (int i = 0; i < arr.length(); i++) {
                                Object it = arr.opt(i);
                                if (it instanceof JSONObject) {
                                    JSONObject o = (JSONObject) it;
                                    String v = o.optString("version", "");
                                    if (v.length() != 0) {
                                        int api = o.optInt("api", o.optInt("min_api", 0));
                                        String label = v;
                                        if (api > 0) {
                                            label = String.valueOf(v) + " (Android " + AndroidVersions.apiToAndroid(api) + ")";
                                        }
                                        versList.add(label);
                                        versValue.add(v);
                                    }
                                } else if (it != null) {
                                    String v2 = String.valueOf(it);
                                    if (v2.length() != 0) {
                                        versList.add(v2);
                                        versValue.add(v2);
                                    }
                                }
                            }
                            if (versList.size() != 0) {
                                new AlertDialog.Builder(AppDetailActivity.this).setTitle(AppDetailActivity.this.isRu() ? "Выберите версию" : "Select version").setItems((CharSequence[]) versList.toArray(new String[versList.size()]), new DialogInterface.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.18.1
                                    @Override // android.content.DialogInterface.OnClickListener
                                    public void onClick(DialogInterface d, int which) {
                                        AppDetailActivity.this.startDownload((String) versValue.get(which));
                                    }
                                }).setNegativeButton(AppDetailActivity.this.isRu() ? "Отмена" : "Cancel", (DialogInterface.OnClickListener) null).show();
                                return;
                            } else {
                                AppDetailActivity.this.startDownload("");
                                return;
                            }
                        }
                        AppDetailActivity.this.startDownload("");
                        return;
                    }
                    AppDetailActivity.this.startDownload("");
                }
            }.execute(new Void[0]);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void startDownload(String version) {
        if (version == null) {
            version = "";
        }
        this.selectedVersion = version;
        int uid = Prefs.getUserId(this);
        String safeVersion = this.selectedVersion;
        if (safeVersion.length() > 0) {
            safeVersion = Uri.encode(safeVersion);
        }
        String url = String.valueOf(Api.baseUrl(this)) + (safeVersion.length() > 0 ? "/api/download/" + this.appId + "/" + safeVersion : "/api/download/" + this.appId) + (uid > 0 ? "?user_id=" + uid : "");
        Intent i = new Intent(this, (Class<?>) DownloadService.class);
        i.setAction(DownloadService.ACTION_START);
        i.putExtra("app_id", this.appId);
        i.putExtra("app_name", this.txtName == null ? "" : String.valueOf(this.txtName.getText()));
        i.putExtra("icon", this.currentIconFile == null ? "" : this.currentIconFile);
        i.putExtra("url", url);
        i.putExtra("file_name", "oldmarket_" + this.appId + (this.selectedVersion.length() > 0 ? "_" + this.selectedVersion : "") + ".apk");
        startService(i);
        showDownloadUi(0, 0L);
        startActivity(new Intent(this, (Class<?>) DownloadsActivity.class));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void refreshInstalledButtons() {
        boolean installed = this.pkgName != null && this.pkgName.length() > 0 && isInstalled(this.pkgName);
        if (this.currentMinApi > Build.VERSION.SDK_INT) {
            this.btnInstall.setVisibility(0);
            this.btnOpen.setVisibility(8);
            this.btnUninstall.setVisibility(8);
            this.btnInstall.setEnabled(false);
            this.btnInstall.setText(getString(R.string.not_compatible));
            return;
        }
        if (installed) {
            this.btnInstall.setVisibility(0);
            this.btnOpen.setVisibility(0);
            this.btnUninstall.setVisibility(0);
            this.btnInstall.setText(isRu() ? "Скачать" : "Download");
            this.btnOpen.setText(getString(R.string.open));
            this.btnUninstall.setText(getString(R.string.uninstall));
            this.btnInstall.setEnabled(true);
            return;
        }
        this.btnInstall.setVisibility(0);
        this.btnOpen.setVisibility(8);
        this.btnUninstall.setVisibility(8);
        this.btnInstall.setText(getString(R.string.install));
        this.btnInstall.setEnabled(true);
    }

    private boolean isInstalled(String packageName) {
        if (packageName == null || packageName.length() == 0) {
            return false;
        }
        try {
            getPackageManager().getPackageInfo(packageName, 0);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void openApp() {
        if (this.pkgName != null && this.pkgName.length() != 0) {
            PackageManager pm = getPackageManager();
            Intent launch = pm.getLaunchIntentForPackage(this.pkgName);
            if (launch != null) {
                startActivity(launch);
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void uninstallApp() {
        if (this.pkgName != null && this.pkgName.length() != 0) {
            Intent intent = new Intent("android.intent.action.DELETE");
            intent.setData(Uri.parse("package:" + this.pkgName));
            startActivity(intent);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void openInstaller(String path) {
        try {
            File f = new File(path);
            Intent intent = new Intent("android.intent.action.VIEW");
            intent.setDataAndType(Uri.fromFile(f), "application/vnd.android.package-archive");
            intent.setFlags(268435456);
            startActivity(intent);
        } catch (Exception e) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void msg(String s) {
        try {
            new AlertDialog.Builder(this).setMessage(s).setPositiveButton("OK", (DialogInterface.OnClickListener) null).show();
        } catch (Exception e) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showLoading(boolean show, String text) {
        if (this.txtLoading != null && text != null) {
            this.txtLoading.setText(text);
        }
        if (this.loadingOverlay != null) {
            this.loadingOverlay.setVisibility(show ? 0 : 8);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean isRu() {
        try {
            String lang = Locale.getDefault().getLanguage();
            if (lang != null) {
                return lang.toLowerCase().startsWith("ru");
            }
            return false;
        } catch (Exception e) {
            return false;
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void showReviewActionsDialog(final ReviewItem r) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(1);
        int pad = (int) (10.0f * getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, pad);
        Button btnProfile = new Button(this);
        btnProfile.setText(String.valueOf(isRu() ? "Профиль" : "Profile") + (r.userId > 0 ? "" : ""));
        layout.addView(btnProfile);
        Button btnLike = new Button(this);
        btnLike.setText(String.valueOf(isRu() ? "Лайк" : "Like") + " (" + r.likes + ")");
        layout.addView(btnLike);
        Button btnDislike = new Button(this);
        btnDislike.setText(String.valueOf(isRu() ? "Дизлайк" : "Dislike") + " (" + r.dislikes + ")");
        layout.addView(btnDislike);
        Button btnComments = new Button(this);
        btnComments.setText(String.valueOf(isRu() ? "Комментарии" : "Comments") + " (" + r.commentsCount + ")");
        layout.addView(btnComments);
        Button btnReport = new Button(this);
        btnReport.setText(isRu() ? "Пожаловаться" : "Report");
        layout.addView(btnReport);
        boolean logged = Prefs.isLoggedIn(this);
        if (!logged) {
            btnLike.setEnabled(false);
            btnDislike.setEnabled(false);
            btnReport.setEnabled(false);
        } else {
            if (r.userReaction == 1) {
                btnLike.setEnabled(false);
            }
            if (r.userReaction == -1) {
                btnDislike.setEnabled(false);
            }
        }
        final AlertDialog dialog = new AlertDialog.Builder(this).setTitle(r.username).setView(layout).setNegativeButton(isRu() ? "Закрыть" : "Close", (DialogInterface.OnClickListener) null).create();
        btnProfile.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.19
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                dialog.dismiss();
                if (r.userId > 0) {
                    Intent i = new Intent(AppDetailActivity.this, (Class<?>) UserProfileActivity.class);
                    i.putExtra("user_id", r.userId);
                    AppDetailActivity.this.startActivity(i);
                }
            }
        });
        btnLike.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.20
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                dialog.dismiss();
                AppDetailActivity.this.sendReaction(r.id, 1);
            }
        });
        btnDislike.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.21
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                dialog.dismiss();
                AppDetailActivity.this.sendReaction(r.id, -1);
            }
        });
        btnComments.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.22
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                dialog.dismiss();
                AppDetailActivity.this.showCommentsDialog(r.id);
            }
        });
        btnReport.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.AppDetailActivity.23
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                dialog.dismiss();
                AppDetailActivity.this.reportReview(r.id);
            }
        });
        dialog.show();
    }

    private static class ReviewItem {
        String avatar;
        int commentsCount;
        String createdAt;
        int dislikes;
        int id;
        int likes;
        int rating;
        String text;
        int userId;
        int userReaction;
        String username;

        private ReviewItem() {
            this.username = "User";
            this.avatar = "default_avatar.png";
            this.rating = 0;
            this.text = "";
            this.createdAt = "";
            this.likes = 0;
            this.dislikes = 0;
            this.commentsCount = 0;
            this.userReaction = 0;
        }

        /* synthetic */ ReviewItem(ReviewItem reviewItem) {
            this();
        }
    }

    private class ReviewAdapter extends BaseAdapter {
        private ReviewAdapter() {
        }

        /* synthetic */ ReviewAdapter(AppDetailActivity appDetailActivity, ReviewAdapter reviewAdapter) {
            this();
        }

        @Override // android.widget.Adapter
        public int getCount() {
            return AppDetailActivity.this.reviews.size();
        }

        @Override // android.widget.Adapter
        public Object getItem(int position) {
            return AppDetailActivity.this.reviews.get(position);
        }

        @Override // android.widget.Adapter
        public long getItemId(int position) {
            return position;
        }

        @Override // android.widget.Adapter
        public View getView(int position, View convertView, ViewGroup parent) {
            if (convertView == null) {
                convertView = LayoutInflater.from(AppDetailActivity.this).inflate(R.layout.list_item_review, parent, false);
            }
            ReviewItem r = (ReviewItem) AppDetailActivity.this.reviews.get(position);
            ImageView imgUser = (ImageView) convertView.findViewById(R.id.imgUser);
            TextView txtUser = (TextView) convertView.findViewById(R.id.txtUser);
            TextView txtDate = (TextView) convertView.findViewById(R.id.txtDate);
            TextView txtMetaLocal = (TextView) convertView.findViewById(R.id.txtMeta);
            TextView txtText = (TextView) convertView.findViewById(R.id.txtText);
            RatingBar rb = (RatingBar) convertView.findViewById(R.id.ratingBarReview);
            txtUser.setText(r.username);
            txtDate.setText(r.createdAt);
            txtMetaLocal.setText("");
            txtText.setText(r.text);
            rb.setRating(r.rating);
            ImageLoader.load(AppDetailActivity.this, Api.avatarUrl(AppDetailActivity.this, r.avatar), imgUser, R.drawable.icon_placeholder);
            return convertView;
        }
    }
}
