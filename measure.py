#! /usr/bin/env python3

import atexit
import itertools
import json
import os
import re
import shutil
import statistics
import subprocess
import tempfile

N = 5
OUTPUT = "measure.csv"

# Settings to investigate cache line size effects.
BENCHMARK_FOOTPRINT = 20971520  # getconf LEVEL3_CACHE_SIZE
BENCHMARK_ITERATIONS = 250_000_000
SIZES = itertools.chain(range(1, 127, 1), range(128, 289, 8), range(320, 4097, 32))
SETTINGS = [
    ([], {"LITTER_MULTIPLIER": "20", "LITTER_OCCUPANCY": "0.95"}),
]


def main():
    build_directory = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, build_directory)
    subprocess.run(
        ["cmake", ".", "-B", build_directory, "-DCMAKE_BUILD_TYPE=Release"], check=True
    )
    subprocess.run(["cmake", "--build", build_directory, "--parallel"], check=True)

    with open(OUTPUT, "w") as f:
        for s in SIZES:
            data = {}
            data["size"] = s

            # 1. Detect.
            subprocess.run(
                [
                    f"{build_directory}/benchmark_iterator",
                    "-f",
                    str(BENCHMARK_FOOTPRINT),
                    "-i",
                    str(BENCHMARK_ITERATIONS),
                    "-s",
                    str(s),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                env={
                    "LD_PRELOAD": f"{build_directory}/libdetector_distribution.so",
                    "DYLD_INSERT_LIBRARIES": f"{build_directory}/libdetector_distribution.dylib",
                    **os.environ,
                },
            )

            row = [s]

            # 2. Run vanilla.
            times = []
            for _ in range(N):
                stdout = subprocess.check_output(
                    [
                        f"{build_directory}/benchmark_iterator",
                        "-f",
                        str(BENCHMARK_FOOTPRINT),
                        "-i",
                        str(BENCHMARK_ITERATIONS),
                        "-s",
                        str(s),
                    ],
                    text=True,
                    env=os.environ,
                )
                times.append(
                    int(re.search(r"Done. Time elapsed: (\d+) ms.", stdout).group(1))
                )
            row.append(statistics.median(times))
            data["vanilla"] = times

            # 3. Run with all settings.
            data["settings"] = []
            for extra_args, litterer_setting in SETTINGS:
                env = {
                    "LD_PRELOAD": f"{build_directory}/liblitterer_distribution_standalone.so",
                    "DYLD_INSERT_LIBRARIES": f"{build_directory}/liblitterer_distribution_standalone.dylib",
                    **litterer_setting,
                    **os.environ,
                }
                times = []
                for _ in range(N):
                    stdout = subprocess.check_output(
                        [
                            f"{build_directory}/benchmark_iterator",
                            "-f",
                            str(BENCHMARK_FOOTPRINT),
                            "-i",
                            str(BENCHMARK_ITERATIONS),
                            "-s",
                            str(s),
                            *extra_args,
                        ],
                        text=True,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )
                    times.append(
                        int(
                            re.search(r"Done. Time elapsed: (\d+) ms.", stdout).group(1)
                        )
                    )
                row.append(statistics.median(times))
                data["settings"].append(times)

            f.write(json.dumps(data))
            f.write("\n")
            f.flush()
            print("\t".join(str(e) for e in row))


if __name__ == "__main__":
    main()
