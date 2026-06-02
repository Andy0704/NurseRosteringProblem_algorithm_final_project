#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#include <nlohmann/json.hpp>
#include "heuristic.h"

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: nrp_heuristic <path/to/problem_exchange.json>\n";
        return EXIT_FAILURE;
    }

    const std::string filepath(argv[1]);

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
        std::ofstream fout(filepath);
        if (!fout.is_open()) {
            std::cerr << "Error: cannot write result to: " << filepath << "\n";
            return EXIT_FAILURE;
        }
        fout << result.dump(2) << "\n";
    }

    std::cerr << "[nrp_heuristic] Result written to: " << filepath << "\n";
    return EXIT_SUCCESS;
}
