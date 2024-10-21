from pathlib import Path
import re
from bids.layout import BIDSLayout
import polars as pl


def read_bids_layout(raw_path: str) -> BIDSLayout | None:
    """Initializes BIDSLayout with raw and preprocessed datasets."""
    print(f"Reading BIDS-layout from {raw_path}...", end="", flush=True)
    try:
        layout = BIDSLayout(raw_path)
        print("ok")
        print(layout, "\n")
        return layout
    except Exception as e:
        print("\n\n >>> Something went wrong! <<<\n\n", e)

def bids_to_df(adnimerge_csv: Path, layout: BIDSLayout, phases: list, valid_dx: list, trc: str, suffix: str, rec: str) -> pl.DataFrame:
    adnimerge_df = pl.scan_csv(str(adnimerge_csv))
    if suffix == "pet":
        bids_list = layout.get(tracer=trc, suffix=suffix, reconstruction=rec, invalid_filters="allow") 
    else:
        bids_list = layout.get(suffix=suffix)

    bids_included_df = pl.DataFrame()
    _ = valid_dx

    for bids_file in bids_list:
        match = re.match(r"(sub-[A-Z0-9]+)_(ses-[A-Za-z][0-9]+)", bids_file.filename)
        if match is None:
            raise ValueError
        ptid = match.group(1)
        session_id = match.group(2)
        bids_included_df = bids_included_df.vstack(pl.DataFrame({"participant_id": ptid, "session_id": session_id}))
    bids_included_df.rechunk()

    adnimerge_df = adnimerge_df.select(
        pl.col("COLPROT").alias("phase"), 
        participant_id=pl.col("PTID").str.replace_all(r"(\d+)_(S)_(\d+)", "sub-ADNI${1}${2}${3}"),
        session_id=pl.when(pl.col("VISCODE") == "bl")
        .then(pl.lit("ses-M000"))
        .otherwise(pl.lit("ses-M") + pl.col("VISCODE").str.strip_prefix("m").str.pad_start(3, "0"))
    ).filter(pl.col("phase").is_in(phases)).collect()

    bids_included_df = bids_included_df.join(adnimerge_df, on=["participant_id", "session_id"], how="semi")

    return bids_included_df


def write_df_to_tsv(df: pl.DataFrame, file: Path) -> None:
    """Write polars dataframe to tsv-file"""
    try:
        with file.open('w') as f:
            df.write_csv(f, separator='\t')
    except IOError as e:
        print(f"Error writing to file: {e}")


if __name__ == "__main__":
    DEBUG = False

    afile = "/home/espen/forskningsdata/adni/clinical/ADNIMERGE_23Apr2024.csv"
    phases = [ "ADNI1", "ADNI2", "ADNI3", "ADNI4", "ADNIGO" ]
    valid_dx = [ "cn", "mci", "dementia" ] # Not in use
    suffix="pet"
    trc="18FFDG"
    rec="coregiso"
    path = "/home/espen/forskningsdata/adni" + ("-dev" if DEBUG else "")

    bids_path = Path(path) / 'bids'
    output_dir = Path(path) / 'data'
    output_dir.mkdir(exist_ok=True)
    output_file = f"included_subjects_{suffix}.tsv"

    layout = read_bids_layout(str(bids_path))
    if layout is None:
        raise ValueError("Failed to read BIDS layout.")
    included_subjects_df = bids_to_df(Path(afile), layout, phases, valid_dx, trc, suffix, rec)
    write_df_to_tsv(included_subjects_df, Path(output_dir) / output_file)
    print(f"Data written to {Path(output_dir) / output_file}")
