#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#include <nlohmann/json.hpp>
#include "heuristic.h"

int main(int argc, char* argv[]) {
    if (argc < 2 || argc > 3) {
        std::cerr << "Usage: nrp_heuristic <input.json> [output.json]\n";
        return EXIT_FAILURE;
    }

    const std::string filepath(argv[1]);
    const std::string outpath(argc == 3 ? argv[2] : argv[1]);

    nlohmann::json data;
    {
        std::ifstream fin(filepath);
        if (!fin.is_open()) {
            std::cerr << "Error: cannot open file: " << filepath << "\n";
            return EXIT_FAILURE;
        }
        try {
            fin >> data;
        } catch (const nlohmann::json::parse_error& exc) {
            std::cerr << "Error: JSON parse error in " << filepath
                      << ": " << exc.what() << "\n";
            return EXIT_FAILURE;
        }
    }

    for (const auto& key : {"metadata", "current_schedule", "nurse_info"}) {
        if (!data.contains(key)) {
            std::cerr << "Error: problem_exchange.json missing required key: " << key << "\n";
            return EXIT_FAILURE;
        }
    }

    nlohmann::json result;
    try {
        result = runHeuristic(data);
    } catch (const std::exception& exc) {
        std::cerr << "Error: runHeuristic failed: " << exc.what() << "\n";
        return EXIT_FAILURE;
    }

    {
        std::ofstream fout(outpath);
        if (!fout.is_open()) {
            std::cerr << "Error: cannot write result to: " << outpath << "\n";
            return EXIT_FAILURE;
        }
        fout << result.dump(2) << "\n";
    }

    std::cerr << "[nrp_heuristic] Result written to: " << outpath << "\n";
    return EXIT_SUCCESS;
}
