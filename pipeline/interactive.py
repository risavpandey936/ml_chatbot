import os
import sys
from pipeline.eda import read_dataset, run_eda
from pipeline.train import train
from pipeline.hypothesis import hypothesis


def prompt_choice(prompt, choices):
    for i, c in enumerate(choices, 1):
        print(f"{i}. {c}")
    while True:
        v = input(prompt + ' ')
        if v.isdigit():
            idx = int(v) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        # allow exact match
        if v in choices:
            return v
        print('Invalid selection, try again.')


def select_column(columns, prompt_text='Select column'):
    print('\nColumns:')
    for i, c in enumerate(columns, 1):
        print(f"{i}. {c}")
    while True:
        v = input(prompt_text + ' (number or name): ')
        if v.isdigit():
            idx = int(v) - 1
            if 0 <= idx < len(columns):
                return columns[idx]
        if v in columns:
            return v
        print('Invalid column, try again.')


def interactive_loop():
    path = input('Path to dataset (CSV or Parquet): ').strip()
    if not path:
        print('No path provided; exiting.')
        return
    if not os.path.exists(path):
        print('File not found:', path)
        return

    df = read_dataset(path)
    columns = list(df.columns)
    print('\nDataset loaded:', path)
    print('Rows,Cols:', df.shape)

    while True:
        print('\nWhat would you like to do?')
        action = prompt_choice('Choose action:', ['EDA', 'Train model', 'Hypothesis test', 'View dashboard', 'Exit'])

        if action == 'EDA':
            out = input('Write EDA output JSON file? (path or leave empty): ').strip() or None
            run_eda(path, out_json=out)

        elif action == 'Train model':
            target = select_column(columns, 'Which column should be the target?')
            model_type = prompt_choice('Model type:', ['auto', 'regression', 'classification'])
            # missing value handling
            impute_choice = prompt_choice('Missing value handling:', ['none', 'drop', 'mean', 'median', 'mode', 'constant'])
            impute_const = None
            if impute_choice == 'constant':
                v = input('Enter constant value (numeric): ').strip()
                try:
                    impute_const = float(v)
                except Exception:
                    print('Invalid number, using 0')
                    impute_const = 0.0
            # outlier handling
            outlier_choice = prompt_choice('Outlier removal:', ['none', 'iqr', 'zscore'])
            outlier_thresh = None
            if outlier_choice == 'iqr':
                v = input('IQR multiplier (default 1.5): ').strip() or '1.5'
                outlier_thresh = float(v)
            elif outlier_choice == 'zscore':
                v = input('Z-score threshold (default 3.0): ').strip() or '3.0'
                outlier_thresh = float(v)

            out_model = input('Save model to (joblib path) or leave empty: ').strip() or None
            print('Training...')
            res = train(path, target, model_type=model_type, out_model=out_model, impute=impute_choice, impute_const=impute_const, outlier_method=outlier_choice, outlier_thresh=outlier_thresh)
            print('\nTrain result:')
            print(res)

        elif action == 'Hypothesis test':
            col = select_column(columns, 'Which column do you want to test?')
            test = prompt_choice('Test to run:', ['ttest', 'shapiro'])
            group_col = None
            if test == 'ttest':
                group_col = select_column(columns, 'Which group column (must have 2 groups)?')
            print('Running hypothesis test...')
            res = hypothesis(path, col, test=test, group_column=group_col)
            print('\nResult:')
            print(res)
        elif action == 'View dashboard':
            out = input('Output HTML path (default dashboard.html): ').strip() or 'dashboard.html'
            open_now = prompt_choice('Open in browser now?', ['yes', 'no'])
            from pipeline.dashboard import make_dashboard
            print('Generating dashboard...')
            make_dashboard(path, out_html=out, open_browser=(open_now == 'yes'))

        else:  # Exit
            print('Goodbye')
            break


if __name__ == '__main__':
    interactive_loop()
