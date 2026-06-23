package com.oldmarket.ui;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.content.DialogInterface;
import android.os.AsyncTask;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.Spinner;
import android.widget.SpinnerAdapter;
import android.widget.TextView;
import com.oldmarket.R;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.util.ImageLoader;
import com.oldmarket.util.LocaleHelper;
import com.oldmarket.util.Prefs;
import org.json.JSONArray;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class ProfileActivity extends Activity {
    private Button btnLogout;
    private Button btnSave;
    private EditText edtDesc;
    private ImageView imgAvatar;
    private Spinner spAvatar;
    private TextView txtCreated;
    private TextView txtUser;
    private int userId;

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_profile);
        this.userId = Prefs.getUserId(this);
        if (this.userId <= 0) {
            msg("Login required");
            finish();
            return;
        }
        this.imgAvatar = (ImageView) findViewById(R.id.imgAvatar);
        this.spAvatar = (Spinner) findViewById(R.id.spAvatar);
        this.edtDesc = (EditText) findViewById(R.id.edtDesc);
        this.txtUser = (TextView) findViewById(R.id.txtUser);
        this.txtCreated = (TextView) findViewById(R.id.txtCreated);
        this.btnSave = (Button) findViewById(R.id.btnSave);
        this.btnLogout = (Button) findViewById(R.id.btnLogout);
        this.txtUser.setText(Prefs.getUsername(this));
        this.btnSave.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.ProfileActivity.1
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                ProfileActivity.this.saveProfile();
            }
        });
        this.btnLogout.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.ProfileActivity.2
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                Prefs.logout(ProfileActivity.this);
                ProfileActivity.this.msg("Logged out");
                ProfileActivity.this.finish();
            }
        });
        loadAvatarsThenProfile();
    }

    /* JADX WARN: Type inference failed for: r1v2, types: [com.oldmarket.ui.ProfileActivity$3] */
    private void loadAvatarsThenProfile() {
        final ProgressDialog pd = new ProgressDialog(this);
        pd.setMessage(getString(R.string.loading));
        pd.setCancelable(false);
        pd.show();
        new AsyncTask<Void, Void, Object[]>() { // from class: com.oldmarket.ui.ProfileActivity.3
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public Object[] doInBackground(Void... v) {
                Object[] objArr = null;
                try {
                    String sA = Http.getString(Api.avatarsUrl(ProfileActivity.this));
                    if (sA == null) {
                        return null;
                    }
                    JSONArray aArr = new JSONArray(sA);
                    String[] avatars = new String[aArr.length()];
                    for (int i = 0; i < aArr.length(); i++) {
                        avatars[i] = aArr.getString(i);
                    }
                    String sP = Http.getString(Api.userProfileUrl(ProfileActivity.this, ProfileActivity.this.userId));
                    if (sP == null) {
                        return null;
                    }
                    JSONObject prof = new JSONObject(sP);
                    objArr = new Object[]{avatars, prof};
                    return objArr;
                } catch (Exception e) {
                    return objArr;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(Object[] out) {
                try {
                    pd.dismiss();
                } catch (Exception e) {
                }
                if (out != null) {
                    final String[] avatars = (String[]) out[0];
                    JSONObject prof = (JSONObject) out[1];
                    ArrayAdapter<String> ad = new ArrayAdapter<>(ProfileActivity.this, android.R.layout.simple_spinner_item, avatars);
                    ad.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
                    ProfileActivity.this.spAvatar.setAdapter((SpinnerAdapter) ad);
                    ProfileActivity.this.spAvatar.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() { // from class: com.oldmarket.ui.ProfileActivity.3.1
                        @Override // android.widget.AdapterView.OnItemSelectedListener
                        public void onItemSelected(AdapterView<?> parent, View view, int pos, long id) {
                            String file = avatars[pos];
                            ImageLoader.load(ProfileActivity.this, Api.avatarUrl(ProfileActivity.this, file), ProfileActivity.this.imgAvatar, R.drawable.icon_placeholder);
                        }

                        @Override // android.widget.AdapterView.OnItemSelectedListener
                        public void onNothingSelected(AdapterView<?> parent) {
                        }
                    });
                    String username = prof.optString("username", Prefs.getUsername(ProfileActivity.this));
                    String avatar = prof.optString("avatar", "default_avatar.png");
                    String desc = prof.optString("description", "");
                    String created = prof.optString("created_at", "");
                    ProfileActivity.this.txtUser.setText(username);
                    ProfileActivity.this.edtDesc.setText(desc);
                    if (created == null || created.length() > 0) {
                        ProfileActivity.this.txtCreated.setText("Created: " + created);
                    } else {
                        ProfileActivity.this.txtCreated.setText("Created: " + created);
                    }
                    int idx = 0;
                    int i = 0;
                    while (true) {
                        if (i >= avatars.length) {
                            break;
                        }
                        if (avatars[i].equalsIgnoreCase(avatar)) {
                            idx = i;
                            break;
                        }
                        i++;
                    }
                    ProfileActivity.this.spAvatar.setSelection(idx);
                    ImageLoader.load(ProfileActivity.this, Api.avatarUrl(ProfileActivity.this, avatars[idx]), ProfileActivity.this.imgAvatar, R.drawable.icon_placeholder);
                    return;
                }
                ProfileActivity.this.msg(ProfileActivity.this.getString(R.string.error_network));
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r3v4, types: [com.oldmarket.ui.ProfileActivity$4] */
    public void saveProfile() {
        final String avatar = (String) this.spAvatar.getSelectedItem();
        final String desc = this.edtDesc.getText().toString();
        final ProgressDialog pd = new ProgressDialog(this);
        pd.setMessage("Saving...");
        pd.setCancelable(false);
        pd.show();
        new AsyncTask<Void, Void, String>() { // from class: com.oldmarket.ui.ProfileActivity.4
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public String doInBackground(Void... v) {
                try {
                    JSONObject o = new JSONObject();
                    o.put("avatar", avatar);
                    o.put("description", desc);
                    return Http.putJson(Api.userProfileUrl(ProfileActivity.this, ProfileActivity.this.userId), o.toString());
                } catch (Exception e) {
                    return null;
                }
            }

            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public void onPostExecute(String s) {
                try {
                    pd.dismiss();
                } catch (Exception e) {
                }
                if (s == null) {
                    ProfileActivity.this.msg(ProfileActivity.this.getString(R.string.error_network));
                } else {
                    ProfileActivity.this.msg("Saved");
                }
            }
        }.execute(new Void[0]);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void msg(String s) {
        try {
            new AlertDialog.Builder(this).setMessage(s).setPositiveButton("OK", (DialogInterface.OnClickListener) null).show();
        } catch (Exception e) {
        }
    }
}
