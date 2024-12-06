# [[file:adni-kode.org::*Make tsv (concurrent)][Make tsv (concurrent):1]]
import numpy as np
import pandas as pd
from bids.layout import BIDSLayout
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

bids_path = '/home/espen/forskningsdata/adni-bids/'
num_parallell_jobs=30

def get_sessions(subject):
    """
    This function takes a subject ID as inbut and returns a list of sessions
    for that subject where both PET and T1w files exist.

    Parameters:
    subject (str): Subject ID

    Returns:
    list: A list of tuples containing subject and session IDs where both PET and
    T1w files exist.
    """
    # Get all sessions for the current subject
    sessions = layout.get_sessions(subject=subject)
    # Initialize a list to store sessions with both PET and T1w
    subject_session_list = []

    # Check each session for both PET and T1w images
    try:
        for session in sessions:
            # Check if PET and T1w files exist for the current subject and session
            pet_files = layout.get(subject=subject, session=session, datatype='pet')
            t1w_files = layout.get(subject=subject, session=session, datatype='anat', suffix='T1w')

            if pet_files and t1w_files:
                subject_session_list.append(['sub-' + subject, 'ses-' + session])
    except Exception as e:
        print(f"Error checking for PET and T1 scans for {subject} in session {session}: {e}")

    return subject_session_list

if __name__ == '__main__':
    """
    Main program to geterate TSV file with subject and session IDs for
    subjects with both PET and T1w images

    Steps:
    - Read the layout from the BIDS dataset.
    - Get a list of all subjects in the dataset.
    - Use concurrent programming to check for PET and T1w files concurrently.
    - Save the results as a TSV file.
    """
    print(f"Reading layout from {bids_path}...", end='', flush=True)
    # Initialize the BIDSLayout object to interact with the BIDS dataset
    layout = BIDSLayout(bids_path)
    print("ok")
    print(layout)

    # Get a list of all subjects in the dataset
    subjects = layout.get_subjects()

    with ProcessPoolExecutor(max_workers=num_parallell_jobs) as executor:
        all_results = []
        # Submit tasks for each subject and process the results concurrently
        for subject_session_list in tqdm(executor.map(get_sessions, subjects)):
            try:
                all_results.extend([(subject, session) for subject, session in subject_session_list])
            except Exception as e:
                print(f"Error processing subject {subject}: {e}")

        df_t1_pet = pd.DataFrame(all_results, columns=['participant_id', 'session_id'])

        csv_file_path = 'subjects_t1_pet.tsv'
        df_t1_pet.to_csv(csv_file_path, sep='\t', index=False)

        print(f"Results saved to {csv_file_path}")
# Make tsv (concurrent):1 ends here
