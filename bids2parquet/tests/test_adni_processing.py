import pytest
import polars as pl
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

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

# Fixtures
@pytest.fixture
def mock_bids_df():
    return pl.DataFrame({
        'filename': ['sub-ADNI002S0413_ses-M132_T1w.nii.gz'],
        'path': ['/path/to/sub-ADNI002S0413_ses-M132_T1w.nii.gz'],
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

# Tests for data processing
class TestDataProcessing:
    def test_collect_data_to_csv(self, mock_bids_df, mock_adnimerge_csv):
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
        assert set(['ptid', 'session', 'dx']).issubset(result.columns)

    def test_split_train_val_test(self):
        df = pl.DataFrame({'ptid': [f'sub-ADNI{i:03d}' for i in range(100)], 'value': range(100)})
        train, val, test = split_train_val_test(df, 0.7, 0.15)
        assert len(train) + len(val) + len(test) == 100
        assert 0.65 < len(train) / 100 < 0.75
        assert 0.10 < len(val) / 100 < 0.20
        assert 0.10 < len(test) / 100 < 0.20

    @pytest.mark.parametrize("shape", [(10, 10, 10), (20, 20, 20)])
    def test_process_scan(self, shape):
        mock_volume = np.random.rand(*shape)
        with patch('src.bids2parquet.adni_processing.data_processing.processing.read_nifti_file', return_value=mock_volume):
            result = process_scan('dummy_path')
            assert result.shape == (*shape, 1)
            assert result.dtype == np.float32
            assert np.all(result >= 0) and np.all(result <= 1)

    @pytest.mark.parametrize("input_array, expected_shape", [
        (np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]]), (8,)),
        (np.array([[1, 2, 3], [4, 5, 6]]), (6,)),
    ])
    def test_flatten(self, input_array, expected_shape):
        result = flatten(input_array)
        assert result.shape == expected_shape
        assert np.array_equal(result, input_array.flatten())

# Tests for file operations
class TestFileOperations:
    def test_read_bids_parquet(self, tmp_path):
        df = pl.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        parquet_path = tmp_path / "test.parquet"
        df.write_parquet(parquet_path)

        result = read_bids_parquet(parquet_path)
        assert len(result) == 3
        assert set(['col1', 'col2']).issubset(result.columns)

    def test_write_df_to_tsv(self, tmp_path):
        df = pl.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        output_path = tmp_path / "test.tsv"
        write_df_to_tsv(df, output_path)
        assert output_path.exists()

        read_df = pl.read_csv(output_path, separator='\t')
        assert len(read_df) == 3
        assert set(['col1', 'col2']).issubset(read_df.columns)

# Tests that require more complex setup or mocking
class TestComplexOperations:
    @pytest.mark.skip(reason="Requires actual NIfTI file")
    def test_read_nifti_file(self):
        # Implement when you have a way to mock or provide a test NIfTI file
        pass

    @pytest.mark.skip(reason="Requires actual data and file system operations")
    def test_process_and_write_column(self):
        # Implement when you have a way to mock the file system and data processing
        pass

    @pytest.mark.skip(reason="Requires actual data processing")
    def test_process_and_write_chunk(self):
        # Implement when you have a way to mock the data processing and chunk writing
        pass

if __name__ == "__main__":
    pytest.main()
