import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import nibabel as nib
import numpy as np
import polars as pl
import pyarrow as pa

from ..constants import CHUNK_SIZE
from ..file_operations.io import process_and_write_chunk


def collect_data_to_csv(
    adnimerge_csv: Path,
    bids_df: pl.DataFrame,
    phases: List[str],
    valid_dx: List[str],
    suffix: str,
    trc: str,
    rec: str,
    desc: str,
    res: str,
) -> pl.DataFrame:
    logging.info("Collecting and processing data")
    adnimerge_df = pl.scan_csv(str(adnimerge_csv))

    filter_conditions = [
        (pl.col("suffix") == suffix),
        (pl.col("extension") == "nii.gz"),
        (pl.col("path").str.contains("derivatives")),
    ]

    if suffix == "pet":
        filter_conditions.extend(
            [
                (pl.col("desc") == desc),
                (pl.col("res") == res),
                (pl.col("tracer") == trc),
                (pl.col("reconstruction") == rec),
            ]
        )
    else:
        filter_conditions.extend(
            [(pl.col("desc") == "Crop"), (pl.col("res") == "1x1x1")]
        )

    dataset_df = bids_df.filter(pl.all(filter_conditions))

    # Extract ptid and session from filename
    dataset_df = dataset_df.with_columns(
        [
            pl.col("filename")
            .str.extract(r"(sub-[A-Z0-9]+)_(ses-[A-Za-z][0-9]+)")
            .alias("extracted"),
            pl.col("path"),
        ]
    )

    dataset_df = dataset_df.with_columns(
        [
            pl.col("extracted").struct.field("field_0").alias("ptid"),
            pl.col("extracted").struct.field("field_1").alias("session"),
        ]
    )

    dataset_df = dataset_df.with_columns(
        [pl.col("ptid").str.replace(r"^sub-ADNI(\d{3})([A-Za-z])(\d{4})$", r"\1_\2_\3")]
    )

    # Process adnimerge_df
    adnimerge_df = (
        adnimerge_df.select(
            pl.col("COLPROT").alias("phase"),
            ptid=pl.col("PTID").str.replace(
                r"^sub-ADNI(\d{3})([A-Za-z])(\d{4})$", r"\1_\2_\3"
            ),
            session=pl.when(pl.col("VISCODE") == "bl")
            .then(pl.lit("ses-M000"))
            .otherwise(
                pl.lit("ses-M")
                + pl.col("VISCODE").str.strip_prefix("m").str.pad_start(3, "0")
            ),
            dx=pl.col("DX").str.strip_chars().str.to_lowercase(),
        )
        .filter(pl.col("phase").is_in(phases))
        .filter(pl.col("dx").is_in(valid_dx))
        .collect()
    )

    dataset_df = dataset_df.join(adnimerge_df, on=["ptid", "session"], how="inner")
    logging.info(f"Collected {len(dataset_df)} rows of data")
    return dataset_df


def split_train_val_test(
    df: pl.DataFrame, train_fraction: float, val_fraction: float
) -> Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    logging.info("Splitting data into train, validation, and test sets")
    if not 0.5 < train_fraction + val_fraction < 1:
        raise ValueError(
            "Invalid split fractions. Must sum to less than 1 and more than 0.5"
        )

    df_agg = df.select(pl.col("ptid")).unique()
    n_rows = df_agg.select(pl.len()).item()

    train_len = round(n_rows * train_fraction)
    val_len = round(n_rows * val_fraction)

    df_agg = df_agg.select(pl.col("ptid").shuffle(seed=22))

    df_train = df.join(
        df_agg.slice(0, train_len), on="ptid", how="inner", validate="m:1"
    )
    df_val = df.unique(subset=["ptid"]).join(
        df_agg.slice(train_len, val_len), on="ptid", how="inner", validate="1:1"
    )
    df_test = df.unique(subset=["ptid"]).join(
        df_agg.slice(train_len + val_len), on="ptid", how="inner", validate="1:1"
    )

    logging.info(
        f"Split sizes: Train={len(df_train)}, Val={len(df_val)}, Test={len(df_test)}"
    )
    return df_train, df_val, df_test


def read_nifti_file(filepath: str) -> np.ndarray:
    scan = nib.load(filepath)
    scan = scan.get_fdata()
    return scan


def process_scan(path: str) -> np.ndarray:
    volume = read_nifti_file(path)
    volume = np.expand_dims(volume, axis=-1)
    volume = volume.astype(np.float32) / 255.0
    return np.array(volume)


def flatten(arr: np.ndarray) -> np.ndarray:
    return np.reshape(arr, [-1])


def process_and_write_column(
    table: pa.Table, output_path: Path, n_proc: int, chunk_size: int
) -> None:
    raw_col = table.column(0)
    dx_col = table.column(1)

    raw_chunks = [
        raw_col[i : (i + chunk_size)] for i in range(0, table.num_rows, chunk_size)
    ]
    dx_chunks = [
        dx_col[i : (i + chunk_size)] for i in range(0, table.num_rows, chunk_size)
    ]

    logging.info(
        f"Processing {len(raw_chunks)} chunks {'with ' + str(n_proc) + ' processes' if n_proc > 1 else 'in single-thread mode'}"
    )

    if n_proc > 1:
        with ProcessPoolExecutor(max_workers=n_proc) as executor:
            futures = [
                executor.submit(
                    process_and_write_chunk, index, raw_chunk, dx_chunk, output_path
                )
                for index, (raw_chunk, dx_chunk) in enumerate(
                    zip(raw_chunks, dx_chunks)
                )
            ]
            for future in as_completed(futures):
                future.result()
    else:
        for index, (raw_chunk, dx_chunk) in enumerate(zip(raw_chunks, dx_chunks)):
            process_and_write_chunk(index, raw_chunk, dx_chunk, output_path)


def process_paths(df: pl.DataFrame, output_path: Path, n_proc: int) -> None:
    table = df.select(pl.col("path"), pl.col("dx")).to_arrow()
    process_and_write_column(table, Path(output_path), n_proc, CHUNK_SIZE)
