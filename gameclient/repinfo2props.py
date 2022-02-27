from bitarray import bitarray
import json
import struct

def int2bitarray(n, nbits):
    bits = bitarray(endian='little')
    bits.frombytes(struct.pack('<L', n))
    return bits[:nbits]

def main():
    classes = {}
    with open('FFieldNetCache_RepProperties.txt') as f:
        for line in f:
            if not line.startswith('  '):
                classname, classid = line.split()
                bits = int2bitarray(int(classid), 32)
                currentprops = {}
                classes[bits.to01()] = {'name': classname,
                                        'props': currentprops}
            else:
                member, memberid = line.split()
                bits = int2bitarray(int(memberid), 16)
                currentprops[bits.to01()] = member

    #print(json.dumps(classes, indent=2))


    for classid, classdata in classes.items():
        print(f'{classdata["name"]}Props = {{')
        for memberid, member in classdata['props'].items():
            print(f"    '{memberid}': {{'name': '{member}', 'type': bitarray, 'size': 1}},")
        print(f'}}')
        print()

    print(f'self.class_dict = {{')
    for classid, classdata in classes.items():
        print(f"    '{classid}': {{'name': '{classdata['name']}', 'props': {classdata['name']}Props}},")
    print(f'}}')


if __name__ == '__main__':
    main()