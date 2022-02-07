#!/usr/bin/env python3

import argparse
import re


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='enumfields.csv to login classes')
    arg_parser.add_argument('file', metavar='FILE', type=str, help='python parse_enum_classes.py known_field_data\enumfields.csv"')

    args = arg_parser.parse_args()
    infile_name = args.file

    with open(infile_name, 'rt') as infile:
        with open(infile_name + '_parsed_classes.txt', 'wt') as outfile:
            for line in infile:
                if "OneByte" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,OneByte,)", r"class m\2(onebyte):\n    def __init__(self):\n        super().__init__(0x\2)\n#", line)
                if "TwoBytes" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,TwoBytes,)", r"class m\2(twobytes):\n    def __init__(self):\n        super().__init__(0x\2)\n#", line)
                if "ThreeBytes" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,ThreeBytes,)", r"class m\2(nbytes):\n    def __init__(self):\n        super().__init__(0x\2, hexparse('00 00 00'))\n#", line)
                if "FourBytes" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,FourBytes,)", r"class m\2(fourbytes):\n    def __init__(self):\n        super().__init__(0x\2)\n#", line)
                if "EightBytes" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,EightBytes,)", r"class m\2(nbytes):\n    def __init__(self):\n        super().__init__(0x\2, hexparse('00 00 00 00 00 00 00 00'))\n#", line)
                if "SizedContent" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,SizedContent,)", r"class m\2(stringenum):\n    def __init__(self):\n        super().__init__(0x\2, '')\n#", line)
                if "ArrayOfEnumBlockArrays" in line:
                    res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,ArrayOfEnumBlockArrays,)", r"class m\2(arrayofenumblockarrays):\n    def __init__(self):\n        super().__init__(0x\2)\n#", line)
                else:
                    if "EnumBlockArray" in line:
                        res_str = re.sub(r"(0x)([0-9a-fA-F]+)(,EnumBlockArray,)", r"class a\2(enumblockarray):\n    def __init__(self):\n        super().__init__(0x\2)\n#", line)
                
                outfile.write(res_str + '\n')