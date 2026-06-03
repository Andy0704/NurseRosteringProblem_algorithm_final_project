#pragma once
#include <nlohmann/json.hpp>

nlohmann::json runHeuristic(const nlohmann::json& data);
nlohmann::json runEvalOnly(const nlohmann::json& data);
