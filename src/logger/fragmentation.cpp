#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <fstream>
#include <ios>
#include <iostream>
#include <unordered_map>
#include <unordered_set>

#include <argparse/argparse.hpp>

#include "shared.hpp"

namespace {
double occupation(
    const std::unordered_map<std::uint64_t, std::uint64_t>& sizeByPointer,
    std::uint8_t ignored_bits) {
    const auto ignored_size = std::uint64_t(1) << ignored_bits;
    std::uint64_t total = 0;
    std::unordered_set<std::uint64_t> occupied;

    for (const auto& entry : sizeByPointer) {
        std::uint64_t pointer = entry.first;
        std::uint64_t size = entry.second;
        total += size;
        while (size > ignored_size) {
            occupied.insert(pointer >> ignored_bits);
            pointer += ignored_size;
            size -= ignored_size;
        }
        if (size > 0) {
            occupied.insert(pointer >> ignored_bits);
        }
    }

    return static_cast<double>(total)
           / static_cast<double>(ignored_size * occupied.size());
}
} // namespace

int main(int argc, char** argv) {
    auto program = argparse::ArgumentParser("benchmark_iterator", "",
                                            argparse::default_arguments::help);
    program.add_argument("-i", "--input")
        .help("input file, generated by the logger tool")
        .default_value("events.bin")
        .metavar("FILE");
    program.add_argument("--ignored-bits")
        .help("granularity at which to measure fragmentation (6: cache line, "
              "12: page)")
        .default_value(12)
        .metavar("N")
        .scan<'u', std::uint8_t>();

    try {
        program.parse_args(argc, argv);
    } catch (const std::exception& err) {
        std::cerr << err.what() << std::endl;
        std::cerr << program;
        std::exit(EXIT_FAILURE);
    }

    const auto input = program.get<std::string>("--input");
    const auto ignoredBits = program.get<std::uint8_t>("--ignored-bits");

    std::ifstream input_file(input, std::ios::binary);
    if (!input_file) {
        std::cerr << "Failed to open " << input << std::endl;
        std::exit(EXIT_FAILURE);
    }

    std::uint64_t count = 0;
    Event event;
    std::unordered_map<std::uint64_t, std::uint64_t> sizeByPointer;
    while (input_file.read(reinterpret_cast<char*>(&event), sizeof(event))) {
        ++count;
        switch (event.type) {
            case EventType::Reallocation:
                assert(sizeByPointer.contains(event.pointer));
                sizeByPointer.erase(event.pointer);
                [[fallthrough]];
            case EventType::Allocation:
                assert(!sizeByPointer.contains(event.result));
                sizeByPointer.emplace(event.result, event.size);
                break;
            case EventType::Free:
                assert(sizeByPointer.contains(event.pointer));
                sizeByPointer.erase(event.pointer);
                break;
            default:
                std::abort();
        }

        if (count % 1000000 == 0) {
            std::cout << "Processed " << count << " events, fragmentation = "
                      << occupation(sizeByPointer, ignoredBits) << std::endl;
        }
    }
    std::cout << "Processed " << count << " events" << std::endl;
}
