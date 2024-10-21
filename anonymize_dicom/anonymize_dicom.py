from pathlib import Path
from typing import Dict, List
import shutil
import csv

import click
from pydicom.dataset import Dataset


def load_id_mapping(tsv_file: str) -> Dict[str, str]:
    """
    Load patient ID mapping from a TSV file.
    Returns a dictionary with old IDs as keys and new IDs as values.
    """
    id_mapping = {}
    with open(tsv_file, newline="") as f:
        reader = csv.reader(f, delimiter=",")
        for row in reader:
            if len(row) >= 2:
                id_mapping[row[0]] = row[1]
    return id_mapping


def anonymize_dataset(ds: Dataset, new_id: str) -> Dataset:
    """
    Anonymize a DICOM dataset by replacing patient name,
    removing patient ID, and modifying birth date.
    """
    if "PatientName" in ds:
        ds.PatientName = new_id

    if "PatientID" in ds:
        del ds.PatientID

    if "PatientBirthDate" in ds:
        original_date = ds.PatientBirthDate
        if original_date:
            year = original_date[:4]
            ds.PatientBirthDate = f"{year}0101"

    if "FileSetID" in ds:
        del ds.FileSetID

    return ds


def anonymize_and_copy_dicomfile(
    src_dicomfile: Path, dst_dir: Path, new_id: str, dry_run: bool
) -> None:
    """
    Create a new anonymized DICOM dataset from the source file and save it to the destination directory.
    If dry_run is True, only print the action without modifying files.
    """
    from pydicom import dcmread

    # Read the DICOM file
    print(f"Preparing DICOMFILE: {dst_dir / src_dicomfile.name}...", end="")
    ds = dcmread(src_dicomfile, force=False)

    # Apply anonymization
    anonymized_ds = anonymize_dataset(ds, new_id)

    if not dry_run:
        # Save the anonymized dataset
        print("Saving.")
        anonymized_ds.save_as(dst_dir / src_dicomfile.name, enforce_file_format=True)
    else:
        print("dry run, not saving.")


def anonymize_and_copy_directory(
    src: Path, dst: Path, new_id: str, dry_run: bool
) -> None:
    """
    Anonymize and copy an entire directory of DICOM files recursively.
    If dry_run is True, only print the actions without modifying files.
    """
    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
    else:
        print(f"Would create directory: {dst}")

    for item in src.rglob("*"):
        relative_path = item.relative_to(src)
        dst_file = dst / relative_path

        if not dry_run:
            dst_file.parent.mkdir(parents=True, exist_ok=True)

        if item.is_file():
            if item.suffix.lower() == ".dcm" or (
                len(item.stem) == 7
                and item.stem[:2].isalpha()
                and item.stem[2] == "_"
                and item.stem[3:].isdigit()
            ):
                anonymize_and_copy_dicomfile(item, dst_file.parent, new_id, dry_run)
            else:
                if not dry_run:
                    print(
                        f"Copying file (not DICOM, not anonymized): {item} to {dst_file}"
                    )
                    shutil.copy2(str(item), str(dst_file))
                else:
                    print(
                        f"Would copy file (not DICOM, not anonymized): {item} to {dst_file}"
                    )
        elif item.is_dir():
            if not dry_run:
                dst_file.mkdir(parents=True, exist_ok=True)
            else:
                print(f"Would create directory: {dst_file}")


def process_datasets(
    input_dir: Path,
    id_mapping: Dict[str, str],
    output_dir: Path,
    dry_run: bool,
) -> None:
    """
    Anonymize multiple datasets based on the provided ID mapping.
    Handles both DICOMDIR and DICOM directory structures.
    If dry_run is True, only print the actions without modifying files.
    """
    for old_id in id_mapping:
        src_dir = input_dir / old_id
        if not src_dir.is_dir():
            print(f"Warning: Directory not found for ID {old_id}. Skipping...")
            continue
        new_id = id_mapping[old_id]
        for session_dir in src_dir.iterdir():
            new_session_dir = output_dir / new_id / session_dir.name
            if new_session_dir.exists():
                print(f"Skipping existing session directory: {new_session_dir}")
                continue
            if not dry_run:
                new_session_dir.mkdir(parents=True, exist_ok=True)
            else:
                print(f"Would create: {new_session_dir}")

            # Process DICOMDIR if it exists
            dicomdirfile = session_dir / "DICOMDIR"
            if dicomdirfile.exists():
                anonymize_and_copy_dicomfile(
                    dicomdirfile, new_session_dir, new_id, dry_run
                )
            else:
                print(f"Warning: DICOMDIR not found in {session_dir}.")

            # Process DICOM directory if it exists
            dicom_dir = session_dir / "DICOM"
            if dicom_dir.exists():
                anonymize_and_copy_directory(
                    dicom_dir, new_session_dir / "DICOM", new_id, dry_run
                )
            else:
                print(
                    f"Warning: DICOM directory not found in {session_dir}. Skipping..."
                )


def print_tags(dataset: Dataset, tag_list: List[str], all_tags: bool) -> None:
    """
    Print DICOM tags from a dataset.
    If all_tags is True, print all tags except sequences.
    Otherwise, print only tags specified in tag_list.
    """
    if all_tags:
        for elem in dataset:
            if elem.VR != "SQ":  # Skip sequence elements
                print(f"{elem.tag} {elem.VR}: {elem.keyword} = {elem.value}")
    elif tag_list:
        for elem in dataset:
            if elem.VR != "SQ" and (
                elem.keyword in tag_list or str(elem.tag) in tag_list
            ):
                print(f"{elem.tag} {elem.VR}: {elem.keyword} = {elem.value}")
    # No output if no matched tags.


@click.command()
@click.argument(
    "dicom_path",
    type=click.Path(exists=True),
)
@click.option(
    "--new-ids",
    type=click.Path(exists=True),
    required=True,
    help="TSV file containing old and new patient identities",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    required=True,
    help="Output directory for anonymized data",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform a dry run without making any changes on disk",
)
def main(
    dicom_path: str,
    new_ids: str,
    output_dir: str,
    dry_run: bool,
) -> None:
    """
    Main function to orchestrate the DICOM anonymization process.
    Handles command-line arguments and initiates the anonymization.

    Arguments:
    dicom_path: Directory that has to be identical to the subject's non-anonymized ID
    """
    id_mapping = load_id_mapping(new_ids)
    process_datasets(Path(dicom_path), id_mapping, Path(output_dir), dry_run)


if __name__ == "__main__":
    main()
