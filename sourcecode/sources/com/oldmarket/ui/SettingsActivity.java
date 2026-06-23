package com.oldmarket.ui;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.SpinnerAdapter;
import android.widget.Toast;
import com.oldmarket.R;
import com.oldmarket.util.LocaleHelper;
import com.oldmarket.util.Prefs;
import java.io.DataOutputStream;

/* JADX INFO: loaded from: classes.dex */
public class SettingsActivity extends Activity {
    private Button btnSave;
    private CheckBox chkAutoInstallRoot;
    private EditText edtServer;
    private boolean ignoreRootToggle = false;
    private Spinner spnLang;

    @Override // android.app.Activity
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LocaleHelper.applySavedLocale(this);
        setContentView(R.layout.activity_settings);
        this.edtServer = (EditText) findViewById(R.id.edtServer);
        this.spnLang = (Spinner) findViewById(R.id.spnLang);
        this.btnSave = (Button) findViewById(R.id.btnSave);
        this.chkAutoInstallRoot = (CheckBox) findViewById(R.id.chkAutoInstallRoot);
        ArrayAdapter<String> a = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, new String[]{getString(R.string.lang_ru), getString(R.string.lang_en)});
        a.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        this.spnLang.setAdapter((SpinnerAdapter) a);
        this.edtServer.setText(Prefs.getServer(this));
        String lang = Prefs.getLang(this);
        this.spnLang.setSelection("en".equals(lang) ? 1 : 0);
        if (this.chkAutoInstallRoot != null) {
            this.chkAutoInstallRoot.setChecked(Prefs.isAutoInstallRoot(this));
            this.chkAutoInstallRoot.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() { // from class: com.oldmarket.ui.SettingsActivity.1
                @Override // android.widget.CompoundButton.OnCheckedChangeListener
                public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                    if (!SettingsActivity.this.ignoreRootToggle) {
                        if (!isChecked) {
                            Prefs.setAutoInstallRoot(SettingsActivity.this, false);
                            return;
                        }
                        if (SettingsActivity.this.requestRootAccess()) {
                            Prefs.setRootGranted(SettingsActivity.this, true);
                            Prefs.setAutoInstallRoot(SettingsActivity.this, true);
                            Toast.makeText(SettingsActivity.this, SettingsActivity.this.getString(R.string.auto_install_root), 0).show();
                        } else {
                            Prefs.setRootGranted(SettingsActivity.this, false);
                            Prefs.setAutoInstallRoot(SettingsActivity.this, false);
                            SettingsActivity.this.ignoreRootToggle = true;
                            SettingsActivity.this.chkAutoInstallRoot.setChecked(false);
                            SettingsActivity.this.ignoreRootToggle = false;
                            Toast.makeText(SettingsActivity.this, "ROOT denied", 0).show();
                        }
                    }
                }
            });
        }
        this.btnSave.setOnClickListener(new View.OnClickListener() { // from class: com.oldmarket.ui.SettingsActivity.2
            @Override // android.view.View.OnClickListener
            public void onClick(View v) {
                String host = SettingsActivity.this.edtServer.getText().toString().trim();
                if (host.length() == 0) {
                    host = "94.156.115.120";
                }
                Prefs.setServer(SettingsActivity.this, host);
                String sel = SettingsActivity.this.spnLang.getSelectedItemPosition() == 1 ? "en" : "ru";
                Prefs.setLang(SettingsActivity.this, sel);
                LocaleHelper.applySavedLocale(SettingsActivity.this);
                Toast.makeText(SettingsActivity.this, R.string.save, 0).show();
                SettingsActivity.this.finish();
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean requestRootAccess() throws Throwable {
        DataOutputStream os;
        Process p = null;
        DataOutputStream os2 = null;
        try {
            p = Runtime.getRuntime().exec("su");
            os = new DataOutputStream(p.getOutputStream());
        } catch (Exception e) {
        } catch (Throwable th) {
            th = th;
        }
        try {
            os.writeBytes("exit\n");
            os.flush();
            int rc = p.waitFor();
            z = rc == 0;
            if (os != null) {
                try {
                    os.close();
                } catch (Exception e2) {
                }
            }
            if (p != null) {
                try {
                    p.destroy();
                } catch (Exception e3) {
                }
            }
        } catch (Exception e4) {
            os2 = os;
            if (os2 != null) {
                try {
                    os2.close();
                } catch (Exception e5) {
                }
            }
            if (p != null) {
                try {
                    p.destroy();
                } catch (Exception e6) {
                }
            }
        } catch (Throwable th2) {
            th = th2;
            os2 = os;
            if (os2 != null) {
                try {
                    os2.close();
                } catch (Exception e7) {
                }
            }
            if (p == null) {
                throw th;
            }
            try {
                p.destroy();
                throw th;
            } catch (Exception e8) {
                throw th;
            }
        }
        return z;
    }
}
