from bitarray import bitarray
import struct
import unittest

import udk


def toint(bits):
    zerobytes = bytes( (0,0,0,0) )
    longbytes = (bits.tobytes() + zerobytes)[0:4]
    return struct.unpack('<L', longbytes)[0]


class TestUdk(unittest.TestCase):

    def test_serialize_bits_to_int(self):
        params = [('10000000', '01010000', '1000', '0000', 'msb included because of low lsbs'),
                  ('00100000', '01010000', '001', '00000', 'msb excluded because of high lsbs'),
                  ('10010000', '01010000', '1001', '0000', 'msb included because it\'s 1')]

        for bits_before, max_value_bits, value_bits, bits_after, comment in params:
            with self.subTest(bits_before=bits_before,
                              max_value_bits=max_value_bits,
                              value_bits=value_bits,
                              bits_after=bits_after,
                              comment=comment):
                bits = bitarray(bits_before, endian='little')
                max_value = toint(bitarray(max_value_bits, endian='little'))
                value, bits = udk.serialize_bits_to_int(max_value, bits)
                self.assertEqual(value, toint(bitarray(value_bits, endian='little')))
                self.assertEqual(bits, bitarray(bits_after, endian='little'))

    def test_serialize_int_to_bits(self):
        params = [('01010000', '10000000', '1000', 'msb included because of low lsbs'),
                  ('01010000', '00100000', '001', 'msb excluded because of high lsbs'),
                  ('01010000', '10010000', '1001', 'msb included because it\'s 1')]

        for max_value_bits, value_bits_in, value_bits_out, comment in params:
            with self.subTest(max_value_bits=max_value_bits,
                              value_bits_in=value_bits_in,
                              value_bits_out=value_bits_out,
                              comment=comment):
                max_value = toint(bitarray(max_value_bits, endian='little'))
                value = toint(bitarray(value_bits_in, endian='little'))
                bits = udk.serialize_int_to_bits(value, max_value)
                self.assertEqual(bits, bitarray(value_bits_out, endian='little'))
