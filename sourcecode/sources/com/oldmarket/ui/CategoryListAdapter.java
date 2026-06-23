package com.oldmarket.ui;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.TextView;
import com.oldmarket.R;
import java.util.List;

/* JADX INFO: loaded from: classes.dex */
public class CategoryListAdapter extends BaseAdapter {
    private final LayoutInflater inflater;
    private final List<String> items;

    public CategoryListAdapter(Context context, List<String> items) {
        this.items = items;
        this.inflater = LayoutInflater.from(context);
    }

    @Override // android.widget.Adapter
    public int getCount() {
        if (this.items == null) {
            return 0;
        }
        return this.items.size();
    }

    @Override // android.widget.Adapter
    public Object getItem(int position) {
        return this.items.get(position);
    }

    @Override // android.widget.Adapter
    public long getItemId(int position) {
        return position;
    }

    @Override // android.widget.Adapter
    public View getView(int position, View convertView, ViewGroup parent) {
        View v = convertView;
        if (v == null) {
            v = this.inflater.inflate(R.layout.list_item_category, parent, false);
        }
        TextView text1 = (TextView) v.findViewById(R.id.text1);
        text1.setText(this.items.get(position));
        return v;
    }
}
