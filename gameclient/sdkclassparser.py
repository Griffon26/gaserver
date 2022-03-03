import json
from pathlib import Path
import re

def main():
    classes = {}
    sdkpath = Path('I:/games/Global Agenda/gamods/Global Agenda/SDK_HEADERS')
    inclass = True
    firstline = True

    with open('parsed_classes.tmp', 'wt') as outfile:
        outfile.write("{")
        for file in sdkpath.glob('*_classes.h'):
            with open(file, 'rt') as infile:
                    for line in infile:
                        if re.search(r'^class\ (.+)\ \:\ .*', line):
                            res_str = re.sub(r"^class\ (.+)\ \:\ .*", r"'\1': {",line)
                            if firstline:
                                inclass = True
                                firstline = False
                            else:
                                inclass = False
                                outfile.write("},")
                            outfile.write(res_str.replace("'","\""))
                        elif "CPF_Net" in line:
                            if re.search(r'^\t([a-zA-Z]*)\ *([a-zA-Z]+)\ +([a-zA-Z]+)\;.+$', line):
                                #res_str = re.sub(r"^\t([a-zA-Z]*)\ *([a-zA-Z]+)\ +([a-zA-Z]+)\;.+$", r"'\3': '\2',", line)
                                res_str = re.sub(r"^\t([a-zA-Z]+)\ *([a-zA-Z]*)\ +([a-zA-Z]+)\;.+$", r"'\3': '\1 \2',", line).replace("struct ", "").replace(" ',","',")
                                outfile.write(res_str.replace("'","\""))
        #"s/,\n}//g"
        outfile.write("}")
        outfile.write("}")
        outfile.close()
        with open('parsed_classes.tmp', 'r') as inf:
            filestr = inf.read()
            content_new = re.sub(',\n}', r'\n}', filestr)
            var = json.loads(content_new)
            print(var)
            open('parsed_classes.json', 'wt').write(content_new)
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
