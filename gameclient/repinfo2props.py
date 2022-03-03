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
                classname, classid = line.split()
                bits = int2bitarray(int(classid), 32)
                currentprops = {}
                classes[bits.to01()] = {'name': classname,
                                        'props': currentprops}
            else:
                # TODO: also parse the class for each field
                member, memberid, originatingclass = line.split()
                currentprops[int(memberid)] = {'name': member,
                                               'class': originatingclass }

    with open('parsed_classes.json') as f:
        classes_from_sdk = json.load(f)

    with open('props.txt', 'w') as f:
        for classid, classdata in classes.items():
            f.write(f'{classdata["name"]}Props = {{\n')
            max_field_id = max(classdata['props'].keys())
            bits_for_field = int(math.ceil(math.log(max_field_id, 2)))

            for memberid, member_data in classdata['props'].items():
                memberidbits = int2bitarray(memberid, bits_for_field)
                type_to_typestring = {
                    'bool':             "'type': bool",
                    'struct FString':   "'type': str",
                    'int':              "'type': int",
                    'class ATgPawn*':   "'type': bitarray, 'size': 11",
                }
                try:
                    cpp_type = classes_from_sdk[member_data['class']][member_data['name']]
                    typestring = type_to_typestring[cpp_type]
                except KeyError:
                    typestring = "'type': None"
                f.write(f"    '{memberidbits.to01()}': {{'name': '{member_data['name']}', {typestring}}},\n")
            f.write(f'}}\n\n')

        f.write(f'self.class_dict = {{\n')
        for classid, classdata in classes.items():
            f.write(f"    '{classid}': {{'name': '{classdata['name']}', 'props': {classdata['name']}Props}},\n")
        f.write(f'}}\n\n')


if __name__ == '__main__':
    main()