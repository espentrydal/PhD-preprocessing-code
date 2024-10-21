from pathlib import Path
from typing import List, Optional, Tuple

import click
import yaml
from pydicom.dataset import Dataset
from pydicom.filereader import dcmread


def print_nested_tags(
    dataset: Dataset, tag_list: List[str], all_tags: bool, indent: int = 0
) -> None:
    for elem in dataset:
        if all_tags or (
            tag_list and (elem.keyword in tag_list or str(elem.tag) in tag_list)
        ):
            print(" " * indent + f"{elem.tag} {elem.VR}: {elem.keyword} = {elem.value}")

        if elem.VR == "SQ":
            for i, item in enumerate(elem.value):
                # print(" " * indent + f"  Sequence Item #{i+1}:")
                print_nested_tags(item, tag_list, all_tags, indent + 4)

        if all_tags or (
            tag_list and (elem.keyword in tag_list or str(elem.tag) in tag_list)
        ):
            print()


def print_tags(dataset: Dataset, tag_list: List[str], all_tags: bool) -> None:
    print_nested_tags(dataset, tag_list, all_tags)

    # No output if no matched tags.


def process_dicom_files_and_directories(
    paths: List[str],
    all_tags: bool = False,
    tag_file: Optional[str] = None,
    max_files: Optional[int] = None,
) -> None:
    tag_list = []
    if tag_file:
        with open(tag_file, "r") as f:
            tag_list = yaml.safe_load(f)

    for path in paths:
        path = Path(path)
        if not path.exists():
            print(f"'{path}' does not exist. Skipping...")
            continue

        if path.is_file():
            process_dicom_file(path, tag_list, all_tags)
        elif path.is_dir():
            process_dicom_directory(path, tag_list, all_tags, max_files)


def process_dicom_file(file_path: Path, tag_list: List[str], all_tags: bool) -> None:
    try:
        with dcmread(str(file_path)) as ds:
            if file_path.name == "DICOMDIR":
                # Process DICOMDIR file
                print("DICOMDIR structure:")
                print_dicomdir_tree(ds)
                print("\nDirectory record tags:")
            else:
                print(f"File: {file_path.name}")
            print_tags(ds, tag_list, all_tags)
    except Exception as e:
        print(f"Error reading file {file_path.name}: {str(e)}")


def print_dicomdir_tree(ds, level=0, image_count=0):
    for record in ds.DirectoryRecordSequence:
        record_type = record.DirectoryRecordType
        if record_type == "IMAGE":
            image_count += 1
            if image_count < 5:
                print("  " * level + f"|-{record_type}")
            elif image_count == 5:
                print("  " * level + "|-(...)")
                print("  " * level + "Ignoring the remaining images...")
        else:
            print("  " * level + f"|-{record_type}")
            if hasattr(record, "DirectoryRecordSequence"):
                image_count = print_dicomdir_tree(record, level + 1, 0)
    return image_count


def process_dicom_directory(
    directory_path: Path, tag_list: List[str], all_tags: bool, max_files: Optional[int]
) -> None:
    # Process individual DICOM files
    file_count = 0
    dicom_files = sorted(
        [
            file_path
            for file_path in directory_path.iterdir()
            if file_path.is_file()
            and (file_path.suffix == ".dcm" or file_path.suffix == "")
        ]
    )
    for file_path in dicom_files:
        try:
            with dcmread(str(file_path)) as ds:
                print(f"File: {file_path.name}")
                print_tags(ds, tag_list, all_tags)
            file_count += 1
            if max_files is not None and file_count >= max_files:
                print(
                    f"Reached maximum number of files ({max_files}) for directory {directory_path}"
                )
                break
        except Exception as e:
            print(f"Error reading file {file_path.name}: {str(e)}")


@click.command()
@click.argument("dicom_paths", nargs=-1, type=click.Path(exists=True))
@click.option(
    "--all", "all_tags", is_flag=True, show_default=True, help="Print all tags"
)
@click.option(
    "--tagfile",
    type=click.Path(exists=True, dir_okay=True),
    help="YAML file containing tags to print. Tags should be given either as keywords or as tags in the format (1234,5678)",
)
@click.option(
    "--max-files",
    type=int,
    default=None,
    help="Maximum number of files to process per directory",
)
def main(
    dicom_paths: Tuple[str, ...],
    all_tags: bool,
    tagfile: Optional[str],
    max_files: Optional[int],
) -> None:
    if not dicom_paths:
        click.echo("Please provide at least one DICOM file or directory.")
        return
    process_dicom_files_and_directories(list(dicom_paths), all_tags, tagfile, max_files)


if __name__ == "__main__":
    main()
