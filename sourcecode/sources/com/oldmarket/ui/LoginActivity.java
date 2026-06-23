package com.oldmarket.ui;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.ProgressDialog;
import android.content.DialogInterface;
import android.os.AsyncTask;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import com.oldmarket.R;
import com.oldmarket.net.Api;
import com.oldmarket.net.Http;
import com.oldmarket.util.LocaleHelper;
import com.oldmarket.util.Prefs;
import org.json.JSONObject;

/* JADX INFO: loaded from: classes.dex */
public class LoginActivity extends Activity {
    private Button btnLogin;
    private Button btnLogout;
    private EditText edtPass;
    private EditText edtUser;
    private TextView txtStatus;

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_login);
        this.edtUser = (EditText) findViewById(R.id.edtUser);
        this.edtPass = (EditText) findViewById(R.id.edtPass);
        this.btnLogin = (Button) findViewById(R.id.btnLogin);
        this.btnLogout = (Button) findViewById(R.id.btnLogout);
        this.txtStatus = (TextView) findViewById(R.id.txtStatus);
        refreshUi();
        this.btnLogin.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.LoginActivity.1
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                LoginActivity.this.doLogin();
            }
        });
        this.btnLogout.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.LoginActivity.2
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                Prefs.logout(LoginActivity.this);
                LoginActivity.this.refreshUi();
                LoginActivity.this.msg("OK");
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void refreshUi() {
        boolean logged = Prefs.isLoggedIn(this);
        this.btnLogout.setEnabled(logged);
        if (logged) {
            String u = Prefs.getUsername(this);
            this.txtStatus.setText("Logged in as " + (u.length() > 0 ? u : "ID " + Prefs.getUserId(this)));
            this.edtUser.setText(u);
            this.edtPass.setText("");
            return;
        }
        this.txtStatus.setText("Not logged in");
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Type inference failed for: r3v10, types: [com.oldmarket.ui.LoginActivity$3] */
    public void doLogin() {
        final String u = this.edtUser.getText().toString().trim();
        final String p = this.edtPass.getText().toString();
        if (u.length() == 0 || p.length() == 0) {
            msg("Enter username and password");
            return;
        }
        final ProgressDialog pd = new ProgressDialog(this);
        pd.setMessage(getString(R.string.loading));
        pd.setCancelable(false);
        pd.show();
        new AsyncTask<Void, Void, String>() { // from class: com.oldmarket.ui.LoginActivity.3
            /* JADX INFO: Access modifiers changed from: protected */
            @Override // android.os.AsyncTask
            public String doInBackground(Void... v) {
                try {
                    JSONObject o = new JSONObject();
                    o.put("username", u);
                    o.put("password", p);
                    return Http.postJson(Api.loginUrl(LoginActivity.this), o.toString());
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
                if (s != null) {
                    try {
                        JSONObject o = new JSONObject(s);
                        if (o.optBoolean("success", false)) {
                            int id = o.optInt("user_id", 0);
                            String name = o.optString("username", "");
                            if (id > 0) {
                                Prefs.setAuth(LoginActivity.this, id, name);
                                LoginActivity.this.refreshUi();
                                LoginActivity.this.msg("OK");
                                LoginActivity.this.finish();
                            } else {
                                LoginActivity.this.msg("Bad response");
                            }
                        } else {
                            LoginActivity.this.msg(o.optString("error", "Login failed"));
                        }
                        return;
                    } catch (Exception e2) {
                        LoginActivity.this.msg("Bad response: " + s);
                        return;
                    }
                }
                LoginActivity.this.msg(LoginActivity.this.getString(R.string.error_network));
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
