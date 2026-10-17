# Data: not committed

The challenge data is sponsor data from the eMerge Hackathon Challenge 1 release. It is **not** in this repo, and `.gitignore` keeps it out.
Put copies here before running `scripts/reproduce.sh`. Treat the files as untrusted input: the scripts only read them (`python -I`), and nothing in `data/` is executed.

## Where it comes from

The organisers' Challenge 1 release (we received it as `Challenge_1/`, with `meps.zip`, `synthea.zip`, `README.md`,
`eMerge_Hackathon_Challenge_1_Guide.md` and `baseline_model.py`). Ask the organisers for access; it is not on a public URL.
`analysis/baseline_reference.py` is the release's `baseline_model.py`, byte for byte.

| release file | bytes | sha256 |
|---|---|---|
| `meps.zip` | 79,248 | `1a5da0e18b3b2f0bc1adf0141c7173a2ba83393673a2e5b221d4cb44f8526d2e` |
| `synthea.zip` | 34,074,978 | `d6fd85c48b3116d48d7dc6260e64bfc20f65b4aae54dc35d178a3064f5c0a2c4` |
| `baseline_model.py` | | `65101ef8b2b802f6da83e9694b762a493f05161c517a05d9b56f161b4e628ed2` |

The MEPS extract is built from the public AHRQ Medical Expenditure Panel Survey (2017 and 2018 full-year files, https://meps.ahrq.gov),
filtered and recoded by the organisers. Synthea (https://synthetichealth.github.io/synthea/) is synthetic patient data; the release contains the generated CSVs, so you do not run Synthea.
No other public data is used.

Committed outputs include per-person out-of-fold predictions keyed by MEPS public-use IDs (`analysis/out/oof.csv`, `runs/autoresearch/*-oof.csv`); no re-identification, per the MEPS use terms.

## Layout

```bash
mkdir -p data && unzip -q path/to/Challenge_1/meps.zip -d data && unzip -q path/to/Challenge_1/synthea.zip -d data
(cd data && shasum -a 256 -c SHA256SUMS)   # every line must say OK (on Linux: sha256sum -c)
```

`data/SHA256SUMS` (committed) lists the 13 files the code reads. The zip also holds 9 Synthea files we do not use
(allergies, careplans, claims, devices, imaging_studies, immunizations, organizations, providers, supplies); they may stay.

| file | bytes | used by |
|---|---|---|
| `meps/meps2017_survivors.csv` | 531,379 | all steps: 2017 predictors (the only file that feeds the model) |
| `meps/meps2018_followup_dev.csv` | 31,513 | `ID` and `outcome_acute_care_2018` only (it reuses 2017 column names for 2018 measures) |
| `meps/heldout_ids.csv` | 2,207 | the 199 held-out IDs, in submission order |
| `meps/meps2017_variables.csv`, `meps/meps2018_variables.csv` | 7,224 / 847 | codebooks (read by people, not code) |
| `synthea/patients.csv`, `conditions.csv`, `encounters.csv`, `medications.csv`, `observations.csv`, `procedures.csv`, `payers.csv`, `payer_transitions.csv` | 538 MB in all | `analysis/synthea.py`, and the Synthea-prior candidate in `analysis/autoresearch.py 3` |
