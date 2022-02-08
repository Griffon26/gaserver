#!/usr/bin/env python3

import argparse
import re


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='enumfields.csv to login classes')
    arg_parser.add_argument('file', metavar='FILE', type=str, help='python parse_cpp-datatypes_enum.py types-out.txt')

    args = arg_parser.parse_args()
    infile_name = args.file

    with open(infile_name, 'rt') as infile:
        with open('cpp-datatypes_enumfields.csv', 'wt') as outfile:
            for line in infile:
                if "TYPE_WCHAR_STR" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_WCHAR_STR)", r"\1,SizedContent,\2", line)
                elif "TYPE_DATA_SET" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_DATA_SET)", r"\1,EnumBlockArray,\2", line)
                elif "TYPE_FLOAT" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_FLOAT)", r"\1,FourBytes,\2", line)
                elif "TYPE_DYNAMIC_UINT32_SIZE" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_DYNAMIC_UINT32_SIZE)", r"\1,EnumBlockArray,\2", line)
                elif "TYPE_DATETIME" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_DATETIME)", r"\1,FourBytes,\2", line)
                elif "TYPE_DOUBLE_OR_INT_SIGNED" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_DOUBLE_OR_INT_SIGNED)", r"\1,FourBytes,\2", line)
                elif "TYPE_UINT8" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_UINT8)", r"\1,OneByte,\2", line)
                elif "TYPE_UINT16" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_UINT16)", r"\1,TwoByte,\2", line)
                elif "TYPE_UINT32" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_UINT32)", r"\1,FourBytes,\2", line)
                elif "TYPE_UINT64" in line:
                    res_str = re.sub(r"\ +([0-9]+).+Name\:\ ([0-9a-zA-Z_]*).+(TYPE_UINT64)", r"\1,EightBytes,\2", line)
                
                decstr = re.compile('[0-9]+').match(res_str)
                #doesn't matter #res_str = re.sub(decstr.group(), str(hex(int(decstr.group()))), res_str)
                res_str = re.sub(decstr.group(), "{0:#0{1}x}".format((int(decstr.group())),6), res_str)
                outfile.write(res_str)