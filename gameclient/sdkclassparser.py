import json
from pathlib import Path
import re


def main():
    classes = {}
    sdkpath = Path('C:/git/gamods/Global Agenda/SDK_HEADERS')

    for file in sdkpath.glob('*_classes.h'):
        with open(file, 'rt') as infile:
            for line in infile:
                match = re.match(r'^class\ (.+)\ \:\ .*', line)
                if match:
                    classname = match.group(1)
                    if classname.startswith('A'):
                        classname = classname[1:]
                    currentclass = {}
                    classes[classname] = currentclass

                else:
                    match = re.match(r'^\t([^:]*)  ([^ :;]+)( : 1)?(\[[^;]*\])?;.*CPF_Net.*$', line)
                    if match:
                        fieldtype = match.group(1).strip()
                        fieldname = match.group(2)
                        if match.group(3) is not None:
                            fieldtype = 'bool'
                        if match.group(4) is not None:
                            fieldtype += '[]'

                        currentclass[fieldname] = fieldtype

        with open('parsed_classes.json', 'w') as f:
            json.dump(classes, f, indent=2)


main()

'''
For code like this:
    class ATgRepInfo_Player : public APlayerReplicationInfo
    {
    public:
        int                                                r_nCharacterId;                                   		// 0x0270 (0x0004) [0x0000000000000020]              ( CPF_Net )
        float                                              c_fLastUpdateTime;                                		// 0x0274 (0x0004) [0x0000000000000000]              
        int                                                r_nHealthCurrent;                                 		// 0x0278 (0x0004) [0x0000000000000020]              ( CPF_Net )
        int                                                r_nHealthMaximum;                                 		// 0x027C (0x0004) [0x0000000000000020]              ( CPF_Net )

Output this:
    { 'ATgRepInfo_Player': { 'r_nCharacterId': 'int',
                             'r_nHealthCurrent': 'int',
                             'r_nHealthMaximum': 'int' },
      ...
    }

'''
