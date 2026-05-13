#!/usr/bin/env python3
"""
Auto-match columns for bulk upload
Detects uploaded file columns and matches them to expected columns
"""
import pandas as pd

def normalize_col(name):
    """Normalize column name for matching"""
    import re
    name = name.lower().strip()
    name = re.sub(r'[\s\-_]+', '', name)
    return name

def auto_match_columns(uploaded_df, expected_columns):
    """
    Auto-match uploaded columns to expected columns.
    Returns dict: {expected_col: uploaded_col_or_None}
    """
    uploaded_cols = list(uploaded_df.columns)
    norm_uploaded = {normalize_col(c): c for c in uploaded_cols}
    
    matched = {}
    for exp_col in expected_columns:
        norm_exp = normalize_col(exp_col)
        if norm_exp in norm_uploaded:
            matched[exp_col] = norm_uploaded[norm_exp]
        else:
            matched[exp_col] = None
    
    return matched

def get_upload_preview(df, col_mapping, expected_cols):
    """Show preview of how data will be mapped"""
    preview_data = {}
    for exp_col in expected_cols:
        upl_col = col_mapping.get(exp_col)
        if upl_col and upl_col in df.columns:
            preview_data[exp_col] = df[upl_col].head(3).tolist()
        else:
            preview_data[exp_col] = ['(missing)']
    return pd.DataFrame(preview_data)

if __name__ == '__main__':
    # Test
    sample_upload = pd.DataFrame({
        'SKU': ['EODA19H-2436', 'EAHDEN-24'],
        'Model': ['EODA19H-2436ABA', 'EAHDEN-24'],
        'Price': [7900, 4222.5],
        'Notes': ['', '']
    })
    
    expected = ['sku', 'model_number', 'list_price', 'notes']
    mapping = auto_match_columns(sample_upload, expected)
    print("Auto-match result:")
    for k, v in mapping.items():
        print(f"  {k} <- {v}")
    
    print("\nPreview:")
    preview = get_upload_preview(sample_upload, mapping, expected)
    print(preview)