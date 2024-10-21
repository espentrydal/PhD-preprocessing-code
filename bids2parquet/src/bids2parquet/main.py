import argparse
import logging
from pathlib import Path

from adni_processing.constants import VALID_SUFFIXES
from adni_processing.data_processing.processing import (
    collect_data_to_csv,
    process_paths,
    split_train_val_test,
)
from adni_processing.file_operations.io import read_bids_parquet, write_df_to_tsv

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main(args):
    bids_df = read_bids_parquet(args.parquet_path)

    dataset_df = collect_data_to_csv(
        Path(args.adnimerge_csv),
        bids_df,
        args.phases,
        args.valid_dx,
        args.suffix,
        args.trc,
        args.rec,
        args.desc,
        args.res,
    )

    write_df_to_tsv(dataset_df, Path(args.output_dir) / "dataset.tsv")

    splits = split_train_val_test(dataset_df, args.train_split, args.val_split)

    for split, name in zip(splits, ["train", "val", "test"]):
        dir = Path(args.output_dir) / name
        dir.mkdir(exist_ok=True)
        write_df_to_tsv(split, dir / f"dataset_{name}.tsv")
        logging.info(f"Processing {name} with {args.n_proc} threads...")
        process_paths(split, Path(args.output_dir) / name, args.n_proc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process BIDS data")
    parser.add_argument(
        "--parquet_path",
        type=Path,
        required=True,
        help="Path to BIDS layout parquet file",
    )
    parser.add_argument(
        "--adnimerge_csv", type=Path, required=True, help="Path to ADNIMERGE CSV file"
    )
    parser.add_argument(
        "--output_dir", type=Path, required=True, help="Output directory"
    )
    parser.add_argument(
        "--phases", nargs="+", default=["ADNI3"], help="Study phases to include"
    )
    parser.add_argument(
        "--valid_dx",
        nargs="+",
        default=["cn", "mci", "dementia"],
        help="Valid diagnoses",
    )
    parser.add_argument(
        "--suffix", choices=VALID_SUFFIXES, default="T1w", help="File suffix"
    )
    parser.add_argument(
        "--scan_params",
        nargs=4,
        default=["", "", "", ""],
        metavar=("trc", "rec", "desc", "res"),
        help="Scan parameters: tracer, reconstruction, description, resolution",
    )
    parser.add_argument(
        "--n_proc", type=int, default=8, help="Number of processes to use"
    )
    parser.add_argument(
        "--train_split", type=float, default=0.8, help="Fraction of data for training"
    )
    parser.add_argument(
        "--val_split", type=float, default=0.1, help="Fraction of data for validation"
    )

    args = parser.parse_args()
    args.trc, args.rec, args.desc, args.res = args.scan_params

    main(args)
