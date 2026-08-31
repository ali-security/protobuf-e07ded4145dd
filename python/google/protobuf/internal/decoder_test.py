# -*- coding: utf-8 -*-
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Test decoder."""

import unittest

from google.protobuf import message
from google.protobuf.internal import api_implementation
from google.protobuf.internal import decoder
from google.protobuf.internal import testing_refleaks
from google.protobuf.internal import wire_format

from google.protobuf import struct_pb2
from google.protobuf import unittest_pb2


@testing_refleaks.TestCase
class DecoderTest(unittest.TestCase):

  def test_decode_unknown_group_field_too_many_levels(self):
    data = memoryview(b'\023' * 5_000_000)
    self.assertRaisesRegex(
        message.DecodeError,
        'Error parsing message',
        decoder._DecodeUnknownField,
        data,
        1,
        wire_format.WIRETYPE_START_GROUP,
    )

  def _MakeRecursiveGroupMessage(self, n):
    """Serializes a message nested 4 * n + 1 levels deep through a group."""
    msg = unittest_pb2.TestMutualRecursionA()
    sub = msg
    for _ in range(n):
      sub = sub.subgroup.sub_message.b.a
    sub.bb.optional_int32 = 1
    return msg.SerializeToString()

  def test_decode_group_field_ok_sized(self):
    data = self._MakeRecursiveGroupMessage(24)  # 97 levels of nesting.
    msg = unittest_pb2.TestMutualRecursionA()
    msg.ParseFromString(data)
    self.assertTrue(msg.HasField('subgroup'))

  def test_decode_group_field_too_many_levels(self):
    data = self._MakeRecursiveGroupMessage(30)  # 121 levels of nesting.
    msg = unittest_pb2.TestMutualRecursionA()
    with self.assertRaises(message.DecodeError) as context:
      msg.ParseFromString(data)
    self.assertIn('Error parsing message', str(context.exception))
    if api_implementation.Type() == 'python':
      self.assertIn('too many levels of nesting', str(context.exception))

  def test_decode_group_field_respects_recursion_limit(self):
    if api_implementation.Type() != 'python':
      self.skipTest('SetRecursionLimit only applies to the python decoder')
    data = self._MakeRecursiveGroupMessage(30)  # 121 levels of nesting.
    msg = unittest_pb2.TestMutualRecursionA()
    decoder.SetRecursionLimit(200)
    try:
      msg.ParseFromString(data)
    finally:
      decoder.SetRecursionLimit(decoder.DEFAULT_RECURSION_LIMIT)
    self.assertTrue(msg.HasField('subgroup'))

  def _MakeRecursiveMapMessage(self, n):
    """Serializes a Struct nested n levels deep through its map<string, Value>."""
    # Struct.fields is a map<string, Value> and Value.struct_value is a Struct,
    # so each level descends through the map decoder (DecodeMap).
    root = struct_pb2.Struct()
    sub = root
    for _ in range(n):
      sub = sub.fields['x'].struct_value
    return root.SerializeToString()

  def test_decode_map_value_ok_sized(self):
    data = self._MakeRecursiveMapMessage(20)
    msg = struct_pb2.Struct()
    msg.ParseFromString(data)
    self.assertIn('x', msg.fields)

  def test_decode_map_value_too_many_levels(self):
    data = self._MakeRecursiveMapMessage(200)
    msg = struct_pb2.Struct()
    with self.assertRaises(message.DecodeError) as context:
      msg.ParseFromString(data)
    if api_implementation.Type() == 'python':
      self.assertIn('too many levels of nesting', str(context.exception))


if __name__ == '__main__':
  unittest.main()
