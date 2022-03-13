#!/usr/bin/env python3
#
# Copyright (C) 2018  Maurice van der Pot <griffon26@kfk4ever.com>
#
# This file is part of taserver
# 
# taserver is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# taserver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with taserver.  If not, see <http://www.gnu.org/licenses/>.
#

from bitarray import bitarray
from itertools import zip_longest
import struct

from props import generated_class_dict

known_int_values = {
}

known_fields = {
}


class ParseError(Exception):
    def __init__(self, message, bitsleft):
        super().__init__(message)
        self.bitsleft = bitsleft

class ParserState():
    def __init__(self):
        # ID sizes are per-class (probably depends on how many members a class has)
        # - it is guaranteed to be 8 for the FirstServerObject_0
        # - it is guaranteed to be 8 for the TrPlayerController_0
        # - it is guaranteed to be 6 for the TrPlayerReplicationInfo_0
        # - it appears to be 6 for TrGameReplicationInfo_0
        # - it appears to be 7 for TrPlayerPawn_0

        FirstServerObjectProps = {
            '00000000': {'name': 'somestring',
                         'type': str}
        }

        self.class_dict = generated_class_dict
        self.class_dict[None] = {'name': 'FirstServerObject', 'props': FirstServerObjectProps}

        def reverse_keys(d):
            return {key[::-1] if key is not None else None: value for key, value in d.items()}

        #self.class_dict = reverse_keys(self.class_dict)
        #for classdef in self.class_dict.values():
        #    classdef['props'] = reverse_keys(classdef['props'])

        self.instance_count = {}
        self.channels = {}
        self.bits_carried_over = bitarray(endian='little')


def int2bitarray(n, nbits):
    bits = bitarray(endian='little')
    bits.frombytes(struct.pack('<L', n))
    return bits[:nbits]

def toint(bits):
    zerobytes = bytes( (0,0,0,0) )
    longbytes = (bits.tobytes() + zerobytes)[0:4]
    return struct.unpack('<L', longbytes)[0]

def float2bitarray(val):
    bits = bitarray(endian='little')
    bits.frombytes(struct.pack('<f', val))
    return bits

def tofloat(bits):
    return struct.unpack('<f', bits.tobytes())[0]

def getnbits(n, bits):
    if n > len(bits):
        raise ParseError('Tried to get more bits (%d) than are available (%d)' %
                             (n, len(bits)),
                         bits)
    
    return bits[0:n], bits[n:]

def getstring(bits):
    stringbytes = bits.tobytes()
    result = []
    for b in stringbytes:
        if b != 0:
            result.append(chr(b))
        else:
            break

    return ''.join(result), bits[(len(result) + 1) * 8:]

def debugbits(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        bitsbefore = args[1]
        debug = kwargs['debug']

        if debug:
            print('%s::frombitarray (entry): starting with %s%s' %
                  (self.__class__.__name__,
                   bitsbefore.to01()[0:32],
                   '...' if len(bitsbefore) > 32 else ' EOF'))
        bitsafter = func(*args, **kwargs)

        if debug:
            nbits_consumed = len(bitsbefore) - len(bitsafter)
            if bitsbefore[nbits_consumed:] != bitsafter:
                raise RuntimeError('Function not returning a tail of the input bits')
            print('%s::frombitarray (exit) : consumed \'%s\'' %
                  (self.__class__.__name__, bitsbefore.to01()[:nbits_consumed]))

            if bitsbefore[:nbits_consumed] != self.tobitarray():
                raise RuntimeError('Object %s serialized into bits is not equal to bits parsed:\n' % repr(self) +
                                   'in : %s\n' % bitsbefore[:nbits_consumed].to01() +
                                   'out: %s\n' % self.tobitarray().to01())

        return bitsafter
    
    return wrapper


class PropertyValueMultipleChoice():
    def __init__(self):
        self.value = None
        self.valuebits = None

    @debugbits
    def frombitarray(self, bits, size, values, debug = False):
        self.valuebits, bits = getnbits(size, bits)
        self.value = values.get(self.valuebits.to01(), 'Unknown')
        return bits

    def tobitarray(self):
        return self.valuebits if self.value is not None else bitarray()

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.value is not None:
            text = '%s%s (value = %s)\n' % (indent_prefix,
                                            self.valuebits.to01(),
                                            self.value)
        else:
            text = '%sempty\n' % indent_prefix
        return text

class PropertyValueString():
    def __init__(self):
        self.size = None
        self.value = None

    @debugbits
    def frombitarray(self, bits, debug = False):
        stringsizebits, bits = getnbits(32, bits)
        self.size = toint(stringsizebits)

        if self.size > 0:
            self.value, bits = getstring(bits)

            if len(self.value) + 1 != self.size:
                raise ParseError('ERROR: string size (%d) was not equal to expected size (%d)' %
                                     (len(self.value) + 1,
                                      self.size),
                                 bits)
        else:
            self.value = ''

        return bits

    def tobitarray(self):
        if self.value is not None:
            bits = int2bitarray(self.size, 32)
            if self.size > 0:
                bits.frombytes(bytes(self.value, encoding = 'latin1'))
                bits.extend('00000000')
        else:
            bits = bitarray()
        return bits
    
    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.value is not None:
            text = '%s%s (strsize = %d)\n' % (indent_prefix, int2bitarray(self.size, 32).to01(), self.size)

            if self.size > 0:
                indent_prefix += ' ' * 32        
                text += '%sx (value = "%s")\n' % (indent_prefix,
                                                  self.value)
        else:
            text = '%sempty\n' % indent_prefix
            
        return text

class PropertyValueVector():
    def __init__(self):
        self.short1 = None
        self.short2 = None
        self.short3 = None

    @debugbits
    def frombitarray(self, bits, debug = False):
        valuebits, bits = getnbits(16, bits)
        self.short1 = toint(valuebits)
        valuebits, bits = getnbits(16, bits)
        self.short2 = toint(valuebits)
        valuebits, bits = getnbits(16, bits)
        self.short3 = toint(valuebits)
        return bits

    def tobitarray(self):
        if self.short3 is not None:
            return (int2bitarray(self.short1, 16) +
                    int2bitarray(self.short2, 16) +
                    int2bitarray(self.short3, 16))
        else:
            return bitarray()
    
    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.short3 is not None:
            return '%s%s (value = (%d,%d,%d))\n' % (indent_prefix,
                                                    self.tobitarray().to01(),
                                                    self.short1,
                                                    self.short2,
                                                    self.short3)
        else:
            return '%sempty\n' % indent_prefix

class PropertyValueInt():
    def __init__(self):
        self.value = None

    @debugbits
    def frombitarray(self, bits, debug = False):
        valuebits, bits = getnbits(32, bits)
        self.value = toint(valuebits)
        return bits

    def tobitarray(self):
        return int2bitarray(self.value, 32) if self.value is not None else bitarray()
    
    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.value is not None:
            text = '%s%s (value = %d %08X%s)\n' % (indent_prefix,
                                                   self.tobitarray().to01(),
                                                   self.value,
                                                   self.value,
                                                   (' %s' % known_int_values.get(self.value, 'unknown')) if self.value in known_int_values else '')
        else:
            text = '%sempty\n' % indent_prefix
        return text


class PropertyValueFloat():
    def __init__(self):
        self.value = None

    @debugbits
    def frombitarray(self, bits, debug=False):
        valuebits, bits = getnbits(32, bits)
        self.value = tofloat(valuebits)
        return bits

    def tobitarray(self):
        return float2bitarray(self.value) if self.value is not None else bitarray()

    def tostring(self, indent=0):
        indent_prefix = ' ' * indent
        if self.value is not None:
            text = '%s%s (value = %f)\n' % (indent_prefix,
                                            self.tobitarray().to01(),
                                            self.value)
        else:
            text = '%sempty\n' % indent_prefix
        return text


class PropertyValueBool():
    def __init__(self):
        self.value = None

    @debugbits
    def frombitarray(self, bits, debug = False):
        valuebits, bits = getnbits(1, bits)
        self.value = (valuebits[0] == 1)
        return bits

    def tobitarray(self):
        return bitarray([self.value]) if self.value is not None else bitarray()

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.value is not None:
            text = '%s%s (value = %s)\n' % (indent_prefix,
                                            '1' if self.value else '0',
                                            self.value)
        else:
            text = '%sempty\n' % indent_prefix
        return text

class PropertyValueFlag():
    def __init__(self):
        pass

    @debugbits
    def frombitarray(self, bits, debug = False):
        return bits

    def tobitarray(self):
        return bitarray()

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        text = '%s(flag is set)\n' % indent_prefix
        return text
        
class PropertyValueBitarray():
    def __init__(self):
        self.value = None

    @debugbits
    def frombitarray(self, bits, size, debug = False):
        self.value, bits = getnbits(size, bits)
        return bits

    def tobitarray(self):
        return self.value if self.value is not None else bitarray()

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.value is not None:
            text = '%s%s (value)\n' % (indent_prefix, self.value.to01())
        else:
            text = '%sempty\n' % indent_prefix
        return text

class PropertyValueFVector():
    def __init__(self):
        self.vectorbits = None

    @debugbits
    def frombitarray(self, bits, debug = False):
        assert len(bits) > 4
        lengthbits, bits = getnbits(4, bits)
        length = toint(lengthbits) * 3 + 6
        self.vectorbits, bits = getnbits(length, bits)
        return bits

    def tobitarray(self):
        length = int((len(self.vectorbits) - 6) / 3)
        lengthbits = int2bitarray(length, 4)
        return lengthbits + self.vectorbits

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        if self.vectorbits is not None:
            length = int((len(self.vectorbits) - 6) / 3)
            lengthbits = int2bitarray(length, 4)
            text = '%s%s %s (FVector)\n' % (indent_prefix, lengthbits.to01(), self.vectorbits.to01())
        else:
            text = '%sempty\n' % indent_prefix
        return text


class PropertyValueMystery1():
    def __init__(self):
        self.int1 = PropertyValueInt()
        self.int2 = PropertyValueInt()
        self.int3 = PropertyValueInt()
        self.int4 = PropertyValueInt()
        self.string1 = PropertyValueString()
        self.string2 = PropertyValueString()
        self.int5 = PropertyValueInt()
        self.int6 = PropertyValueInt()
        self.string3 = PropertyValueString()

    @debugbits
    def frombitarray(self, bits, debug = False):
        bits = self.int1.frombitarray(bits, debug = debug)
        bits = self.int2.frombitarray(bits, debug = debug)
        bits = self.int3.frombitarray(bits, debug = debug)
        bits = self.int4.frombitarray(bits, debug = debug)
        bits = self.string1.frombitarray(bits, debug = debug)
        bits = self.string2.frombitarray(bits, debug = debug)
        bits = self.int5.frombitarray(bits, debug = debug)
        bits = self.int6.frombitarray(bits, debug = debug)
        bits = self.string3.frombitarray(bits, debug = debug)
        return bits

    def tobitarray(self):
        return (self.int1.tobitarray() +
                self.int2.tobitarray() +
                self.int3.tobitarray() +
                self.int4.tobitarray() +
                self.string1.tobitarray() +
                self.string2.tobitarray() +
                self.int5.tobitarray() +
                self.int6.tobitarray() +
                self.string3.tobitarray())

    def tostring(self, indent = 0):
        items = []
        items.append(self.int1.tostring(indent))
        items.append(self.int2.tostring(indent))
        items.append(self.int3.tostring(indent))
        items.append(self.int4.tostring(indent))
        items.append(self.string1.tostring(indent))
        items.append(self.string2.tostring(indent))
        items.append(self.int5.tostring(indent))
        items.append(self.int6.tostring(indent))
        items.append(self.string3.tostring(indent))
        text = ''.join(items)
        return text

class PropertyValueMystery2():
    def __init__(self):
        self.string1 = PropertyValueString()
        self.string2 = PropertyValueString()
        self.string3 = PropertyValueString()

    @debugbits
    def frombitarray(self, bits, debug = False):
        bits = self.string1.frombitarray(bits, debug = debug)
        bits = self.string2.frombitarray(bits, debug = debug)
        bits = self.string3.frombitarray(bits, debug = debug)
        return bits

    def tobitarray(self):
        return (self.string1.tobitarray() +
                self.string2.tobitarray() +
                self.string3.tobitarray())

    def tostring(self, indent = 0):
        items = []
        items.append(self.string1.tostring(indent))
        items.append(self.string2.tostring(indent))
        items.append(self.string3.tostring(indent))
        text = ''.join(items)
        return text

class PropertyValueMystery3():
    def __init__(self):
        self.string1 = PropertyValueString()
        self.string2 = PropertyValueString()

    @debugbits
    def frombitarray(self, bits, debug = False):
        bits = self.string1.frombitarray(bits, debug = debug)
        bits = self.string2.frombitarray(bits, debug = debug)
        return bits

    def tobitarray(self):
        return (self.string1.tobitarray() +
                self.string2.tobitarray())

    def tostring(self, indent = 0):
        items = []
        items.append(self.string1.tostring(indent))
        items.append(self.string2.tostring(indent))
        text = ''.join(items)
        return text


class PropertyValueUdkArray():
    def __init__(self, subtype, size):
        self._index = None
        self.subtype = subtype
        self.size = size
        self.value = None

    @debugbits
    def frombitarray(self, bits, debug=False):
        self.index, bits = getnbits(8, bits)

        if isinstance(self.subtype, tuple):
            self.value = PropertyValueStruct(self.subtype)
            bits = self.value.frombitarray(bits, debug=debug)
        else:
            try:
                self.value, bits = parse_basic_property('element', self.subtype, bits, self.size, debug=debug)
            except:
                self.value = PropertyValueBitarray()
                raise
        return bits

    def tobitarray(self):
        bits = self.index.copy()
        bits.extend(self.value.tobitarray())
        return bits

    def tostring(self, indent=0):
        indent_prefix = ' ' * indent
        text = '%s%s (array index)\n' % (indent_prefix, self.index.to01())
        text += self.value.tostring(indent + 4)
        return text


class PropertyValueArray:
    def __init__(self):
        self.length = None
        self.fields = []

    @debugbits
    def frombitarray(self, bits, debug=False):
        lengthbits, bits = getnbits(16, bits)
        self.length = toint(lengthbits)

        self.fields = []
        for i in range(self.length):
            field = PropertyValueField()
            self.fields.append(field)
            bits = field.frombitarray(bits, debug=debug)

        return bits

    def tobitarray(self):
        bits = int2bitarray(self.length, 16)
        for field in self.fields:
            bits.extend(field.tobitarray())
        return bits

    def tostring(self, indent=0):
        indent_prefix = ' ' * indent
        if self.length is not None:
            text = '%s%s (length = %d)\n' % (indent_prefix, int2bitarray(self.length, 16).to01(), self.length)

            for field in self.fields:
                text += field.tostring(indent + 4)
        else:
            text = '%sempty\n' % indent_prefix

        return text


class PropertyValueArrayOfArrays:
    def __init__(self):
        self.length = None
        self.arrays = []

    @debugbits
    def frombitarray(self, bits, debug=False):
        lengthbits, bits = getnbits(16, bits)
        self.length = toint(lengthbits)

        self.arrays = []
        for i in range(self.length):
            array = PropertyValueArray()
            self.arrays.append(array)
            bits = array.frombitarray(bits, debug=debug)

        return bits

    def tobitarray(self):
        bits = int2bitarray(self.length, 16)
        for array in self.arrays:
            bits.extend(array.tobitarray())
        return bits

    def tostring(self, indent=0):
        indent_prefix = ' ' * indent
        if self.length is not None:
            text = '%s%s (length = %d)\n' % (indent_prefix, int2bitarray(self.length, 16).to01(), self.length)

            for array in self.arrays:
                text += array.tostring(indent + 4)
        else:
            text = '%sempty\n' % indent_prefix

        return text



class PropertyValueField:
    fieldmap = {
        '0000111010000000': PropertyValueArrayOfArrays,
        '1111011010000000': PropertyValueArrayOfArrays,
        '0011011000100000': 64,
        '1101100100100000': PropertyValueFloat
    }

    def __init__(self):
        self.ident = None
        self.data = None

    @debugbits
    def frombitarray(self, bits, debug=False):
        idbits, bits = getnbits(16, bits)
        self.ident = toint(idbits)

        if idbits.to01() in self.fieldmap:
            fielddef = self.fieldmap[idbits.to01()]
            if isinstance(fielddef, int):
                self.data, bits = getnbits(fielddef, bits)
            else:
                self.data = fielddef()
                bits = self.data.frombitarray(bits, debug=debug)
        else:
            self.data = PropertyValueInt()
            bits = self.data.frombitarray(bits, debug=debug)

        return bits

    def tobitarray(self):
        bits = int2bitarray(self.ident, 16)
        if isinstance(self.data, bitarray):
            bits.extend(self.data)
        else:
            bits.extend(self.data.tobitarray())
        return bits

    def tostring(self, indent=0):
        indent_prefix = ' ' * indent
        if self.ident is not None:
            fielddesc = (', %s' % known_fields[self.ident]) if self.ident in known_fields else ''
            text = '%s%s (field ident = %04X%s)\n' % (indent_prefix, int2bitarray(self.ident, 16).to01(), self.ident, fielddesc)
            if isinstance(self.data, bitarray):
                text += '%s%s (field value)\n' % (' ' * (indent + 16), self.data.to01())
            else:
                text += self.data.tostring(indent + 16)
        else:
            text = '%sempty\n' % indent_prefix

        return text


class PropertyValueInteresting:
    def __init__(self):
        self.prefixbits = None
        self.length = None
        self.fields = []

    @debugbits
    def frombitarray(self, bits, debug=False):
        self.prefixbits, bits = getnbits(28, bits)

        idbits, bits = getnbits(16, bits)
        self._id = toint(idbits)
        lengthbits, bits = getnbits(16, bits)
        self.length = toint(lengthbits)

        self.fields = []
        for i in range(self.length):
            field = PropertyValueField()
            self.fields.append(field)
            bits = field.frombitarray(bits, debug=debug)

        return bits

    def tobitarray(self):
        bits = self.prefixbits[:]
        bits.extend(int2bitarray(self._id, 16))
        bits.extend(int2bitarray(self.length, 16))
        for field in self.fields:
            bits.extend(field.tobitarray())
        return bits

    def tostring(self, indent=0):
        indent_prefix = ' ' * indent
        if self.prefixbits is not None:
            text = '%s%s (prefix for size %d)\n' % (indent_prefix, self.prefixbits.to01(), toint(self.prefixbits[:9]))
            text += '%s%s (id = %04X)\n' % (indent_prefix, int2bitarray(self._id, 16).to01(), self._id)
            text += '%s%s (number of fields = %d)\n' % (indent_prefix, int2bitarray(self.length, 16).to01(), self.length)

            for field in self.fields:
                text += field.tostring(indent)
        else:
            text = '%sempty\n' % indent_prefix

        return text


def parse_basic_property(propertyname, propertytype, bits, size=None, debug=False):
    if propertytype is str:
        value = PropertyValueString()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype is int:
        value = PropertyValueInt()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype is float:
        value = PropertyValueFloat()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype is bool:
        value = PropertyValueBool()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype is 'flag':
        value = PropertyValueFlag()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype is bitarray:
        value = PropertyValueBitarray()
        #if size is None:
        #    raise RuntimeError("Coding error: size can't be None for bitarray")
        bits = value.frombitarray(bits, size, debug=debug)
    elif propertytype == 'fvector':
        value = PropertyValueFVector()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype == PropertyValueMystery1:
        value = PropertyValueMystery1()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype == PropertyValueMystery2:
        value = PropertyValueMystery2()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype == PropertyValueMystery3:
        value = PropertyValueMystery3()
        bits = value.frombitarray(bits, debug=debug)
    elif propertytype == PropertyValueInteresting:
        value = PropertyValueInteresting()
        bits = value.frombitarray(bits, debug=debug)
    else:
        raise ParseError('Coding error: propertytype of property %s has invalid value: %s' % (propertyname, propertytype), bits)

    return value, bits


class PropertyValueStruct():
    def __init__(self, member_list):
        self.member_list = member_list
        self.values = []

    @debugbits
    def frombitarray(self, bits, debug = False):
        self.values = []
        for member in self.member_list:
            propertyname = member.get('name', None)
            propertytype = member.get('type', None)
            propertysize = member.get('size', None)
            value, bits = parse_basic_property(propertyname, propertytype, bits, propertysize, debug = debug)
            self.values.append(value)

        return bits

    def tobitarray(self):
        allbits = bitarray()
        for member in self.values:
            allbits += member.tobitarray()
        return allbits

    def tostring(self, indent = 0):
        items = []
        for member, value in zip(self.member_list, self.values):
            items.append(value.tostring(indent)[:-1] + ' (%s)\n' % member['name'])
        text = ''.join(items)
        return text


class PropertyValueParams():
    def __init__(self, param_list):
        self.param_list = param_list
        self.presence = []
        self.values = []

    @debugbits
    def frombitarray(self, bits, debug = False):

        self.values = []
        for member in self.param_list:
            propertyname = member.get('name', None)
            propertytype = member.get('type', None)
            propertysize = member.get('size', None)

            present, bits = getnbits(1, bits)
            self.presence.append(present[0])
            if present[0] == 1:
                value, bits = parse_basic_property(propertyname, propertytype, bits, propertysize, debug = debug)
            else:
                value = None
            self.values.append(value)

        return bits

    def tobitarray(self):
        allbits = bitarray()
        for present, value in zip_longest(self.presence, self.values):
            if present:
                allbits += bitarray([1])
                if value is not None:
                    allbits += value.tobitarray()
            else:
                allbits += bitarray([0])
        return allbits

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        items = []
        for member, present, value in zip_longest(self.param_list, self.presence, self.values):
            if present:
                items.append('%s1 (%s param present)\n' % (indent_prefix, member['name']))
                if value is not None:
                    items.append(value.tostring(indent)[:-1] + '(%s)\n' % member['name'])
            else:
                items.append('%s0 (%s param absent)\n' % (indent_prefix, member['name']))
        text = ''.join(items)
        return text


class ObjectProperty():
    def __init__(self, id_size = 6):
        self.propertyid_size = id_size
        self.propertyid = None
        self.property_ = { 'name' : 'Unknown' }
        self.value = None

    @debugbits
    def frombitarray(self, bits, class_, debug = False):
        propertyidbits, bits = getnbits(self.propertyid_size, bits)
        self.propertyid = toint(propertyidbits)
        
        propertykey = propertyidbits.to01()
        property_ = class_['props'].get(propertykey, {'name' : 'Unknown'})
        self.property_ = property_

        propertyname = property_.get('name', None)
        propertytype = property_.get('type', None)
        propertysubtype = property_.get('subtype', None)
        propertysize = property_.get('size', None)
        propertyvalues = property_.get('values', None)
        if propertyvalues:
            self.value = PropertyValueMultipleChoice()
            bits = self.value.frombitarray(bits, propertysize, propertyvalues, debug = debug)
        
        elif propertytype:
            if isinstance(propertytype, list):
                self.value = PropertyValueParams(propertytype)
                bits = self.value.frombitarray(bits, debug=debug)
            elif isinstance(propertytype, tuple):
                self.value = PropertyValueStruct(propertytype)
                bits = self.value.frombitarray(bits, debug=debug)
            elif propertytype == 'array':
                self.value = PropertyValueUdkArray(propertysubtype, propertysize)
                bits = self.value.frombitarray(bits, debug=debug)
            else:
                try:
                    self.value, bits = parse_basic_property(propertyname, propertytype, bits, propertysize, debug = debug)
                except:
                    self.value = PropertyValueBitarray()
                    raise
        else:
            raise ParseError('Unknown property %s for class %s' %
                                 (propertykey, class_['name']),
                             bits)
        
        return bits

    def tobitarray(self):
        bits = bitarray(endian='little')
        if self.propertyid is not None:
            bits.extend(int2bitarray(self.propertyid, self.propertyid_size))
        if self.value is not None:
            bits.extend(self.value.tobitarray())
        return bits

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        text = ''
        if self.propertyid is not None:
            propertykey = int2bitarray(self.propertyid, self.propertyid_size).to01()
            text += '%s%s (property = %s)\n' % (indent_prefix,
                                               propertykey,
                                               self.property_['name'])
        if self.value is not None:
            text += self.value.tostring(indent = indent + len(propertykey))
        return text


class FirstServerObjectInstance:
    def __init__(self):
        pass

    @debugbits
    def frombitarray(self, bits, class_, state, debug=False):
        self.bitsfromprevious = state.bits_carried_over
        self.bitsfornext = None
        state.bits_carried_over = bitarray(endian='little')
        self.originalbits = bits.copy()

        bits = self.bitsfromprevious + bits

        self.bunches = []

        if bits.length() == 4000:
            pass
        else:
            while bits:
                bits_at_start_of_loop = bits.copy()
                try:
                    field1, bits = getnbits(16, bits)
                    field2, bits = getnbits(16, bits)
                    field3, bits = getnbits(16, bits)
                    lengthbits, bits = getnbits(16, bits)
                    stringlength = toint(lengthbits)
                    stringbits, bits = getnbits(stringlength * 8, bits)
                    string = ''.join(chr(b) for b in stringbits.tobytes())
                    if string.startswith('WELCOME'):
                        field4 = None
                    else:
                        field4, bits = getnbits(32, bits)
                    self.bunches.append((field1, field2, field3, string, field4))
                except ParseError:
                    self.bitsfornext = bits_at_start_of_loop
                    state.bits_carried_over = bits_at_start_of_loop
                    break

        return bitarray(endian='little')

    def tobitarray(self):
        return self.originalbits

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        text = ''
        if self.bitsfromprevious:
            text += f'{indent_prefix}({self.bitsfromprevious.length()} bits carried over from previous payload)\n'

        if self.originalbits.length() == 4000:
            text += f'{indent_prefix}{self.originalbits.to01()}\n'
        else:
            for field1, field2, field3, string, field4 in self.bunches:
                text += (f'{indent_prefix}{field1.to01()}\n'
                         f'{indent_prefix}{field2.to01()}\n'
                         f'{indent_prefix}{field3.to01()}\n'
                         f'{indent_prefix}{int2bitarray(len(string), 16).to01()} "{string}"\n')
                if field4 is not None:
                    text += f'{indent_prefix}{field4.to01()}\n'

        if self.bitsfornext:
            text += f'{indent_prefix}{self.bitsfornext.length()} bits remaining for next payload: {self.bitsfornext.to01()}\n'

        return text

class ObjectInstance:
    def __init__(self, is_rpc = False):
        self.class_ = None
        self.properties = []
        self.is_rpc = is_rpc
    
    @debugbits
    def frombitarray(self, bits, class_, state, debug = False):

        while bits:
            property_ = ObjectProperty(id_size = class_['idsize'])
            self.properties.append(property_)
            bits = property_.frombitarray(bits, class_, debug = debug)

        return bits

    def tobitarray(self):
        bits = bitarray(endian = 'little')
        for prop in self.properties:
            bits.extend(prop.tobitarray())
        return bits
    
    def tostring(self, indent = 0):
        items = [prop.tostring(indent) for prop in self.properties]
        return ''.join(items)


class ObjectClass():
    def __init__(self):
        self.classid = None

    def getclasskey(self):
        classbits = int2bitarray(self.classid, 32)
        #if classbits[0:5] == bitarray('10001'):
        #    classbits[5:] = False
        return classbits.to01()

    @debugbits
    def frombitarray(self, bits, state, debug = False):
        classbits, bits = getnbits(32, bits)
        self.classid = toint(classbits)
        
        classkey = self.getclasskey()
        if classkey not in state.class_dict:
            classname = 'unknown%d' % len(state.class_dict)
            state.class_dict[classkey] = {'name': classname,
                                          'props': {}}

        return bits

    def tobitarray(self):
        bits = bitarray(endian = 'little')
        if self.classid is not None:
            bits.extend(int2bitarray(self.classid, 32))
        return bits

class PayloadData():

    def __init__(self, reliable = False):
        self.reliable = reliable
        self.size = None
        self.object_class = None
        self.flags = None
        self.object_deleted = False
        self.instancename = None
        self.instance = None
        self.bitsleftreason = None
        self.bitsleft = None
        self.originalpayloadsizebits = None

    @debugbits
    def frombitarray(self, bits, channel, state, debug = False):
        payloadsizebits, bits = getnbits(12, bits)

        self.originalpayloadsizebits = payloadsizebits
        if toint(payloadsizebits) >= toint(bitarray('00000000001101', endian='little')):
            payloadsizebits = payloadsizebits[:-1]
            bits.insert(0, True)
            self.shortened = True

        self.nr_of_payload_bits = len(payloadsizebits)
        self.size = toint(payloadsizebits)

        payloadbits, bits = getnbits(self.size, bits)
        originalpayloadbits = bitarray(payloadbits)

        try:
            if channel not in state.channels:
                newinstance = True
                self.object_class = ObjectClass()
                print(f'length of bits before parsing object: {len(payloadbits)}')
                payloadbits = self.object_class.frombitarray(payloadbits, state, debug = debug)
                if len(payloadbits) > 11:
                    self.flags, payloadbits = getnbits(11, payloadbits)
                    #if self.flags != bitarray('00000010101', endian='little'):
                    #    print('blabla')
                    #    payloadbits = self.flags + payloadbits
                    #    self.flags = None


                class_ = state.class_dict[self.object_class.getclasskey() if channel != 0 else None]
                classname = class_['name']

                prop_keys = list(class_['props'].keys())
                class_['idsize'] = len(prop_keys[0]) if prop_keys else 6

                state.instance_count[classname] = state.instance_count.get(classname, -1) + 1
                instancename = '%s_%d' % (classname, state.instance_count[classname])
                state.channels[channel] = { 'class' : class_,
                                            'instancename' : instancename }
            else:
                newinstance = False
                class_ = state.channels[channel]['class']
                classname = class_['name']
                instancename = state.channels[channel]['instancename']

            self.instancename = instancename
            if classname == 'FirstServerObject':
                self.instance = FirstServerObjectInstance()
            else:
                self.instance = ObjectInstance(is_rpc = self.reliable and not newinstance)
            payloadbits = self.instance.frombitarray(payloadbits, class_, state, debug = debug)
            
            if payloadbits:
                raise ParseError('Bits of payload left over',
                                 payloadbits)

            if self.size == 0:
                self.object_deleted = True
                del state.channels[channel]
            
        except ParseError as e:
            self.bitsleftreason = str(e)
            self.bitsleft = e.bitsleft

        return bits

    def tobitarray(self):
        bits = bitarray(endian = 'little')

        if self.size is not None:
            bits.extend(int2bitarray(self.size, self.nr_of_payload_bits))
        if self.object_class is not None:
            bits.extend(self.object_class.tobitarray())
            if self.flags:
                bits.extend(self.flags)
        if self.instance is not None:
            bits.extend(self.instance.tobitarray())
        if self.bitsleft is not None:
            bits.extend(self.bitsleft)
            
        return bits
    
    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        text = ''

        if self.size is not None:      
            if self.nr_of_payload_bits != len(self.originalpayloadsizebits):
                shortened_text = ', shortened from %s' % self.originalpayloadsizebits.to01()
            else:
                shortened_text = ''
            text += ('%s%s (payloadsize = %d%s)\n' % (indent_prefix,
                                                      int2bitarray(self.size, self.nr_of_payload_bits).to01(),
                                                      self.size,
                                                      shortened_text))
            indent += self.nr_of_payload_bits
            
        if self.object_class is not None:
            text += '%s%s (new object %s)\n' % (' ' * indent,
                                                self.object_class.tobitarray().to01(),
                                                self.instancename)
            indent += 32
            text += '%s%s (flags)\n' % (' ' * indent,
                                        self.flags.to01() if self.flags else None)
        elif self.object_deleted:
            text += '%sx (destroyed object = %s)\n' % (' ' * indent,
                                                       self.instancename)
            indent += 1
        else:
            text += '%sx (object = %s)\n' % (' ' * indent,
                                             self.instancename)
            indent += 1

        if self.instance is not None:
            text += self.instance.tostring(indent = indent)
            
        if self.bitsleft is not None:
            text += ' ' * indent + self.bitsleft.to01() + ' (rest of payload)\n'
            
        return text

class ChannelData():
    def __init__(self):
        self.channel = None
        self.counter = None
        self.unknownbits = None
        self.payload = None

    @debugbits
    def frombitarray(self, bits, with_counter, state, debug = False):
        channelbits, bits = getnbits(10, bits)
        self.channel = toint(channelbits)

        if with_counter:
            counterbits, bits = getnbits(5, bits)
            self.counter = toint(counterbits)

            self.unknownbits, bits = getnbits(8, bits)

        self.payload = PayloadData(reliable = with_counter)
        bits = self.payload.frombitarray(bits, self.channel, state, debug = debug)
        return bits

    def tobitarray(self):
        bits = int2bitarray(self.channel, 10)
        if self.counter is not None:
            bits.extend(int2bitarray(self.counter, 5))
            bits.extend(self.unknownbits)
        bits.extend(self.payload.tobitarray())
        return bits
    
    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        items = []
        items.append('%s (channel = %d)\n' % (int2bitarray(self.channel, 10).to01(),
                                              self.channel))
        indent += 10
        if self.counter is not None:
            items.append('          %s (counter = %d)\n' %
                         (int2bitarray(self.counter, 5).to01(),
                          self.counter))
            items.append('               %s\n' % self.unknownbits.to01())
            indent += 13
        text = ''.join(['%s%s' % (indent_prefix, item) for item in items])
        text += self.payload.tostring(indent = indent)
        return text

class PacketData():
    def __init__(self):
        self.flag1a = None
        self.unknownbits11 = None
        self.unknownbits10 = None
        self.channel_data = None

    @debugbits
    def frombitarray(self, bits, state, debug = False):

        self.flag1a, bits = getnbits(2, bits)
        if self.flag1a == bitarray('11'):
            self.unknownbits11 = True
            self.flag1a = None
            self.flag1a, bits = getnbits(2, bits)

        if self.flag1a == bitarray('00'):
            channel_with_counter = False
        elif self.flag1a == bitarray('01'):
            channel_with_counter = True
        elif self.flag1a == bitarray('10'):
            channel_with_counter = True
            self.unknownbits10, bits = getnbits(2, bits)
            if self.unknownbits10 != bitarray('11'):
                raise ParseError('Unexpected value for unknownbits10: %s' %
                                     self.unknownbits10.to01(),
                                 bits)
            
        else:
            raise ParseError('Unexpected value for flag1a: %s' % self.flag1a.to01(),
                             bits)

        self.channel_data = ChannelData()
        bits = self.channel_data.frombitarray(bits, channel_with_counter, state, debug = debug)
            
        return bits

    def tobitarray(self):
        bits = bitarray(endian = 'little')
        if self.unknownbits11:
            bits.extend('11')
        if self.flag1a:
            bits.extend(self.flag1a)
        if self.unknownbits10 is not None:
            bits.extend(self.unknownbits10)

        if self.channel_data:
            bits.extend(self.channel_data.tobitarray())

        return bits
    
    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        items = []
        if self.unknownbits11 is not None:
            items.append('11 (flag1a = 3)\n')
        if self.flag1a is not None:
            items.append('%s (flag1a = %d)\n' % (self.flag1a.to01(),
                                                 toint(self.flag1a)))
        if self.unknownbits10 is not None:
            items.append('%s\n' % self.unknownbits10.to01())
                         
        text = ''.join(['%s%s' % (indent_prefix, item) for item in items])
        if self.channel_data is not None:
            text += self.channel_data.tostring(indent = indent + 2)
        return text

class PacketAck():
    def __init__(self):
        self.acknr = None

    @debugbits
    def frombitarray(self, bits, debug = False):
        acknrbits, bits = getnbits(14, bits)
        self.acknr = toint(acknrbits)
        return bits

    def tobitarray(self):
        return int2bitarray(self.acknr, 14)

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        return ('%s%s (acknr = %d)\n' % (indent_prefix,
                                         self.tobitarray().to01(),
                                         self.acknr))

class Packet():
    def __init__(self):
        self.seqnr = None
        self.parts = []
        self.paddingbits = None

    @debugbits
    def frombitarray(self, bits, state, debug = False):
        original_bits = bits.copy()
        original_nbits = len(bits)
        
        seqnr, bits = getnbits(14, bits)
        self.seqnr = toint(seqnr)

        while bits:
            flag1, bits = getnbits(1, bits)
            if flag1 == bitarray('0'):
                part = PacketData()
                self.parts.append(part)
                bits = part.frombitarray(bits, state, debug = debug)
            elif len(bits) >= 14:
                part = PacketAck()
                self.parts.append(part)
                bits = part.frombitarray(bits, debug = debug)
            else:
                # the end
                break

        parsed_nbits = len(self.tobitarray())

        if len(bits) != original_nbits - parsed_nbits:
            raise ParseError(f'Coding error: parsed bits + unparsed bits does not equal total bits: '
                               f'parsed so far: {self.tostring(0)}\n'
                               f'Original bits: {original_bits.to01()}\n'
                               f'Parsed bits  : {self.tobitarray().to01()}', bitarray())

        nr_of_padding_bits = 8 - (parsed_nbits % 8)
        if len(bits) != nr_of_padding_bits:
            raise ParseError('Left over bits at the end of the packet',
                             bits)

        self.paddingbits, bits = getnbits(nr_of_padding_bits, bits)
        return bits

    def tobitarray(self):
        bits = int2bitarray(self.seqnr, 14)
        for part in self.parts:
            if isinstance(part, PacketData):
                bits.extend('0')
            else:
                bits.extend('1')
            bits.extend(part.tobitarray())
        bits.extend('1')
        if self.paddingbits:
            bits += self.paddingbits
        return bits

    def tostring(self, indent = 0):
        indent_prefix = ' ' * indent
        
        databits = self.tobitarray()
        packetbits = bitarray(databits)
        packetbits.fill()
        size = len(packetbits) / 8
        
        text = []
        text.append('%sPacket with size %d\n' % (indent_prefix, size))
        if self.seqnr is not None:
            text.append('%s%s (seqnr = %d)\n' % (indent_prefix,
                                                 int2bitarray(self.seqnr, 14).to01(),
                                                 self.seqnr))

            indent = indent + 14
            
        indent_prefix = ' ' * indent
        for part in self.parts:
            if isinstance(part, PacketData):
                text.append('%s0 (flag1 = 0)\n' % indent_prefix)
            else:
                text.append('%s1 (flag1 = 1)\n' % indent_prefix)
            text.append(part.tostring(indent = indent + 1))

        text.append('%s1 (flag1 = 1)\n' % indent_prefix)
            
        if self.paddingbits:
            text.append('    Bits left over in the last byte: %s\n' % self.paddingbits.to01())
        
        return ''.join(text)

class Parser():
    def __init__(self):
        self.parser_state = ParserState()

    def parsepacket(self, bits, debug = False, exception_on_failure = True):
        packet = Packet()
        bitsleft = None
        errormsg = None
        try:
            packet.frombitarray(bits, self.parser_state, debug = debug)
        except ParseError as e:
            errormsg = str(e)
            bitsleft = e.bitsleft
            if exception_on_failure:
                raise

        if exception_on_failure:
            return packet
        else:
            return packet, bitsleft, errormsg
