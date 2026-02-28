import argparse
import pandas as pd
from scipy import stats


def read_dataset(path):
    if path.endswith('.parquet') or path.endswith('.pq'):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def hypothesis(path, column, test='ttest', group_column=None):
    df = read_dataset(path)
    if column not in df.columns:
        raise SystemExit(f'Column {column} not found')

    series = df[column].dropna()

    if test == 'ttest':
        if not group_column or group_column not in df.columns:
            raise SystemExit('group_column required for t-test')
        groups = df[[group_column, column]].dropna().groupby(group_column)[column]
        if len(groups) != 2:
            raise SystemExit('t-test requires exactly 2 groups')
        g1, g2 = [g for _, g in groups]
        stat, p = stats.ttest_ind(g1, g2)
        return {'statistic': float(stat), 'pvalue': float(p)}
    elif test == 'shapiro':
        stat, p = stats.shapiro(series.sample(min(len(series), 5000)))
        return {'statistic': float(stat), 'pvalue': float(p)}
    else:
        raise SystemExit('Unknown test')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Run hypothesis tests on a dataset')
    p.add_argument('path')
    p.add_argument('--column', required=True)
    p.add_argument('--test', default='ttest', choices=['ttest','shapiro'])
    p.add_argument('--group-column')
    args = p.parse_args()
    res = hypothesis(args.path, args.column, args.test, args.group_column)
    print(res)
