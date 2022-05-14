from bitarray import bitarray
import json
from pathlib import Path
import re
import struct


def int2bitarray(n, nbits):
    bits = bitarray(endian='little')
    bits.frombytes(struct.pack('<L', n))
    if any(bits[nbits:]):
        raise ValueError(f'Unable to store {n} in {nbits} bits')
    return bits[:nbits]


def main():
    classes = {}

    with open('replication_info.txt') as f:
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

    with open('extracted_classes.json') as f:
        classes_from_sdk = json.load(f)

    with open(Path('../props.py'), 'w') as f:
        def reverse_string(s):
            s = (s + '0' * 100)[:100]
            return s[::-1]

        f.write('from bitarray import bitarray\n\n')

        for classid in sorted(classes.keys(), key=reverse_string):
            classdata = classes[classid]
            f.write(f'{classdata["name"]}Props = {{\n')
            max_field_id = max(classdata['props'].keys())

            def get_msb(value):
                nr_of_bits = 0
                while value > 0:
                    value >>= 1
                    nr_of_bits += 1

                msb = 1 << (nr_of_bits - 1)
                return msb, nr_of_bits

            def memberid_to_bits(memberid, max_field_id):
                msb, nbits = get_msb(max_field_id)
                memberidbits = int2bitarray(memberid, nbits)
                if (memberid | msb) > max_field_id:
                    memberidbits = memberidbits[:-1]

                return memberidbits.to01()

            classdata['props'] = {memberid_to_bits(memberid, max_field_id): member_data for memberid, member_data in classdata['props'].items()}

            for memberid in sorted(classdata['props'].keys(), key=reverse_string):
                member_data = classdata['props'][memberid]

                def get_typestring(name, cpp_type):
                    unsigned_char_sizes = {
                        'r_GameType': 4,
                        'Role': 2,
                        'r_eEquippedAt': 5,
                        'r_eCoalition': 2
                    }

                    type_to_typestring = {
                        'bool':             "'type': bool",
                        'unsigned long: 1': "'type': bool",
                        'unsigned long':    "'type': bool",
                        'float':            "'type': float",
                        'int':              "'type': int",
                        'struct FString':   "'type': str",
                        'struct FRotator':  "'type': 'frotator'",
                        'struct FVector':   "'type': 'fvector'",
                        'struct FName':     "'type': str",
                    }
                    try:
                        if cpp_type in ('class UClass*',
                                        'class ATgMissionObjective*',
                                        'class ATgOmegaVolume*'):
                            typestring = "'type': bitarray, 'size': 32"
                            comment = f'\t# {cpp_type} confirmed to be 32 bits'
                        elif cpp_type in ('class ATgRepInfo_TaskForce*',
                                          'class APlayerReplicationInfo*',
                                          'class APawn*',
                                          'class AActor*',
                                          'class AInventory*',
                                          'class AInventoryManager*',
                                          'class AController*'):
                            typestring = "'type': bitarray, 'size': 11"
                            comment = f'\t# {cpp_type} confirmed to be 11 bits'
                        elif cpp_type.endswith('*'):
                            typestring = "'type': bitarray, 'size': 11"
                            comment = f'\t# {cpp_type} defaulting to 11 bits'
                        elif cpp_type.endswith('[]'):
                            typestring, comment = get_typestring(name, cpp_type[:-2])
                            typestring = typestring.replace("'type'", "'type': 'array', 'subtype'", 1)
                        elif cpp_type.endswith(']'):
                            m = re.match(r'(.*)\[ (.*) ]', cpp_type)
                            elem_sizes = {'int': 32}
                            elem_type = m.group(1)
                            elem_size = elem_sizes[elem_type]
                            elem_count = int(m.group(2), 16)
                            typestring = f"'type': bitarray, 'size': {elem_size * elem_count}"
                            comment = f"\t# static array of {elem_count} {elem_type}'s"
                        elif cpp_type == 'unsigned char':
                            if name in unsigned_char_sizes:
                                typestring = f"'type': bitarray, 'size': {unsigned_char_sizes[name]}"
                                comment = f'\t# unsigned char encoded in {unsigned_char_sizes[name]} bits for {name}'
                            else:
                                typestring = f"'type': bitarray, 'size': 8"
                                comment = f'\t# unsigned char, assuming 8 bits'
                        else:
                            if cpp_type in type_to_typestring:
                                typestring = type_to_typestring[cpp_type]
                                comment = ''
                            elif cpp_type.startswith('struct') and cpp_type.split()[1] in classes_from_sdk['structs']:
                                _, struct_name = cpp_type.split()
                                struct_data = classes_from_sdk['structs'][struct_name]
                                typestring = f"'type': (\n"
                                indentation = 24 * ' '
                                for structmemberdata in struct_data:
                                    typestring += indentation + f"{{'name': '{structmemberdata['name']}',"
                                    membertypestring, membercomment = get_typestring(structmemberdata['name'], structmemberdata['type'])
                                    typestring += f" {membertypestring}}},{membercomment}\n"
                                typestring += indentation + ')'
                                comment = ''
                            else:
                                typestring = "'type': None"
                                comment = f'\t# original type was: "{cpp_type}"'
                    except KeyError:
                        typestring = "'type': None"
                        comment = f'\t# original type was: "{cpp_type}"'

                    return typestring, comment

                sdkfields = classes_from_sdk['classes'][member_data['class']]['fields']
                sdkmethods = {meth[5:] if meth.startswith('event') else meth: data for meth, data in classes_from_sdk['classes'][member_data['class']]['methods'].items()}
                if member_data['name'] in sdkfields:
                    cpp_type = sdkfields[member_data['name']]
                    typestring, comment = get_typestring(member_data['name'], cpp_type)
                    f.write(f"    '{memberid}': {{'name': '{member_data['name']}', {typestring}}},{comment}\n")

                elif member_data['name'] in sdkmethods:
                    rpc_data = sdkmethods[member_data['name']]
                    f.write(f"    '{memberid}': {{'name': 'RPC {member_data['name']}', 'type': [\n")
                    for param in rpc_data['params']:
                        f.write(f"        {{'name': '{param['name']}',\n")
                        typestring, comment = get_typestring(param['name'], param['type'])
                        f.write(f"         {typestring}}},{comment}\n")
                    f.write(f"    ]}},\n")
                else:
                    print(f'Member not found in SDK: {member_data}')
                    cpp_type = 'not_in_sdk'


            f.write(f'}}\n\n')

        f.write(f'generated_class_dict = {{\n')

        for classid in sorted(classes.keys(), key=reverse_string):
            classdata = classes[classid]
            f.write(f"    '{classid}': {{'name': '{classdata['name']}', 'props': {classdata['name']}Props}},\n")
        f.write(f'}}\n\n')


if __name__ == '__main__':
    main()