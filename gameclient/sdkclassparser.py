import json
from pathlib import Path


def main():
    classes = {}

    sdkpath = Path('C:/git/gamods/Global Agenda/SDK_HEADERS')
    for file in sdkpath.glob('*_classes.h'):
        with open(file) as f:
            for line in f:
                # do something
                pass


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
