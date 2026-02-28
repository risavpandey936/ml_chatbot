import argparse
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score, f1_score, mean_squared_error
import numpy as np


def read_dataset(path):
    if path.endswith('.parquet') or path.endswith('.pq'):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _impute_df(df, strategy, const_value=None):
    if strategy is None or strategy == 'none':
        return df
    df = df.copy()
    if strategy == 'drop':
        return df.dropna()
    numeric = df.select_dtypes(include=['number']).columns
    if strategy == 'mean':
        df[numeric] = df[numeric].fillna(df[numeric].mean())
    elif strategy == 'median':
        df[numeric] = df[numeric].fillna(df[numeric].median())
    elif strategy == 'mode':
        for c in df.columns:
            df[c] = df[c].fillna(df[c].mode().iloc[0] if not df[c].mode().empty else df[c].fillna(0))
    elif strategy == 'constant':
        df = df.fillna(const_value)
    return df


def _remove_outliers(X, y, method='none', thresh=1.5):
    if method is None or method == 'none':
        return X, y
    X = X.copy()
    if method == 'iqr':
        mask = np.ones(len(X), dtype=bool)
        for c in X.columns:
            q1 = X[c].quantile(0.25)
            q3 = X[c].quantile(0.75)
            iqr = q3 - q1
            low = q1 - thresh * iqr
            high = q3 + thresh * iqr
            mask &= X[c].between(low, high)
        removed = (~mask).sum()
        return X.loc[mask].reset_index(drop=True), y.loc[mask].reset_index(drop=True)
    elif method == 'zscore':
        from scipy import stats as _stats
        zs = _stats.zscore(X.fillna(0))
        if zs.ndim == 1:
            mask = np.abs(zs) <= thresh
        else:
            mask = (np.abs(zs) <= thresh).all(axis=1)
        return X.loc[mask].reset_index(drop=True), y.loc[mask].reset_index(drop=True)
    return X, y


def train(path, target, model_type='auto', out_model=None, impute=None, impute_const=None, outlier_method=None, outlier_thresh=None):
    df = read_dataset(path)
    if impute:
        df = _impute_df(df, impute, const_value=impute_const)
    if target not in df.columns:
        raise SystemExit(f'Target column {target} not found in dataset')

    X = df.drop(columns=[target]).select_dtypes(include=['number'])
    # after imputation there may be no NaNs, otherwise fill remaining numeric NaNs with 0
    X = X.fillna(0)
    y = df[target]
    if X.shape[1] == 0:
        raise SystemExit('No numeric features found for training')

    # outlier removal (operate on X and y)
    if outlier_method and outlier_method != 'none':
        prev_n = len(X)
        X, y = _remove_outliers(X, y, method=outlier_method, thresh=(outlier_thresh or 1.5))
        print(f'Removed {prev_n - len(X)} outlier rows using {outlier_method}')

    if model_type == 'auto':
        if pd.api.types.is_numeric_dtype(y):
            task = 'regression'
            model = LinearRegression()
        else:
            task = 'classification'
            model = LogisticRegression(max_iter=1000)
    else:
        if model_type == 'regression':
            task = 'regression'
            model = LinearRegression()
        else:
            task = 'classification'
            model = LogisticRegression(max_iter=1000)

    label_encoder = None
    if task == 'classification' and not pd.api.types.is_numeric_dtype(y):
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(y.astype(str))

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = make_pipeline(StandardScaler(), model)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)

    res = {'task': task}
    if task == 'classification':
        try:
            preds_int = np.round(preds).astype(int)
        except Exception:
            preds_int = preds
        res.update({
            'accuracy': float(accuracy_score(y_test, preds_int)),
            'f1_weighted': float(f1_score(y_test, preds_int, average='weighted'))
        })
    else:
        mse = mean_squared_error(y_test, preds)
        res.update({
            'r2': float(r2_score(y_test, preds)),
            'rmse': float(np.sqrt(mse))
        })

    if out_model:
        joblib.dump({'pipeline': clf, 'label_encoder': label_encoder}, out_model)
        res['model_path'] = out_model

    return res


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Train a simple model on a dataset')
    p.add_argument('path')
    p.add_argument('--target', required=True)
    p.add_argument('--model-type', default='auto', choices=['auto','regression','classification'])
    p.add_argument('--out-model', help='Path to save model (joblib)')
    p.add_argument('--impute', default='none', choices=['none','drop','mean','median','mode','constant'], help='Missing value handling')
    p.add_argument('--impute-const', type=float, help='Constant value to use with --impute constant')
    p.add_argument('--outlier-method', default='none', choices=['none','iqr','zscore'], help='Outlier removal method')
    p.add_argument('--outlier-thresh', type=float, help='Threshold for outlier method (IQR multiplier or z-score)')
    args = p.parse_args()
    result = train(args.path, args.target, args.model_type, args.out_model, impute=args.impute, impute_const=args.impute_const, outlier_method=args.outlier_method, outlier_thresh=args.outlier_thresh)
    print('Training result:')
    print(result)
