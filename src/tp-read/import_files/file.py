import shutil
import os

def import_files(files, data_dir):
    """
    Imports a list of files into tp-read's folders. Expects
    `files` to be a dictionary with one entry per file with
    the following structure:
    
        {
            'file1': {
                'teacher': 'Teacher1',
                'term': 'fall-24',
                'class': 'MATH101'
            }
        }
    """
    for file, metadata in files.items():
        import_file(file, data_dir, metadata)

def import_file(path, data_dir, metadata):
    """
    Imports a file into tp-read's folders for later processing.
    Expects `metadata` to be a dictionary defining teacher, term
    and class.
    """
    shutil.copy(
        path,
        os.path.join(
            data_dir,
            metadata['teacher'],
            metadata['term'],
            metadata['class']
        )
    )