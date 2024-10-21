import logging
from pathlib import Path
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

def read_bids_parquet(parquet_path: Path) -> pl.DataFrame:
    logging.info(f"Reading BIDS-layout from {parquet_path}")
    try:
        df = pl.read_parquet(parquet_path)
        if df.is_empty():
            raise ValueError("Parquet file is empty")
        logging.info(f"Successfully read {len(df)} rows from parquet file")
        return df
    except Exception as e:
        logging.error(f"Error reading parquet file: {e}")
        raise

def write_df_to_tsv(df: pl.DataFrame, file: Path) -> None:
    logging.info(f"Writing DataFrame to {file}")
    with file.open("w") as f:
        df.write_csv(f, separator="\t")
    logging.info(f"Successfully wrote {len(df)} rows to {file}")

def process_and_write_chunk(
    index: int, raw_chunk: pa.ChunkedArray, dx_chunk: pa.ChunkedArray, output_path: Path
) -> None:
    from ..data_processing.processing import process_scan, flatten

    processed_scans = []
    dxs = []

    for scan, dx in zip(raw_chunk, dx_chunk):
        arr = process_scan(scan.as_py())
        arr = flatten(arr)
        tensor_array = arr

        processed_scans.append(tensor_array)
        dxs.append(dx)

    schema = pa.schema([("raw", pa.list_(pa.float32())), ("dx", pa.large_string())])
    table = pa.table([processed_scans, dxs], schema=schema)

    Path(output_path).mkdir(parents=True, exist_ok=True)
    logging.info(f"Writing chunk {index} to {output_path}")
    pq.write_table(
        table, Path(output_path) / f"chunk_{index}.parquet", compression="zstd"
    )
