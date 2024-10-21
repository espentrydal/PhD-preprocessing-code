import pytest
from pathlib import Path
from bids2parquet import to_ptid, valid_dx, collect_data_to_csv

# Mock data and constants for testing
VALID_DX_MOCK = ["cn", "mci", "dementia"]

# Tests for to_ptid function
def test_to_ptid():
    assert to_ptid("sub-ADNI001S0023") == "001_S_0023"
    assert to_ptid("sub-ADNI002S0045") == "002_S_0045"

# Tests for valid_dx function
def test_valid_dx():
    # Assuming VALID_DX is set in bids2parquet.py
    assert valid_dx("cn") == True
    assert valid_dx("mci") == True
    assert valid_dx("dementia") == True
    assert valid_dx("invalid") == False

# Tests for collect_data_to_csv function
# This test requires a mock BIDSLayout and CSV file
def test_collect_data_to_csv():
    # Mock objects would be created here
    # For example, using pytest-mock or unittest.mock
    # layout = mock.create_autospec(BIDSLayout)
    # afile_csv = Path("/path/to/mock/ADNIMERGE.csv")
    # phases = ["ADNI1", "ADNI2"]
    # data_csv = Path("/path/to/mock/output.csv")
    # result_df = collect_data_to_csv(layout, afile_csv, phases, data_csv)
    # Assertions would be made here based on the expected result
    pass

# Additional tests would be added here for other functions
import pytest
import polars as pl
import pyarrow as pa
from pathlib import Path
import numpy as np
from src.bids2parquet.adni_processing.data_processing.processing import (
    collect_data_to_csv,
    split_train_val_test,
    read_nifti_file,
    process_scan,
    flatten,
    process_and_write_column
)
from src.bids2parquet.adni_processing.file_operations.io import (
    read_bids_parquet,
    write_df_to_tsv,
    process_and_write_chunk
)

# Mock data and fixtures
@pytest.fixture
def mock_bids_df():
    return pl.DataFrame({
        'filename': ['sub-ADNI002S0413_ses-M132_T1w.nii.gz'],
        'path': ['/home/espen/forskningsdata/adni/caps/subjects/sub-ADNI002S0413/ses-M132/t1_linear/sub-ADNI002S0413_ses-M132_T1w.nii.gz'],
        'suffix': ['T1w'],
        'extension': ['nii.gz'],
        'desc': ['Crop'],
        'res': ['1x1x1']
    })

@pytest.fixture
def mock_adnimerge_csv(tmp_path):
    df = pl.DataFrame({
        'COLPROT': ['ADNI3'],
        'PTID': ['002_S_0413'],
        'VISCODE': ['m132'],
        'DX': ['CN']
    })
    csv_path = tmp_path / "mock_adnimerge.csv"
    df.write_csv(csv_path)
    return csv_path

# Tests
def test_collect_data_to_csv(mock_bids_df, mock_adnimerge_csv):
    result = collect_data_to_csv(
        mock_adnimerge_csv,
        mock_bids_df,
        phases=['ADNI3'],
        valid_dx=['cn'],
        suffix='T1w',
        trc='',
        rec='',
        desc='Crop',
        res='1x1x1'
    )
    assert len(result) == 1
    assert 'ptid' in result.columns
    assert 'session' in result.columns
    assert 'dx' in result.columns

def test_split_train_val_test():
    df = pl.DataFrame({'ptid': [f'sub-ADNI{i:03d}' for i in range(100)], 'value': range(100)})
    train, val, test = split_train_val_test(df, 0.7, 0.15)
    assert len(train) + len(val) + len(test) == 100
    assert 0.65 < len(train) / 100 < 0.75
    assert 0.10 < len(val) / 100 < 0.20
    assert 0.10 < len(test) / 100 < 0.20

@pytest.mark.skip(reason="Requires actual NIfTI file")
def test_read_nifti_file():
    # This test would require a real NIfTI file
    pass

def test_process_scan(mocker):
    mock_volume = np.random.rand(10, 10, 10)
    mocker.patch('src.bids2parquet.adni_processing.data_processing.processing.read_nifti_file', return_value=mock_volume)
    result = process_scan('dummy_path')
    assert result.shape == (10, 10, 10, 1)
    assert result.dtype == np.float32
    assert np.all(result >= 0) and np.all(result <= 1)

def test_flatten():
    arr = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
    result = flatten(arr)
    assert result.shape == (8,)
    assert np.array_equal(result, np.array([1, 2, 3, 4, 5, 6, 7, 8]))

@pytest.mark.skip(reason="Requires actual data and file system operations")
def test_process_and_write_column():
    # This test would require setting up mock data and file system
    pass

def test_read_bids_parquet(tmp_path):
    # Create a mock parquet file
    df = pl.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
    parquet_path = tmp_path / "test.parquet"
    df.write_parquet(parquet_path)

    result = read_bids_parquet(parquet_path)
    assert len(result) == 3
    assert 'col1' in result.columns
    assert 'col2' in result.columns

def test_write_df_to_tsv(tmp_path):
    df = pl.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
    output_path = tmp_path / "test.tsv"
    write_df_to_tsv(df, output_path)
    assert output_path.exists()

    # Read back and check
    read_df = pl.read_csv(output_path, separator='\t')
    assert len(read_df) == 3
    assert 'col1' in read_df.columns
    assert 'col2' in read_df.columns

@pytest.mark.skip(reason="Requires actual data processing")
def test_process_and_write_chunk():
    # This test would require setting up mock data and processing
    pass
