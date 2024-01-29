#! /usr/bin/env python3

import itertools
import os
import re
import shutil
import subprocess
import tempfile

N = 5
OUTPUT = "measure.csv"

BENCHMARK_N = 50000
BENCHMARK_I = 5000


def main():
    build_directory = tempfile.mkdtemp()
    subprocess.run(
        f"cmake . -B {build_directory} -DCMAKE_BUILD_TYPE=Release",
        shell=True,
        check=True,
    )
    subprocess.run(
        f"cmake --build {build_directory} --parallel", shell=True, check=True
    )

    with open(OUTPUT, "w") as f:
        for s in itertools.chain(range(8, 289, 8), range(320, 4097, 32)):
            print(f"Testing with s = {s}...")
            # 1. Detect.
            subprocess.run(
                f"{build_directory}/benchmark_iterator -n {BENCHMARK_N} -i {BENCHMARK_I} -s {s} --max-chunk-size 8",
                shell=True,
                check=True,
                env={
                    "LD_PRELOAD": f"{build_directory}/libdetector_distribution.so",
                    "DYLD_INSERT_LIBRARIES": f"{build_directory}/libdetector_distribution.dylib",
                    **os.environ,
                },
                stdout=subprocess.DEVNULL,
            )

            # 2. Run vanilla.
            times_ms_2 = []
            for _ in range(N):
                stdout = subprocess.check_output(
                    f"{build_directory}/benchmark_iterator -n {BENCHMARK_N} -i {BENCHMARK_I} -s {s} --max-chunk-size 8",
                    shell=True,
                    text=True,
                )
                m = re.search(r"Done. Time elapsed: (\d+) ms.", stdout)
                assert m
                times_ms_2.append(int(m.group(1)))

            # 3. Run with litterer.
            times_ms_3 = []
            for _ in range(N):
                stdout = subprocess.check_output(
                    f"{build_directory}/benchmark_iterator -n {BENCHMARK_N} -i {BENCHMARK_I} -s {s} --max-chunk-size 8",
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    env={
                        "LD_PRELOAD": f"{build_directory}/liblitterer_distribution_standalone.so",
                        "DYLD_INSERT_LIBRARIES": f"{build_directory}/liblitterer_distribution_standalone.dylib",
                        **os.environ,
                    },
                )
                m = re.search(r"Done. Time elapsed: (\d+) ms.", stdout)
                assert m
                times_ms_3.append(int(m.group(1)))

            # 4. Run with sweetened litterer.
            times_ms_4 = []
            for _ in range(N):
                stdout = subprocess.check_output(
                    f"{build_directory}/benchmark_iterator -n {BENCHMARK_N} -i {BENCHMARK_I} -s {s} --max-chunk-size 8",
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    env={
                        "LD_PRELOAD": f"{build_directory}/liblitterer_distribution_standalone.so",
                        "DYLD_INSERT_LIBRARIES": f"{build_directory}/liblitterer_distribution_standalone.dylib",
                        "LITTER_MULTIPLIER": "1",
                        "LITTER_OCCUPANCY": "0.4",
                        **os.environ,
                    },
                )
                m = re.search(r"Done. Time elapsed: (\d+) ms.", stdout)
                assert m
                times_ms_4.append(int(m.group(1)))

            # 5. Run with zero litterer.
            times_ms_5 = []
            for _ in range(N):
                stdout = subprocess.check_output(
                    f"{build_directory}/benchmark_iterator -n {BENCHMARK_N} -i {BENCHMARK_I} -s {s} --max-chunk-size 8",
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    env={
                        "LD_PRELOAD": f"{build_directory}/liblitterer_distribution_standalone.so",
                        "DYLD_INSERT_LIBRARIES": f"{build_directory}/liblitterer_distribution_standalone.dylib",
                        "LITTER_MULTIPLIER": "5",
                        "LITTER_OCCUPANCY": "0",
                        **os.environ,
                    },
                )
                m = re.search(r"Done. Time elapsed: (\d+) ms.", stdout)
                assert m
                times_ms_5.append(int(m.group(1)))

            # 6. Run with one litterer.
            times_ms_6 = []
            for _ in range(N):
                stdout = subprocess.check_output(
                    f"{build_directory}/benchmark_iterator -n {BENCHMARK_N} -i {BENCHMARK_I} -s {s} --max-chunk-size 8",
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    env={
                        "LD_PRELOAD": f"{build_directory}/liblitterer_distribution_standalone.so",
                        "DYLD_INSERT_LIBRARIES": f"{build_directory}/liblitterer_distribution_standalone.dylib",
                        "LITTER_MULTIPLIER": "5",
                        "LITTER_OCCUPANCY": "1",
                        **os.environ,
                    },
                )
                m = re.search(r"Done. Time elapsed: (\d+) ms.", stdout)
                assert m
                times_ms_6.append(int(m.group(1)))
            
            f.write(f"{s}\t{sum(times_ms_2) / N}\t{sum(times_ms_3) / N}\t{sum(times_ms_4) / N}\t{sum(times_ms_5) / N}\t{sum(times_ms_6) / N}\n")
            print(f"{s}\t{sum(times_ms_2) / N}\t{sum(times_ms_3) / N}\t{sum(times_ms_4) / N}\t{sum(times_ms_5) / N}\t{sum(times_ms_6) / N}\n")

    shutil.rmtree(build_directory)


if __name__ == "__main__":
    main()
