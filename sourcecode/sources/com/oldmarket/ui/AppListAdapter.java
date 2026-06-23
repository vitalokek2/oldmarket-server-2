package com.oldmarket.ui;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.ImageView;
import android.widget.RatingBar;
import android.widget.TextView;
import com.oldmarket.R;
import com.oldmarket.model.AppItem;
import com.oldmarket.net.Api;
import com.oldmarket.util.ImageLoader;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/* JADX INFO: loaded from: classes.dex */
public class AppListAdapter extends BaseAdapter {
    private final Context c;
    private final LayoutInflater inf;
    private final Map<String, Integer> installedPackages = new HashMap();
    private final List<AppItem> items;

    public AppListAdapter(Context c, List<AppItem> items) {
        this.c = c;
        this.items = items;
        this.inf = LayoutInflater.from(c);
        refreshInstalledPackages();
    }

    public void refreshInstalledPackages() {
        this.installedPackages.clear();
        try {
            PackageManager pm = this.c.getPackageManager();
            List<PackageInfo> list = pm.getInstalledPackages(0);
            for (int i = 0; i < list.size(); i++) {
                PackageInfo pi = list.get(i);
                if (pi != null && pi.packageName != null) {
                    this.installedPackages.put(pi.packageName, Integer.valueOf(pi.versionCode));
                }
            }
        } catch (Throwable th) {
        }
    }

    public int getInstalledVersionCode(String packageName) {
        Integer v = this.installedPackages.get(packageName);
        if (v == null) {
            return 0;
        }
        return v.intValue();
    }

    @Override // android.widget.Adapter
    public int getCount() {
        return this.items.size();
    }

    @Override // android.widget.Adapter
    public Object getItem(int position) {
        return this.items.get(position);
    }

    @Override // android.widget.Adapter
    public long getItemId(int position) {
        return this.items.get(position).id;
    }

    @Override // android.widget.Adapter
    public View getView(int position, View convertView, ViewGroup parent) {
        View v = convertView;
        if (v == null) {
            v = this.inf.inflate(R.layout.list_item_app, parent, false);
        }
        ImageView img = (ImageView) v.findViewById(R.id.img);
        TextView title = (TextView) v.findViewById(R.id.title);
        TextView developer = (TextView) v.findViewById(R.id.subtitle);
        TextView status = (TextView) v.findViewById(R.id.txtStatus);
        RatingBar ratingBar = (RatingBar) v.findViewById(R.id.ratingBar);
        AppItem a = this.items.get(position);
        title.setText(AppItem.safe(a.name));
        developer.setText(AppItem.safe(a.developer));
        ratingBar.setRating(a.rating);
        String packageName = AppItem.safe(a.packageName);
        boolean installed = packageName.length() > 0 && this.installedPackages.containsKey(packageName);
        int installedVersionCode = getInstalledVersionCode(packageName);
        a.installedVersionCode = installedVersionCode;
        if (installed && a.versionCode > 0 && installedVersionCode > 0 && a.versionCode > installedVersionCode) {
            status.setText(this.c.getString(R.string.updates_available));
            status.setTextColor(-881640);
        } else if (installed) {
            status.setText(this.c.getString(R.string.installed));
            status.setTextColor(-13619152);
        } else {
            status.setText(this.c.getString(R.string.free));
            status.setTextColor(-13619152);
        }
        String iconUrl = a.icon == null ? "" : Api.iconUrl(this.c, a.icon);
        ImageLoader.load(this.c, iconUrl, img, R.drawable.icon_placeholder);
        return v;
    }
}
