# HYDRUS-1D–Python crop rotation coupling

A configurable Python workflow for sequential HYDRUS-1D simulations of crop rotations. Independent single-solute runs cover Pb, Cd, Zn, Ni, Mn and P; the nitrogen workflow carries NH4 and NO3 together using a separate HYDRUS project template. The final nodal state of each period initializes the next period.

## Installation
Install HYDRUS-1D separately on Windows and use Python 3.10 or later.

```sh
python -m pip install -r requirements.txt
```

## Input structure
Provide separate roots for elements and nitrogen. Each root contains `Crop_A`, `Crop_B` (and `Crop_C` if needed), with complete HYDRUS projects, and an `Assets` directory. No experimental data or proprietary executables are distributed.

- `Assets/Concentration.xlsx`: sheets named after crop IDs; columns named after solutes; one row per atmospheric record.
- `Assets/Init_Conc.xlsx`: crop sheets, columns `moisture` and solute names; one row per node.
- `Assets/Elements_Para.xlsx`: crop sheets, solute columns; nine parameter rows in the original notebook order (elements mode only).
- Crop boundary workbooks: names specified in configuration; sheets named `1`, `2`, etc.; first four columns match the atmospheric input fields in the original notebooks.

Use consistent HYDRUS units throughout. The moisture field retains the original notebook's nodal field mapping; ensure the template initial-condition convention matches it.

## Run
```sh
python simulate.py --config configs/farm1.json --mode both --hydrus "C:/path/H1D_CALC.EXE" --elements-root "C:/projects/F1" --nitrogen-root "C:/projects/F1_N" --output results
```
Use `--mode elements` or `--mode nitrogen` to run only one workflow. Use a new output directory for each run. Outputs are organized by mode, solute, year and crop period.

## Adapt to your research
Edit a JSON configuration: crop IDs, template directories, workbook names, annual crop sequence, atmospheric row counts, solutes, timeout, and file layout. Farm 1 uses A/B for ten years; Farm 2 uses A/C in years 1, 5 and 9 and B/C otherwise; Farm 3 uses A/B for five years. Crop names are not established by the notebooks, so letter IDs are retained. Layout indices are zero-based and specific to the original HYDRUS project format. Adjust them for other project layouts, mesh sizes and output schedules. The output block must correspond to the end of the crop period. Nitrogen reaction parameters are defined in the nitrogen templates.

## Notes
The script waits for the executable to finish rather than terminating it after a fixed sleep. It applies element parameters to every crop, including Farm 2 crop B (not explicitly updated in the original loop), and assumes the Farm 1 nitrogen Crop_B template is separate from Crop_A, correcting the duplicate path in the notebook. These are deliberate behavior changes. The supplied configuration reproduces the notebook row mappings, not a universal HYDRUS parser.