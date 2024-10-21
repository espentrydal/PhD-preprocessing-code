import pathlib
import click
import pydicom
from pydicom.filereader import dcmread


def get_dicom_files(directory: pathlib.Path) -> set[pathlib.Path]:
    """Get all DICOM files in the directory and its subdirectories."""
    dicom_files = set()
    for file in directory.rglob("*"):
        if file.is_file() and (
            file.suffix.lower() == ".dcm"
            or (
                file.name[:2].isalpha()
                and file.name[2] == "_"
                and file.name[3:7].isdigit()
            )
        ):
            dicom_files.add(file)
    return dicom_files


def get_dicomdir_files(
    dicomdir: pydicom.FileDataset, directory: pathlib.Path
) -> set[str]:
    """Get files listed in DICOMDIR."""
    dicomdir_files = set()
    for record in dicomdir.DirectoryRecordSequence:
        if record.DirectoryRecordType == "IMAGE":
            file_id = pathlib.Path(*record.ReferencedFileID)
            dicomdir_files.add(str(directory / file_id))
    return dicomdir_files


def compare_files(
    actual_files: set[str], dicomdir_files: set[str]
) -> tuple[set[str], set[str], set[str]]:
    """Compare actual files with DICOMDIR files using set operations."""
    missing_in_dicomdir = actual_files.difference(dicomdir_files)
    extra_in_dicomdir = dicomdir_files.difference(actual_files)
    common_files = actual_files.intersection(dicomdir_files)
    return missing_in_dicomdir, extra_in_dicomdir, common_files


def check_dicomdir(
    directory: pathlib.Path,
    print_dicomdir_only: bool,
    print_directory_only: bool,
    print_common: bool,
) -> None:
    """Check if DICOMDIR is up to date with the actual DICOM files in the directory."""
    dicomdir_path = directory / "DICOMDIR"

    if not dicomdir_path.exists():
        click.echo("DICOMDIR file not found.")
        return

    dicomdir = dcmread(dicomdir_path)

    actual_files = set(str(file) for file in get_dicom_files(directory))
    dicomdir_files = set(str(file) for file in get_dicomdir_files(dicomdir, directory))
    missing_in_dicomdir, extra_in_dicomdir, common_files = compare_files(
        actual_files, dicomdir_files
    )

    if not missing_in_dicomdir and not extra_in_dicomdir:
        click.echo("DICOMDIR is up to date.")
    else:
        click.echo(
            f"Files missing in the DICOMDIR index file: {len(missing_in_dicomdir)}"
        )
        click.echo(f"Extra files in the DICOMDIR index file: {len(extra_in_dicomdir)}")

    if print_dicomdir_only:
        click.echo("\nFiles only in the DICOMDIR index file:")
        for file in extra_in_dicomdir:
            click.echo(file)

    if print_directory_only:
        click.echo("\nFiles only in DICOM directory:")
        for file in missing_in_dicomdir:
            click.echo(file)

    if print_common:
        click.echo("\nFiles in both DICOMDIR and DICOM directory:")
        for file in common_files:
            click.echo(file)


@click.command()
@click.argument(
    "directory",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path
    ),
)
@click.option(
    "--print-only",
    type=click.Choice(["dicomdir", "dicomfiles", "common"]),
    multiple=True,
    help="Specify which files to print: 'dicomdir' for files only in DICOMDIR, "
    "'dicomfiles' for files only in the DICOM directory, "
    "'common' for files in both DICOMDIR and the DICOM directory",
)
def main(
    directory: pathlib.Path,
    print_only: tuple[str],
) -> None:
    print_dicomdir_only = "dicomdir" in print_only
    print_directory_only = "dicomfiles" in print_only
    print_common = "common" in print_only
    check_dicomdir(directory, print_dicomdir_only, print_directory_only, print_common)


if __name__ == "__main__":
    main()
