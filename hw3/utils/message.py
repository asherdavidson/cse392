from construct import Int32ub, PascalString
import json

class Message():
    struct = PascalString(Int32ub, "utf8")
    @classmethod
    def build(cls, obj):
        return cls.struct.build(json.dumps(obj))

    @classmethod
    def parse(cls, msg):
        json_str = cls.struct.parse(msg)
        return json.loads(json_str)
