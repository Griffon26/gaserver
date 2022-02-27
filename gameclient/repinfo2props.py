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
                currentclass = line.strip()
                classes[currentclass] = {}
            else:
                member, value = line.split()
                classes[currentclass][value] = member

    print(json.dumps(classes, indent=2))

    for myclass, myid in classes:
        int2bitarray()


if __name__ == '__main__':
    main()