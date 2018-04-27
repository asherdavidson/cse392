from construct import Int32ub, PascalString
import json

class Message():
    @classmethod
    def build(cld, obj):
        return PascalString(Int32ub, "utf8").build(json.dumps(obj))

    @classmethod
    def parse(cls, msg):
        json_str = PascalString(Int32ub, "utf8").parse(msg)
        return json.loads(json_str)

    @classmethod
    def parse_length(cls, buf):
        return Int32ub.parse(buf)
