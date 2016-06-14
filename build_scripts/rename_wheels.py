# renames ABI string in wheels from cp34m or cp35m to none

import os

for file in os.listdir('../dist'):
    if '-cp34m-' in file:
        file_parts = file.split('-cp34m-')
        os.rename('../dist/{}'.format(file),
                  '../dist/{}-none-{}'.format(file_parts[0], file_parts[1]))
    elif '-cp35m-' in file:
        file_parts = file.split('-cp35m-')
        os.rename('../dist/{}'.format(file),
                  '../dist/{}-none-{}'.format(file_parts[0], file_parts[1]))
