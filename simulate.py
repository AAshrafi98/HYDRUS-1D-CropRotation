"""Run sequential HYDRUS-1D crop periods with state transfer between periods."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
import pandas as pd

def workbook(path):
    """Read all Excel sheets"""
    return pd.read_excel(path, sheet_name=None)

def edit_rows(path, start, rows):
    """Replace selected fields; start and column indices are zero-based."""
    lines = path.read_text().splitlines(keepends=True)
    for i, changes in enumerate(rows, start):
        fields = lines[i].split()
        for col, value in changes.items():
            if pd.isna(value):
                raise ValueError(f'Missing value in {path}, row {i+1}, column {col+1}')
            fields[col] = str(value)
        lines[i] = ' '.join(fields) + '\n'
    path.write_text(''.join(lines))

def run(config, mode, executable, root, output):
    """Each solute group has its own independent sequence of crop simulations."""
    assets = root / 'Assets'
    concentrations = workbook(assets / 'Concentration.xlsx')
    initial = workbook(assets / 'Init_Conc.xlsx')
    parameters = workbook(assets / 'Elements_Para.xlsx') if mode == 'elements' else None
    boundary = {crop: workbook(assets / filename) for crop, filename in config['boundary_files'].items()}
    groups = [(s, [s]) for s in config['elements']] if mode == 'elements' else [('N', ['NH4', 'NO3'])]
    layout = config['layout']
    nodes = layout['nodes']
    profile_start = layout['profile_start']
    profile_cols = layout['profile_columns'][mode]
    output_cols = layout['output_columns'][mode]
    atmospheric_cols = layout['atmospheric_columns'][mode]
    for label, species in groups:
        state = None
        for year, periods in enumerate(config['rotation'], 1):
            for period, entry in enumerate(periods, 1):
                crop, count = entry['crop'], entry['atmospheric_rows']
                # Copy a fresh template for every period; never modify source projects.
                work = output / mode / label / f'year_{year:02d}' / f'{period:02d}_{crop}'
                shutil.copytree(root / config['crop_templates'][crop], work,
                                ignore=shutil.ignore_patterns('*.out', '*.OUT'))
                if state is None:
                    table = initial[crop]
                    state = table[['moisture', *species]].iloc[:nodes].values.tolist()
                    if len(state) != nodes:
                        raise ValueError('Initial profile does not match configured node count')
                edit_rows(work / 'PROFILE.DAT', profile_start,
                          [dict(zip(profile_cols, row)) for row in state])
                # Single-species transport parameters; nitrogen reactions remain in its template.
                if parameters is not None:
                    values = parameters[crop][label]
                    for line, mapping in layout['selector_rows'].items():
                        edit_rows(work / 'SELECTOR.IN', int(line),
                                  [{int(col): values.iloc[index] for col, index in mapping.items()}])
                weather = boundary[crop][str(year)]
                chemistry = concentrations[crop]
                if min(len(weather), len(chemistry)) < count:
                    raise ValueError(f'Insufficient boundary rows for {crop}, year {year}')
                edit_rows(work / 'ATMOSPH.IN', layout['atmospheric_start'], [
                    {**dict(enumerate(weather.iloc[i, :4])),
                     **dict(zip(atmospheric_cols, chemistry.loc[i, species]))}
                    for i in range(count)])
                print(f'{mode}: {label}, year {year}, crop {crop}', flush=True)
                subprocess.run([str(executable), str(work.resolve())], check=True,
                               timeout=config['timeout_seconds'])
                # Use the same output block and fields as the original notebooks.
                lines = (work / 'Nod_Inf.out').read_text().splitlines()
                start = layout['output_start']
                state = [[lines[i].split()[col] for col in output_cols]
                         for i in range(start, start + nodes)]
                # Ensure the transferred fields are numeric before the next crop.
                for row in state:
                    for value in row:
                        float(value)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--mode', choices=['elements', 'nitrogen', 'both'], default='both')
    parser.add_argument('--hydrus', type=Path, required=True, help='Path to H1D_CALC.EXE')
    parser.add_argument('--elements-root', type=Path, help='Folder containing elements projects and Assets')
    parser.add_argument('--nitrogen-root', type=Path, help='Folder containing nitrogen projects and Assets')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    modes = ['elements', 'nitrogen'] if args.mode == 'both' else [args.mode]
    for mode in modes:
        root = getattr(args, mode + '_root')
        if root is None:
            parser.error(f'--{mode}-root is required for {mode} mode')
        run(config, mode, args.hydrus.resolve(), root.resolve(), args.output.resolve())

if __name__ == '__main__':
    main()