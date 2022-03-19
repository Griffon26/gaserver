from bitarray import bitarray
import json
import math
from pathlib import Path
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
            return s[::-1]

        f.write('from bitarray import bitarray\n\n')

        for classid in sorted(classes.keys(), key=reverse_string):
            classdata = classes[classid]
            f.write(f'{classdata["name"]}Props = {{\n')
            max_field_id = max(classdata['props'].keys())

            exceptions = {
                'TgPlayerController': 8,
                'TgRepInfo_Game': 6,
                'TgRepInfo_GameOpenWorld': 6,
                'TgDevice': 5,
                'TgDevice_Grenade': 5,
                'TgDevice_HitPulse': 5,
                'TgDevice_NewMelee': 5,
                'TgDevice_MeleeDualWield': 5,
                'TgDevice_Morale': 5,
                'TgDevice_NewRange': 5,
                'TgPawn_NPC': 7,
            }
            if classdata['name'] in exceptions:
                bits_for_field = exceptions[classdata['name']]
            else:
                bits_for_field = int(math.ceil(math.log(max_field_id, 2)))

            def memberid_to_bits(memberid, nbits):
                try:
                    bits = int2bitarray(memberid, nbits).to01()
                except ValueError:
                    bits = int2bitarray(memberid, nbits + 1).to01() + '_invalid'
                return bits

            classdata['props'] = {memberid_to_bits(memberid, bits_for_field): member_data for memberid, member_data in classdata['props'].items()}

            for memberid in sorted(classdata['props'].keys(), key=reverse_string):
                member_data = classdata['props'][memberid]

                def get_typestring(cpp_type):
                    type_to_typestring = {
                        'bool':             "'type': bool",
                        'unsigned long: 1': "'type': bool",
                        'unsigned long':    "'type': bool",
                        'float':            "'type': float",
                        'int':              "'type': int",
                        'unsigned char':    "'type': bitarray, 'size': 8",
                        'struct FString':   "'type': str",
                        'struct FRotator':  "'type': 'frotator'",
                        'struct FVector':   "'type': 'fvector'",
                        'struct FName':     "'type': str",
                    }
                    try:
                        if cpp_type in ('class UClass*',
                                        'class ATgMissionObjective*'):
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
                            typestring, comment = get_typestring(cpp_type[:-2])
                            typestring = typestring.replace("'type'", "'type': 'array', 'subtype'", 1)
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
                                    membertypestring, membercomment = get_typestring(structmemberdata['type'])
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
                    typestring, comment = get_typestring(cpp_type)
                    f.write(f"    '{memberid}': {{'name': '{member_data['name']}', {typestring}}},{comment}\n")

                elif member_data['name'] in sdkmethods:
                    rpc_data = sdkmethods[member_data['name']]
                    f.write(f"    '{memberid}': {{'name': 'RPC {member_data['name']}', 'type': [\n")
                    for param in rpc_data['params']:
                        f.write(f"        {{'name': '{param['name']}',\n")
                        typestring, comment = get_typestring(param['type'])
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