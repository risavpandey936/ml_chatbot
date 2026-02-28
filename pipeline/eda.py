import argparse
import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


def read_dataset(path):
    if path.endswith('.parquet') or path.endswith('.pq'):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def run_eda(path, out_json=None, generate_plots=False, plots_outdir=None):
    df = read_dataset(path)
    info = {
        'shape': df.shape,
        'dtypes': df.dtypes.astype(str).to_dict(),
        'nulls': df.isnull().sum().to_dict(),
        'describe': df.describe(include='all').to_dict()
    }
    print('Shape:', info['shape'])
    print('\nColumns and dtypes:')
    for c, t in info['dtypes'].items():
        print(f'- {c}: {t} (nulls={info["nulls"].get(c,0)})')

    if out_json:
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(info, f, default=str, indent=2)
        print('\nEDA written to', out_json)

    if generate_plots:
        outdir = plots_outdir or os.path.join(os.path.dirname(__file__), 'plots')
        os.makedirs(outdir, exist_ok=True)
        saved = generate_plots(path, outdir)
        print(f'Plots saved to {outdir}: {len(saved)} files')
        return {'info': info, 'plots': saved}
    return {'info': info}


def _safe_fname(s):
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in s)


def generate_plots(path, out_dir=None, max_scatter_pairs=8):
    """Generate common EDA plots and save PNGs.

    Creates:
    - histogram and boxplot for each numeric column
    - countplot for categorical columns
    - correlation heatmap for numeric columns
    - scatter plots for top correlated numeric pairs

    Returns list of saved file paths.
    """
    df = read_dataset(path)
    out_dir = out_dir or os.path.join(os.path.dirname(__file__), 'plots')
    os.makedirs(out_dir, exist_ok=True)
    saved_files = []

    numeric = df.select_dtypes(include=['number']).columns.tolist()
    categorical = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()

    # Histograms and boxplots for numeric
    for col in numeric:
        try:
            plt.figure(figsize=(6, 4))
            sns.histplot(df[col].dropna(), kde=True)
            p = os.path.join(out_dir, f'hist_{_safe_fname(col)}.png')
            plt.title(f'Histogram: {col}')
            plt.tight_layout()
            plt.savefig(p)
            plt.close()
            saved_files.append(p)

            plt.figure(figsize=(6, 4))
            sns.boxplot(x=df[col].dropna())
            p = os.path.join(out_dir, f'box_{_safe_fname(col)}.png')
            plt.title(f'Boxplot: {col}')
            plt.tight_layout()
            plt.savefig(p)
            plt.close()
            saved_files.append(p)
        except Exception:
            plt.close()
            continue

    # Countplots for categorical (limit unique values)
    for col in categorical:
        try:
            top = df[col].fillna('___NA___').value_counts().nlargest(30)
            plt.figure(figsize=(6, min(6, 0.25 * len(top))))
            sns.barplot(x=top.values, y=top.index)
            p = os.path.join(out_dir, f'count_{_safe_fname(col)}.png')
            plt.title(f'Countplot: {col}')
            plt.tight_layout()
            plt.savefig(p)
            plt.close()
            saved_files.append(p)
        except Exception:
            plt.close()
            continue

    # Correlation heatmap for numeric columns
    if len(numeric) >= 2:
        try:
            corr = df[numeric].corr()
            plt.figure(figsize=(max(6, 0.5 * len(numeric)), max(6, 0.5 * len(numeric))))
            sns.heatmap(corr, annot=True, fmt='.2f', cmap='vlag', square=False)
            p = os.path.join(out_dir, 'heatmap_correlation.png')
            plt.title('Correlation heatmap')
            plt.tight_layout()
            plt.savefig(p)
            plt.close()
            saved_files.append(p)
        except Exception:
            plt.close()

    # Scatter plots for top correlated pairs
    if len(numeric) >= 2:
        try:
            corrabs = df[numeric].corr().abs()
            pairs = []
            for i, c1 in enumerate(corrabs.columns):
                for j, c2 in enumerate(corrabs.columns):
                    if j <= i:
                        continue
                    pairs.append((corrabs.loc[c1, c2], c1, c2))
            pairs.sort(reverse=True)
            for v, c1, c2 in pairs[:max_scatter_pairs]:
                try:
                    plt.figure(figsize=(6, 4))
                    sns.scatterplot(x=df[c1], y=df[c2])
                    p = os.path.join(out_dir, f'scatter_{_safe_fname(c1)}__{_safe_fname(c2)}.png')
                    plt.title(f'Scatter: {c1} vs {c2} (corr={v:.2f})')
                    plt.tight_layout()
                    plt.savefig(p)
                    plt.close()
                    saved_files.append(p)
                except Exception:
                    plt.close()
                    continue
        except Exception:
            pass

    return saved_files


def generate_single_plot(path, plot_type, col1, col2=None, out_dir=None):
    df = read_dataset(path)
    out_dir = out_dir or os.path.join(os.path.dirname(__file__), 'plots')
    os.makedirs(out_dir, exist_ok=True)
    
    import uuid
    file_name = f'custom_{plot_type}_{_safe_fname(col1)}_{uuid.uuid4().hex[:6]}.png'
    if col2:
        file_name = f'custom_{plot_type}_{_safe_fname(col1)}_{_safe_fname(col2)}_{uuid.uuid4().hex[:6]}.png'
        
    p = os.path.join(out_dir, file_name)
    plt.figure(figsize=(6, 4))
    
    try:
        if plot_type == 'hist':
            sns.histplot(df[col1].dropna(), kde=True)
            plt.title(f'Histogram: {col1}')
        elif plot_type == 'kde':
            sns.kdeplot(df[col1].dropna(), fill=True)
            plt.title(f'KDE Plot: {col1}')
        elif plot_type == 'cdf':
            sns.ecdfplot(df[col1].dropna())
            plt.title(f'CDF Plot: {col1}')
        elif plot_type == 'box':
            sns.boxplot(x=df[col1].dropna())
            plt.title(f'Boxplot: {col1}')
        elif plot_type == 'count':
            top = df[col1].fillna('___NA___').value_counts().nlargest(30)
            sns.barplot(x=top.values, y=top.index)
            plt.title(f'Countplot: {col1}')
        elif plot_type == 'scatter' and col2:
            sns.scatterplot(x=df[col1], y=df[col2])
            plt.title(f'Scatter: {col1} vs {col2}')
        else:
            plt.close()
            return None
            
        plt.tight_layout()
        plt.savefig(p)
        plt.close()
        return p
    except Exception as e:
        print(f"Plot generation error: {e}")
        plt.close()
        return None


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Run EDA on a dataset (CSV or Parquet)')
    p.add_argument('path')
    p.add_argument('--out', dest='out_json', help='Write EDA JSON output')
    args = p.parse_args()
    run_eda(args.path, args.out_json)
