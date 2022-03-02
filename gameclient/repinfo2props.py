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
            if not line.startswith('  '):
                classname, classid = line.split()
                bits = int2bitarray(int(classid), 32)
                currentprops = {}
                classes[bits.to01()] = {'name': classname,
                                        'props': currentprops}
            else:
                member, memberid = line.split()
                currentprops[int(memberid)] = member

    #print(json.dumps(classes, indent=2))


    for classid, classdata in classes.items():
        print(f'{classdata["name"]}Props = {{')
        max_field_id = max(classdata['props'].keys())
        bits_for_field = int(math.ceil(math.log(max_field_id, 2)))

        for memberid, member in classdata['props'].items():
            memberidbits = int2bitarray(memberid, bits_for_field)
            print(f"    '{memberidbits.to01()}': {{'name': '{member}', 'type': bitarray, 'size': 1}},")
        print(f'}}')
        print()

    print(f'self.class_dict = {{')
    for classid, classdata in classes.items():
        print(f"    '{classid}': {{'name': '{classdata['name']}', 'props': {classdata['name']}Props}},")
    print(f'}}')


if __name__ == '__main__':
    main()