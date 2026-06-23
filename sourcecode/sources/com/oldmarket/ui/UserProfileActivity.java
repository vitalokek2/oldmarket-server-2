package com.oldmarket.ui;

import android.app.Activity;
import android.app.ProgressDialog;
import android.os.AsyncTask;
import android.os.Bundle;
import android.widget.ImageView;
import android.widget.TextView;
import com.oldmarket.R;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.util.ImageLoader;
import com.oldmarket.util.LocaleHelper;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class UserProfileActivity extends Activity {
    private ImageView imgAvatar;
    private TextView txtCreated;
    private TextView txtDesc;
    private TextView txtUser;
    private int userId;

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_user_profile);
        this.userId = getIntent().getIntExtra("user_id", 0);
        this.imgAvatar = (ImageView) findViewById(R.id.imgAvatar);
        this.txtUser = (TextView) findViewById(R.id.txtUser);
        this.txtCreated = (TextView) findViewById(R.id.txtCreated);
        this.txtDesc = (TextView) findViewById(R.id.txtDesc);
        loadProfile();
    }

    /* JADX WARN: Type inference failed for: r1v2, types: [com.oldmarket.ui.UserProfileActivity$1] */
    private void loadProfile() {
        final ProgressDialog pd = new ProgressDialog(this);
        pd.setMessage(getString(R.string.loading));
        pd.setCancelable(false);
        pd.show();
        new AsyncTask<Void, Void, JSONObject>() { // from class: com.oldmarket.ui.UserProfileActivity.1
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public JSONObject doInBackground(Void... v) {
                try {
                    String s = Http.getString(Api.userProfileUrl(UserProfileActivity.this, UserProfileActivity.this.userId));
                    if (s == null) {
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
                try {
                    pd.dismiss();
                } catch (Exception e) {
                }
                if (o == null) {
                    UserProfileActivity.this.txtUser.setText("Network error");
                    return;
                }
                String username = o.optString("username", "User");
                String avatar = o.optString("avatar", "default_avatar.png");
                String desc = o.optString("description", "");
                String created = o.optString("created_at", "");
                UserProfileActivity.this.txtUser.setText(String.valueOf(username) + " (ID: " + UserProfileActivity.this.userId + ")");
                TextView textView = UserProfileActivity.this.txtDesc;
                if (desc == null || desc.length() <= 0) {
                    desc = "-";
                }
                textView.setText(desc);
                UserProfileActivity.this.txtCreated.setText((created == null || created.length() <= 0) ? "Created: -" : "Created: " + created);
                ImageLoader.load(UserProfileActivity.this, Api.avatarUrl(UserProfileActivity.this, avatar), UserProfileActivity.this.imgAvatar, R.drawable.icon_placeholder);
            }
        }.execute(new Void[0]);
    }
}
