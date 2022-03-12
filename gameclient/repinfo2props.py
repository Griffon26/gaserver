from bitarray import bitarray
import json
import math
import struct


def int2bitarray(n, nbits):
    bits = bitarray(endian='little')
    bits.frombytes(struct.pack('<L', n))
    return bits[:nbits]


def main():
    classes = {}

    with open('gadlloutput.txt') as f:
        for line in f:
            if not line.strip():
                continue

            if not line.startswith('  '):
                classname, decimalclassid = line.split()
                classid = int2bitarray(int(decimalclassid) * 2, 32).to01()
                currentprops = {}
                classes[classid] = {'name': classname,
                                    'props': currentprops}
            else:
                # TODO: also parse the class for each field
                member, memberid, originatingclass = line.split()
                currentprops[int(memberid)] = {'name': member,
                                               'class': originatingclass }

    classes = {classid: classdata for classid, classdata in classes.items() if len(classdata['props']) > 0}

    with open('parsed_classes.json') as f:
        classes_from_sdk = json.load(f)

    with open('props.py', 'w') as f:
        def reverse_string(s):
            return s[::-1]

        f.write('from bitarray import bitarray\n\n')

        for classid in sorted(classes.keys(), key=reverse_string):
            classdata = classes[classid]
            f.write(f'{classdata["name"]}Props = {{\n')
            max_field_id = max(classdata['props'].keys())
            bits_for_field = int(math.ceil(math.log(max_field_id, 2)))

            classdata['props'] = {int2bitarray(memberid, bits_for_field).to01(): member_data for memberid, member_data in classdata['props'].items()}


            for memberid in sorted(classdata['props'].keys(), key=reverse_string):
                member_data = classdata['props'][memberid]
                type_to_typestring = {
                    'bool':             "'type': bool",
                    'float':            "'type': float",
                    'int':              "'type': int",
                    'unsigned char':    "'type': bitarray, 'size': 8",
                    'struct FString':   "'type': str",
                    'struct FRotator':  "'type': bitarray, 'size': 3 * 8",
                    'struct FVector':   "'type': 'fvector'",
                }
                try:
                    cpp_type = classes_from_sdk[member_data['class']][member_data['name']]
                except KeyError:
                    print(f'Member not found in SDK: {member_data}')
                    cpp_type = 'not_in_sdk'
                try:
                    if cpp_type.endswith('*'):
                        typestring = "'type': bitarray, 'size': 11"
                        comment = ''
                    else:
                        typestring = type_to_typestring[cpp_type]
                        comment = ''
                except KeyError:
                    typestring = "'type': None"
                    comment = f'\t# original type was: {cpp_type}'
                f.write(f"    '{memberid}': {{'name': '{member_data['name']}', {typestring}}},{comment}\n")
            f.write(f'}}\n\n')

        f.write(f'generated_class_dict = {{\n')

        for classid in sorted(classes.keys(), key=reverse_string):
            classdata = classes[classid]
            f.write(f"    '{classid}': {{'name': '{classdata['name']}', 'props': {classdata['name']}Props}},\n")
        f.write(f'}}\n\n')


if __name__ == '__main__':
    main()