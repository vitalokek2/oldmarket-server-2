package com.oldmarket.model;

/* JADX INFO: loaded from: classes.dex */
public class CategoryItem {
    public String code;
    public String label;

    public CategoryItem() {
    }

    public CategoryItem(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String toString() {
        return this.label == null ? "" : this.label;
    }
}
