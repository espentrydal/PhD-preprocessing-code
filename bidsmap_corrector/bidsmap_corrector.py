import yaml
import click
from typing import Dict, Any, Tuple
from collections import OrderedDict
from yaml.representer import Representer
from yaml.dumper import SafeDumper


def represent_ordereddict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


SafeDumper.add_representer(OrderedDict, represent_ordereddict)


# Define known suffix categories
SUFFIX_CATEGORIES = {
    "T1w": "anat",
    "T2w": "anat",
    "flair": "anat",
    "bold": "func",
    "dwi": "dwi",
}
DICOM_KEY = "DICOM"
BIDS_KEY = "bids"
BIDS_SUFFIX_KEY = "suffix"
EXTRA_DATA = "extra_data"


def literal_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


SafeDumper.add_representer(str, literal_presenter)


def process_dicom_item(item: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Process a single DICOM item and return its category and the item itself."""
    suffix = item.get(BIDS_KEY, {}).get(BIDS_SUFFIX_KEY)
    for sequence in SUFFIX_CATEGORIES:
        if suffix == sequence:
            return SUFFIX_CATEGORIES[suffix], item
    return EXTRA_DATA, item


def correct_dicom_schemas(data: Dict[str, Any]) -> Dict[str, Any]:
    """Traverse the YAML structure and reorganize based on the bids suffix while preserving key order."""
    ordered_data = OrderedDict()

    for toplevel, toplevel_data in data.items():
        if toplevel != DICOM_KEY:
            ordered_data[toplevel] = toplevel_data
            continue

        ordered_data[DICOM_KEY] = OrderedDict()
        for category, category_data in toplevel_data.items():
            print(
                f"CATEGORY: {category} DATATYPE: {type(category_data)}\nVALUE: {category_data}"
            )

            if not isinstance(category_data, list):
                if category not in ordered_data[DICOM_KEY].keys():
                    ordered_data[DICOM_KEY][category] = category_data
                continue

            for item in category_data:
                new_category, processed_item = process_dicom_item(item)
                if new_category not in ordered_data[DICOM_KEY].keys():
                    ordered_data[DICOM_KEY][new_category] = list()
                if new_category in SUFFIX_CATEGORIES.values():
                    ordered_data[DICOM_KEY][new_category].append(processed_item)
                else:
                    ordered_data[DICOM_KEY][EXTRA_DATA].append(item)

    return ordered_data


@click.command()
@click.option(
    "--input",
    required=True,
    type=click.Path(exists=True),
    help="Path to the input YAML file",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(),
)
def main(input: str, output: str) -> None:
    try:
        with open(input, "r") as infile, open(output, "w") as outfile:
            data = yaml.safe_load(infile)
            from pprint import pprint

            # pprint(data, width=40)
            corrected_data = correct_dicom_schemas(data)

            yaml.dump(
                corrected_data,
                outfile,
                Dumper=SafeDumper,
                default_flow_style=False,
                sort_keys=False,
                width=float("inf"),
            )

        click.echo(f"Successfully corrected YAML file. Output saved to {output}")
    except Exception as e:
        click.echo(f"An error occurred: {str(e)}", err=True)


if __name__ == "__main__":
    main()
