import argparse
from enum import Enum
import struct

# Sync with logger Event struct.
EVENT_FORMAT = "BNQQ"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)


class EventType(Enum):
    Null = 0
    Allocation = 1
    Reallocation = 2
    Free = 3


N_IGNORED_BITS = 12  # 6 -> 64, cache line size, 12 -> 4096, page size


def main(args: argparse.Namespace) -> None:
    count = 0
    size_by_pointer = {}
    with open(args.input, "rb") as f:
        while True:
            event = f.read(EVENT_SIZE)

            if not event:
                break

            event_type, size, pointer, result = struct.unpack(EVENT_FORMAT, event)
            assert event_type != EventType.Null
            if event_type == EventType.Allocation:
                assert result not in size_by_pointer
                size_by_pointer[result] = size
            elif event_type == EventType.Reallocation:
                del size_by_pointer[pointer]
                assert result not in size_by_pointer
                size_by_pointer[result] = size
            elif event_type == EventType.Free:
                del size_by_pointer[pointer]
            count += 1
    print(count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=str,
        help="input file, generated by the logger tool",
        default="events.bin",
    )
    main(parser.parse_args())
