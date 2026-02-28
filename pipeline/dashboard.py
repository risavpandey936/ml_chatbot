import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import os
import webbrowser
def read_dataset(path):
    if path.endswith('.parquet') or path.endswith('.pq'):
        return pd.read_parquet(path)
    return pd.read_csv(path)
def make_dashboard(path, out_html='dashboard.html', max_numeric=6, max_categorical=6, open_browser=True):
    df = read_dataset(path)
    figs = []

    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(exclude=['number']).columns.tolist()

    # Numeric histograms (limit)
    for c in num_cols[:max_numeric]:
        fig = px.histogram(df, x=c, nbins=40, title=f'Histogram: {c}')
        figs.append(fig)

    # Categorical top-values bar charts
    for c in cat_cols[:max_categorical]:
        top = df[c].value_counts(dropna=False).nlargest(10)
        fig = go.Figure([go.Bar(x=top.index.astype(str), y=top.values)])
        fig.update_layout(title=f'Top values: {c}', xaxis_title=c, yaxis_title='count')
        figs.append(fig)

    # Missing values
    miss = df.isnull().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    if len(miss):
        fig = go.Figure([go.Bar(x=miss.index.astype(str), y=miss.values)])
        fig.update_layout(title='Missing values by column', xaxis_title='column', yaxis_title='missing_count')
        figs.append(fig)

    # Correlation heatmap for numeric cols
    if len(num_cols) > 1:
        corr = df[num_cols].corr()
        fig = px.imshow(corr, text_auto=True, aspect='auto', title='Correlation matrix')
        figs.append(fig)

    # Build single HTML with all figures
    html_parts = []
    for fig in figs:
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs='cdn'))

    html_body = "\n<hr/\n".join(html_parts)
    html = f"<html><head><meta charset='utf-8'><title>Dataset Dashboard</title></head><body><h1>Dashboard for {os.path.basename(path)}</h1>{html_body}</body></html>"

    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Dashboard written to: {out_html}')
    if open_browser:
        webbrowser.open('file://' + os.path.abspath(out_html))

    return out_html


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Generate an HTML dashboard for a dataset')
    p.add_argument('path')
    p.add_argument('--out', default='dashboard.html')
    p.add_argument('--no-open', dest='open_browser', action='store_false')
    args = p.parse_args()
    make_dashboard(args.path, out_html=args.out, open_browser=args.open_browser)
