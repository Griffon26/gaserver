import copy
import json
from pathlib import Path
import re


def main():
    types = {'classes': {},
             'structs': {}}
    sdkpath = Path('../../../gamods/Global Agenda/SDK_HEADERS')

    if not sdkpath.exists():
        print(f'{sdkpath} was not found.\n'
              'This script assumes that gamods is located at the same directory level as gaserver.\n'
              'If that is not the case, please modify sdkpath in this script to point to the location of gamods.')
        exit(-1)

    structname = None
    for file in sdkpath.glob('*_structs.h'):
        with open(file, 'rt') as infile:
            for line in infile:
                if not structname:
                    match = re.match(r'^struct ([^ ]+)( : ([^ ]+))?\n$', line)
                    if match:
                        structname = match.group(1)
                        parent = match.group(3)
                        if parent:
                            types['structs'][structname] = copy.copy(types['structs'][parent])
                        else:
                            types['structs'][structname] = []
                        print(f'struct {structname}')

                else:
                    if line == '};\n':
                        structname = None
                    else:
                        match = re.match(r'^\t([^:]*)  ([^ :;]+)( : 1)?(\[[^;]*\])?;.*$', line)
                        if match:
                            _type = match.group(1)
                            _array = match.group(3)
                            _bit = match.group(4)
                            types['structs'][structname].append({
                                'name': match.group(2),
                                'type': f'{_type.strip()}{_array.strip() if _array else ""}{_bit.strip() if _bit else ""}'
                            })

    for file in sdkpath.glob('*_classes.h'):
        with open(file, 'rt') as infile:
            for line in infile:
                match = re.match(r'^class (.+) : .*', line)
                if match:
                    classname = match.group(1)
                    if classname.startswith('A'):
                        classname = classname[1:]
                    currentclass = {'fields': {},
                                    'methods': {}}
                    types['classes'][classname] = currentclass

                else:
                    match = re.match(r'^\t([^:]*)  ([^ :;]+)( : 1)?(\[[^;]*\])?;.*CPF_Net.*$', line)
                    if match:
                        fieldtype = match.group(1).strip()
                        fieldname = match.group(2)
                        if match.group(3) is not None:
                            fieldtype = 'bool'
                        if match.group(4) is not None:
                            fieldtype += '[]'

                        currentclass['fields'][fieldname] = fieldtype
                    else:
                        match = re.match(r'^([^\(]*)\(([^\)]*)\);$', line)
                        if match:
                            def to_type_and_name(space_separated_string):
                                parts = space_separated_string.split()
                                mytype = ' '.join(parts[:-1])
                                myname = parts[-1]
                                return mytype, myname

                            func = match.group(1)
                            functype, funcname = to_type_and_name(func)

                            paramtext = match.group(2).strip()
                            if paramtext:
                                param_types_and_names = [to_type_and_name(param) for param in paramtext.split(',')]
                                params = [{'name': myname, 'type': mytype} for mytype, myname in param_types_and_names]
                            else:
                                params = []

                            currentclass['methods'][funcname] = {
                                'rettype': functype,
                                'params': params
                            }


        with open('extracted_classes.json', 'w') as f:
            json.dump(types, f, indent=2)


main()
