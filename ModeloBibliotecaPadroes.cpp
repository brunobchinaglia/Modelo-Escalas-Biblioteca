// complete versão com restrições pedidas
#include <bits/stdc++.h>
#include <gurobi_c++.h>
#include <cmath>
#include <algorithm>
#include <locale>

using namespace std;

const int DAYS = 6; // seg, ter, qua, qui, sex, sab
const vector<string> DAY_NAMES = {"seg","ter","qua","qui","sex","sab", "dom"};
const vector<string> MONTH_NAMES = {
    "", "JANEIRO","FEVEREIRO","MARÇO","ABRIL","MAIO","JUNHO",
    "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"
};

// ======================================================
// DATA STRUCTS
// ======================================================
struct Employee {
    string name;
    char group;               // 'A' = Mon-Tue, 'B' = Wed-Thu, 'J' = Juliana (Saturdays only)
    bool worksFriday;         // false = never Friday (not used everywhere but kept)
};

struct DayInfo {
    int day, month, year;
    int weekday;              // 0=Mon ... 6=Sun
    bool holiday;
    int weekIndex;
};

struct Preference {
    vector<int> friday;
    vector<int> saturday;
};

// Função para remover acentos e normalizar a string
std::string normalize(const std::string& input) {
    std::string output;
    std::locale loc("pt_BR.utf8");
    for (char c : input) {
        if (std::isalpha(c, loc)) {
            output += std::tolower(c, loc);
        }
    }
    cout << "Normalized '" << input << "' to '" << output << "'\n"; // Debugging output
    return output;
}

// ======================================================
// PATTERN GENERATION
// ======================================================
vector<bitset<DAYS>> generatePatterns(const vector<int>& baseGroup) {
    vector<bitset<DAYS>> patterns;

    int n = baseGroup.size();
    cout << "Generating patterns for base group of size " << n << "\n";
    for (int mask = 0; mask < (1 << n); ++mask) {
        bitset<DAYS> base;
        for (int i = 0; i < n; ++i)
            if (mask & (1 << i))
                base.set(baseGroup[i]);
                cout << "Generated base pattern: " << base << "\n";

        int weekdayCount = base.count();

        patterns.push_back(base);

        if (weekdayCount + 1 <= 2) {
            auto fri = base;
            fri.set(4); // sexta-feira
            if (!(base.test(0) && base.test(1))) { // Não permite seg-ter e sexta
                patterns.push_back(fri);
            }
        }

        if (weekdayCount + 1 <= 3) {
            auto sat = base;
            sat.set(5); // sábado
            patterns.push_back(sat); // Permite seg-ter e sábado
        }
    }
    return patterns;
}

// ======================================================
// CSV UTILS
// ======================================================
vector<string> split(const string& s, char sep=',') {
    vector<string> out;
    string cur;
    for (char c : s) {
        if (c == sep) {
            out.push_back(cur);
            cur.clear();
        } else {
            cur.push_back(c);
        }
    }
    out.push_back(cur);

    return out;
}

// trim helper
static inline string trim_all(const string &s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

// ======================================================
// MAIN
// ======================================================
int main() {
    try {
        // ==================================================
        // READ RestricoesSemestre.csv
        // ==================================================
        ifstream rfile("RestricoesSemestre.csv");
        if (!rfile) {
            cerr << "Error opening RestricoesSemestre.csv\n";
            return 1;
        }

        vector<Employee> employees;

        // Helper: parse list of names
        auto parseNames = [&](const string& s, char g) {
            stringstream ss(s);
            string name;
            while (getline(ss, name, ',')) {
                employees.push_back({trim_all(name), g, false});
            }
        };

        string line, key, names;

        // ---------- Line Mon/Tue ----------
        if (!getline(rfile, line)) {
            cerr << "Error reading Mon/Tue line\n";
            return 1;
        }
        {
            stringstream ss(line);
            getline(ss, key, ',');    // Mon/Tue
            getline(ss, names);       // "Gislene, Irene, Ana"
            names.erase(remove(names.begin(), names.end(), '"'), names.end());
            parseNames(names, 'A');
        }

        // ---------- Line Wed/Thu ----------
        if (!getline(rfile, line)) {
            cerr << "Error reading Wed/Thu line\n";
            return 1;
        }
        {
            stringstream ss(line);
            getline(ss, key, ',');    // Wed/Thu
            getline(ss, names);       // "Sandra, Regina, Bia"
            names.erase(remove(names.begin(), names.end(), '"'), names.end());
            parseNames(names, 'B');
        }

        // debug
        cout << "\nEmployees loaded (from Restrictions):\n";
        for (auto& e : employees) {
            cout << "[" << e.name << "] group=" << e.group << "\n";
        }

        // ---------- read year / dates / holidays (rest of file) ----------
        if (!getline(rfile, line)) {
            cerr << "Error reading year line\n";
            return 1;
        }
        auto y = split(line);
        string ys = trim_all(y.back());
        int year = stoi(ys);

        // skip lines until finding "first day," in the format your file has - we already know the layout of your file
        // assume the fixed format as you sent before
        getline(rfile, line); // "first day,"
        getline(rfile, line); // "day,month"
        getline(rfile, line); // "4,8"
        auto s1 = split(line);
        int sd = stoi(trim_all(s1[0]));
        int sm = stoi(trim_all(s1[1]));

        getline(rfile, line); // "last day,"
        getline(rfile, line); // "day,month"
        getline(rfile, line); // "14,12"
        auto s2 = split(line);
        int ed = stoi(trim_all(s2[0]));
        int em = stoi(trim_all(s2[1]));

        set<pair<int,int>> holidays;
        while (getline(rfile, line)) {
            auto p = split(line);
            if (p.size() < 2) continue;
            string a = trim_all(p[0]);
            string b = trim_all(p[1]);
            if (a.empty() || b.empty()) continue;
            if (!isdigit(a[0]) || !isdigit(b[0])) continue;
            holidays.insert({stoi(a), stoi(b)});
        }

        // ==================================================
        // CALENDAR
        // ==================================================
        vector<DayInfo> calendar;
        tm t = {};
        t.tm_mday = sd;
        t.tm_mon = sm-1;
        t.tm_year = year-1900;
        mktime(&t);

        int weekIndex = 0;
        while (true) {
            int wd = (t.tm_wday + 6) % 7;
            bool isHoliday = holidays.count({t.tm_mday, t.tm_mon+1});
            calendar.push_back({t.tm_mday, t.tm_mon+1, year, wd, isHoliday, weekIndex});
            if (wd == 6) weekIndex++;
            if (t.tm_mday == ed && t.tm_mon+1 == em) break;
            t.tm_mday++;
            mktime(&t);
        }
        int W = weekIndex+1;

        // ==================================================
        // READ RespostasEscala.csv
        // ==================================================
        ifstream pfile("RespostasEscala.csv");
        if (!pfile) {
            cerr << "Error opening RespostasEscala.csv\n";
            return 1;
        }

        getline(pfile, line);
        auto header = split(line);

        map<string, Preference> prefs;
        set<string> processedColumns; // Track processed columns to avoid duplication
        while (getline(pfile, line)) {
            auto v = split(line);

            string name = trim_all(v[2]);
            cout << "Processing preferences for: " << name << "\n"; // Debugging output

            Preference pr;
            for (int i = 3; i < (int)v.size(); ++i) {
                string colName = header[i];
                transform(colName.begin(), colName.end(), colName.begin(), ::tolower); // Normalize to lowercase

                string s = normalize(v[i]); // Normaliza a string, removendo acentos e espaços
                int val;
                if (s.empty()) val = 4;
                else if (s == "gostaria") val = 3;
                else if (s == "indiferente") val = 2;
                else if (s == "nogostaria" || s == "nao gostaria" || s == "não gostaria") val = 1;
                else val = 0;

                if (colName.find("sexta") != string::npos) {
                    pr.friday.push_back(val);
                    cout << "Processed preference for " << name << " in column " << colName << " with value " << val << "\n";
                } else if (colName.find("sábado") != string::npos || colName.find("sabado") != string::npos || colName.find("sábados") != string::npos || colName.find("sabados") != string::npos || colName.find("sabados") != string::npos) {
                    pr.saturday.push_back(val);
                    cout << "Processed preference for " << name << " in column " << colName << " with value " << val << "\n";
                } else {
                    cout << "Unrecognized column: " << colName << "\n"; // Debugging output
                }
            }

            // Ensure preferences are stored even if no valid columns were found
            if (pr.friday.empty() && pr.saturday.empty()) {
                cout << "No valid preferences found for: " << name << "\n";
            }

            prefs[name] = pr;
        }

        // If Juliana exists in prefs but wasn't in Restricoes, add Juliana as special
        bool hasJul = false;
        for (auto &e: employees) if (e.name == "Juliana") hasJul = true;
        if (!hasJul && prefs.count("Juliana")) {
            employees.push_back({"Juliana", 'J', false});
            cout << "Adicionando Juliana como funcionária (sábados only)\n";
        }
        for (auto& e : employees) cout << "[" << e.name << "] grupo="<< e.group << "\n";

        // update N
        int N = employees.size();

        // ==================================================
        // PATTERNS
        // ==================================================
        auto patsA = generatePatterns({0,1});
        auto patsB = generatePatterns({2,3});
        for (int i=0; i<(int)patsA.size(); ++i) cout << "Generated " << patsA[i] << " patterns for group A\n";
        for (int i=0; i<(int)patsB.size(); ++i) cout << "Generated " << patsB[i] << " patterns for group B\n";
        // patterns for Juliana: only none or saturday
        vector<bitset<DAYS>> patsJ;
        {
            bitset<DAYS> none;
            none.reset();
            bitset<DAYS> sat;
            sat.reset();
            sat.set(5);
            patsJ.push_back(none);
            patsJ.push_back(sat);
            cout << "Generated " << none << " and " << sat << " patterns for Juliana\n";
        }

        // ==================================================
        // PRECOMPUTE day_exists / holiday / month for (w,d)
        // ==================================================
        vector<vector<bool>> day_exists(W, vector<bool>(DAYS,false));
        vector<vector<bool>> day_holiday(W, vector<bool>(DAYS,false));
        vector<vector<int>> day_month(W, vector<int>(DAYS,-1));
        for (auto &di : calendar) {
            if (di.weekIndex >=0 && di.weekIndex < W && di.weekday >=0 && di.weekday < DAYS) {
                day_exists[di.weekIndex][di.weekday] = true;
                day_holiday[di.weekIndex][di.weekday] = di.holiday;
                day_month[di.weekIndex][di.weekday] = di.month;
            }
        }

        // collect months present and mapping month->friday weeks/sat weeks
        set<int> months_set;
        for (auto &di : calendar) months_set.insert(di.month);
        vector<int> months(months_set.begin(), months_set.end());

        map<int, vector<int>> fridays_in_month; // month -> list of weeks w where friday exists
        map<int, vector<int>> saturdays_in_month;
        vector<int> all_friday_weeks;
        vector<int> all_saturday_weeks;

        // ==================================================
        // Build fridays_in_month, saturdays_in_month and all_*_weeks
        // (ONLY non-holiday days are counted)
        // ==================================================
        for (int w = 0; w < W; ++w) {
            // FRIDAYS: only if day exists AND is NOT holiday
            if (day_exists[w][4] && !day_holiday[w][4]) {
                int m = day_month[w][4];
                fridays_in_month[m].push_back(w);
                all_friday_weeks.push_back(w);
            }
            // SATURDAYS: only if day exists AND is NOT holiday
            if (day_exists[w][5] && !day_holiday[w][5]) {
                int m = day_month[w][5];
                saturdays_in_month[m].push_back(w);
                all_saturday_weeks.push_back(w);
            }
        }

        // sort to guarantee chronological order (important for sliding windows)
        sort(all_friday_weeks.begin(), all_friday_weeks.end());
        sort(all_saturday_weeks.begin(), all_saturday_weeks.end());
        for (auto &p : fridays_in_month) sort(p.second.begin(), p.second.end());
        for (auto &p : saturdays_in_month) sort(p.second.begin(), p.second.end());

        // define STI / SAU groups for Saturdays (as you requested)
        // STI: Juliana, Bia, Sandra, Gislene
        // SAU: Ana, Irene, Regina
        auto isSTI = [&](const string &name) {
            string n = name;
            // normalize simple
            if (n=="Juliana" || n=="Bia" || n=="Sandra" || n=="Gislene") return true;
            return false;
        };
        auto isSAU = [&](const string &name) {
            string n = name;
            if (n=="Ana" || n=="Irene" || n=="Regina") return true;
            return false;
        };

        // find number of A and B employees (fixed schedules)
        int countA = 0, countB = 0;
        for (auto &e: employees) {
            if (e.group == 'A') countA++;
            else if (e.group == 'B') countB++;
        }

        // compute eligible saturday counts per group (STI excluding Bia if rule says Bia never works saturday)
        vector<int> eligibleSTI_indices;
        vector<int> eligibleSAU_indices;
        int idxBia = -1;
        for (int i=0;i<N;i++) {
            if (employees[i].name == "Bia") idxBia = i;
            if (isSTI(employees[i].name)) {
                if (employees[i].name == "Bia") {
                    // Bia never works Saturdays (explicit)
                    continue;
                }
                eligibleSTI_indices.push_back(i);
            } else if (isSAU(employees[i].name)) {
                eligibleSAU_indices.push_back(i);
            }
        }
        cout << "Eligible STI for Saturdays (excluding Bia): ";
        for (int i : eligibleSTI_indices) cout << employees[i].name << " ";
        cout << "\n";
        int countSTI_eligible = (int)eligibleSTI_indices.size();
        int countSAU_eligible = (int)eligibleSAU_indices.size();

        cout << "\nTotal employees: " << N << " (A=" << countA << ", B=" << countB << ")\n";

        // ==================================================
        // MODEL
        // ==================================================
        GRBEnv env;
        GRBModel model(env);
        double MSb_sti, MSb_sau, MSx;

        map<tuple<int,int,int>, GRBVar> x; // x[i,j,w]

        for (int i=0;i<N;i++) {
            const auto& pats = (employees[i].group=='A') ? patsA : (employees[i].group=='B') ? patsB : patsJ;
            for (int j=0;j<(int)pats.size();j++) {
                for (int w=0; w<W; ++w) {
                    x[{i,j,w}] = model.addVar(0.0, 1.0, 0.0, GRB_BINARY,
                        "x_" + to_string(i) + "_" + to_string(j) + "_" + to_string(w));
                }
            }
        }

        // One pattern per employee per week
        for (int i=0;i<N;i++) {
            const auto& pats = (employees[i].group=='A') ? patsA : (employees[i].group=='B') ? patsB : patsJ;
            for (int w=0; w<W; ++w) {
                GRBLinExpr sum = 0;
                for (int j=0;j<(int)pats.size();j++) sum += x[{i,j,w}];
                model.addConstr(sum == 1, "onepat_i" + to_string(i) + "_w" + to_string(w));
            }
        }

        // ---------- Invalidate patterns that put someone on holidays ----------
        for (int w=0; w<W; ++w) {
            for (int i=0; i<N; ++i) {
                const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                for (int j=0;j<(int)pats.size(); ++j) {
                    bool forbid = false;
                    for (int d=0; d<DAYS; ++d) {
                        if (pats[j][d] && day_exists[w][d] && day_holiday[w][d]) { forbid = true; break; }
                    }
                    if (forbid) {
                        model.addConstr(x[{i,j,w}] == 0, "forbid_hol_i" + to_string(i) + "_j" + to_string(j) + "_w" + to_string(w));
                    }
                }
            }
        }

        // ---------- Bia never works Saturdays: forbid patterns with sat for Bia ----------
        if (idxBia != -1) {
            int i = idxBia;
            const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
            for (int j=0;j<(int)pats.size(); ++j) {
                if (pats[j][5]) {
                    for (int w=0; w<W; ++w) {
                        model.addConstr(x[{i,j,w}] == 0, "forbid_bia_sat_i" + to_string(i) + "_j" + to_string(j) + "_w" + to_string(w));
                    }
                }
            }
        }

        // ---------- Friday coverage: exactly 1 from group A and 1 from group B (when day exists and not holiday) ----------
        for (int w=0; w<W; ++w) {
            if (!day_exists[w][4]) continue;
            if (day_holiday[w][4]) {
                // no-one on holiday (patterns already forbidden) -> we can ensure 0
                GRBLinExpr coverAll = 0;
                for (int i=0;i<N;i++) {
                    const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                    for (int j=0;j<(int)pats.size(); ++j)
                        if (pats[j][4]) coverAll += x[{i,j,w}];
                }
                model.addConstr(coverAll == 0, "cover_friday_w" + to_string(w) + "_holiday");
            } else {
                // group A count == 1
                GRBLinExpr coverA=0;
                for (int i=0;i<N;i++) if (employees[i].group=='A') {
                    const auto& pats = patsA;
                    for (int j=0;j<(int)pats.size(); ++j)
                        if (pats[j][4]) coverA += x[{i,j,w}];
                }
                model.addConstr(coverA == 1, "friday_A_w" + to_string(w));
                // group B count == 1
                GRBLinExpr coverB=0;
                for (int i=0;i<N;i++) if (employees[i].group=='B') {
                    const auto& pats = patsB;
                    for (int j=0;j<(int)pats.size(); ++j)
                        if (pats[j][4]) coverB += x[{i,j,w}];
                }
                model.addConstr(coverB == 1, "friday_B_w" + to_string(w));
            }
        }

        // ---------- Coverage for other weekdays (seg..qui) : exactly 2 if not holiday ----------
        for (int w=0; w<W; ++w) {
            for (int d=0; d<=3; ++d) {
                if (!day_exists[w][d]) continue;
                if (day_holiday[w][d]) {
                    // no-one
                    GRBLinExpr cover=0;
                    for (int i=0;i<N;i++) {
                        const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                        for (int j=0;j<(int)pats.size(); ++j)
                            if (pats[j][d]) cover += x[{i,j,w}];
                    }
                    model.addConstr(cover == 0, "cover_w" + to_string(w) + "_d" + to_string(d) + "_holiday");
                } else {
                    GRBLinExpr cover=0;
                    for (int i=0;i<N;i++) {
                        const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                        for (int j=0;j<(int)pats.size(); ++j)
                            if (pats[j][d]) cover += x[{i,j,w}];
                    }
                    model.addConstr(cover == 2, "cover_w" + to_string(w) + "_d" + to_string(d));
                }
            }
        }

        // ---------- Saturdays: one STI and one SAU (if not holiday) ----------
        for (int w=0; w<W; ++w) {
            if (!day_exists[w][5]) continue;
            if (day_holiday[w][5]) {
                // nobody
                GRBLinExpr cover=0;
                for (int i=0;i<N;i++) {
                    const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                    for (int j=0;j<(int)pats.size(); ++j)
                        if (pats[j][5]) cover += x[{i,j,w}];
                }
                model.addConstr(cover == 0, "sat_w" + to_string(w) + "_holiday");
            } else {
                // STI count == 1 (excluding Bia by forbidding patterns earlier)
                GRBLinExpr stiCover = 0;
                for (int i=0;i<N;i++) if (isSTI(employees[i].name)) {
                    const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                    for (int j=0;j<(int)pats.size(); ++j)
                        if (pats[j][5]) stiCover += x[{i,j,w}];
                }
                model.addConstr(stiCover == 1, "sat_STI_w" + to_string(w));
                // SAU count == 1
                GRBLinExpr sauCover = 0;
                for (int i=0;i<N;i++) if (isSAU(employees[i].name)) {
                    const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                    for (int j=0;j<(int)pats.size(); ++j)
                        if (pats[j][5]) sauCover += x[{i,j,w}];
                }
                model.addConstr(sauCover == 1, "sat_SAU_w" + to_string(w));
            }
        }

        // ==================================================
        // Two consecutive Fridays/Saturdays restriction (no 3-in-a-row)
        // ==================================================
        // For fridays: sliding window over ordered all_friday_weeks
        for (int t = 1; t < (int)all_friday_weeks.size(); ++t) {
            int w1 = all_friday_weeks[t-1];
            int w2 = all_friday_weeks[t];
            for (int i=0;i<N;i++) {
                const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                GRBLinExpr works = 0;
                for (int j=0;j<(int)pats.size(); ++j) {
                    if (pats[j][4]) {
                        works += x[{i,j,w1}];
                        works += x[{i,j,w2}];
                    }
                }
                model.addConstr(works <= 2, "no3fri_i" + to_string(i) + "_w" + to_string(w2));
            }
        }
        // For saturdays: sliding window over all_saturday_weeks
        for (int t = 2; t < (int)all_saturday_weeks.size(); ++t) {
            int w0 = all_saturday_weeks[t-2];
            int w1 = all_saturday_weeks[t-1];
            int w2 = all_saturday_weeks[t];
            for (int i=0;i<N;i++) {
                const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
                GRBLinExpr works = 0;
                for (int j=0;j<(int)pats.size(); ++j) {
                    if (pats[j][5]) {
                        works += x[{i,j,w0}];
                        works += x[{i,j,w1}];
                        works += x[{i,j,w2}];
                    }
                }
                model.addConstr(works <= 2, "no3sat_i" + to_string(i) + "_w" + to_string(w2));
            }
        }

        // ==================================================
        // Balance constraints using floor/ceil:
        // - per month
        // - per consecutive 2-month windows
        // - across all fridays / all saturdays
        // For Fridays: balance among group A and among group B
        // For Saturdays: balance among eligible STI and among SAU
        // ==================================================

        // Helper: create an expression count of employee i working day d in week w
        auto work_expr = [&](int i, int w, int d) {
            GRBLinExpr expr = 0;
            const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
            for (int j=0;j<(int)pats.size(); ++j) if (pats[j][d]) expr += x[{i,j,w}];
            return expr;
        };

        // --- FRIDAYS balance ---
        // prepare mapping month -> friday weeks is fridays_in_month
        // months vector already prepared

        // per month
        for (int m : months) {
            auto &weeks = fridays_in_month[m];
            int num_fridays = (int)weeks.size();
            if (num_fridays == 0) continue;

            if (countA > 0) {
                double targetA = (double)num_fridays / (double)countA;
                int lowA = (int)floor(targetA);
                int highA = (int)ceil(targetA);
                // for each employee in A
                for (int i=0;i<N;i++) if (employees[i].group=='A') {
                    GRBLinExpr sum = 0;
                    for (int w : weeks) sum += work_expr(i,w,4);
                    model.addConstr(sum >= lowA, "A_month_low_" + to_string(i) + "_m" + to_string(m));
                    model.addConstr(sum <= highA, "A_month_high_" + to_string(i) + "_m" + to_string(m));
                }
            }
            if (countB > 0) {
                double targetB = (double)num_fridays / (double)countB;
                int lowB = (int)floor(targetB);
                int highB = (int)ceil(targetB);
                for (int i=0;i<N;i++) if (employees[i].group=='B') {
                    GRBLinExpr sum = 0;
                    for (int w : weeks) sum += work_expr(i,w,4);
                    model.addConstr(sum >= lowB, "B_month_low_" + to_string(i) + "_m" + to_string(m));
                    model.addConstr(sum <= highB, "B_month_high_" + to_string(i) + "_m" + to_string(m));
                }
            }
        }

        // per 2-month windows (consecutive)
        for (int idxMonth=0; idxMonth+1<(int)months.size(); ++idxMonth) {
            int m1 = months[idxMonth];
            int m2 = months[idxMonth+1];
            vector<int> weeks;
            weeks.insert(weeks.end(), fridays_in_month[m1].begin(), fridays_in_month[m1].end());
            weeks.insert(weeks.end(), fridays_in_month[m2].begin(), fridays_in_month[m2].end());
            int num_fridays = (int)weeks.size();
            if (num_fridays == 0) continue;
            if (countA > 0) {
                double targetA = (double)num_fridays / (double)countA;
                int lowA = (int)floor(targetA);
                int highA = (int)ceil(targetA);
                for (int i=0;i<N;i++) if (employees[i].group=='A') {
                    GRBLinExpr sum=0;
                    for (int w:weeks) sum += work_expr(i,w,4);
                    model.addConstr(sum >= lowA, "A_2m_low_i" + to_string(i) + "_m" + to_string(m1));
                    model.addConstr(sum <= highA, "A_2m_high_i" + to_string(i) + "_m" + to_string(m1));
                }
            }
            if (countB > 0) {
                double targetB = (double)num_fridays / (double)countB;
                int lowB = (int)floor(targetB);
                int highB = (int)ceil(targetB);
                for (int i=0;i<N;i++) if (employees[i].group=='B') {
                    GRBLinExpr sum=0;
                    for (int w:weeks) sum += work_expr(i,w,4);
                    model.addConstr(sum >= lowB, "B_2m_low_i" + to_string(i) + "_m" + to_string(m1));
                    model.addConstr(sum <= highB, "B_2m_high_i" + to_string(i) + "_m" + to_string(m1));
                }
            }
        }

        // across all fridays
        {
            auto &weeks = all_friday_weeks;
            int num_fridays = (int)weeks.size();
            if (num_fridays > 0) {
                if (countA > 0) {
                    double targetA = (double)num_fridays / (double)countA;
                    int lowA = (int)floor(targetA);
                    int highA = (int)ceil(targetA);
                    MSx = lowA;
                    
                    for (int i=0;i<N;i++) if (employees[i].group=='A') {
                        GRBLinExpr sum=0;
                        for (int w:weeks) sum += work_expr(i,w,4);
                        model.addConstr(sum >= lowA, "A_all_low_i" + to_string(i));
                        model.addConstr(sum <= highA, "A_all_high_i" + to_string(i));
                    }
                }
                if (countB > 0) {
                    double targetB = (double)num_fridays / (double)countB;
                    int lowB = (int)floor(targetB);
                    int highB = (int)ceil(targetB);
                    for (int i=0;i<N;i++) if (employees[i].group=='B') {
                        GRBLinExpr sum=0;
                        for (int w:weeks) sum += work_expr(i,w,4);
                        model.addConstr(sum >= lowB, "B_all_low_i" + to_string(i));
                        model.addConstr(sum <= highB, "B_all_high_i" + to_string(i));
                    }
                }
            }
        }

        // --- SATURDAYS balance (group STI vs SAU) ---
        // per month
        for (int m : months) {
            auto &weeks = saturdays_in_month[m];
            int num_sats = (int)weeks.size();
            if (num_sats == 0) continue;

            if (countSTI_eligible > 0) {
                double targetSTI = (double)num_sats / (double)countSTI_eligible;
                int low = (int)floor(targetSTI);
                int high = (int)ceil(targetSTI);
                for (int idx : eligibleSTI_indices) {
                    GRBLinExpr sum=0;
                    for (int w: weeks) sum += work_expr(idx,w,5);
                    model.addConstr(sum >= low, "STI_month_low_i" + to_string(idx) + "_m" + to_string(m));
                    model.addConstr(sum <= high, "STI_month_high_i" + to_string(idx) + "_m" + to_string(m));
                }
            }
            if (countSAU_eligible > 0) {
                double targetSAU = (double)num_sats / (double)countSAU_eligible;
                int low = (int)floor(targetSAU);
                int high = (int)ceil(targetSAU);
                for (int idx : eligibleSAU_indices) {
                    GRBLinExpr sum=0;
                    for (int w: weeks) sum += work_expr(idx,w,5);
                    model.addConstr(sum >= low, "SAU_month_low_i" + to_string(idx) + "_m" + to_string(m));
                    model.addConstr(sum <= high, "SAU_month_high_i" + to_string(idx) + "_m" + to_string(m));
                }
            }
        }

        // per 2-month windows
        for (int idxMonth=0; idxMonth+1<(int)months.size(); ++idxMonth) {
            int m1 = months[idxMonth];
            int m2 = months[idxMonth+1];
            vector<int> weeks;
            weeks.insert(weeks.end(), saturdays_in_month[m1].begin(), saturdays_in_month[m1].end());
            weeks.insert(weeks.end(), saturdays_in_month[m2].begin(), saturdays_in_month[m2].end());
            int num_sats = (int)weeks.size();

            // Debugging output
            cout << "Processing 2-month window: " << m1 << " and " << m2 << "\n";
            cout << "Number of Saturdays: " << num_sats << "\n";
            cout << "Weeks: ";
            for (int w : weeks) cout << w << " ";
            cout << "\n";

            if (num_sats == 0) continue;
            if (countSTI_eligible > 0) {
                double targetSTI = (double)num_sats / (double)countSTI_eligible;
                int low = (int)floor(targetSTI);
                int high = (int)ceil(targetSTI);
                cout << "STI Target: " << targetSTI << " Low: " << low << " High: " << high << "\n";
                for (int idx : eligibleSTI_indices) {
                    GRBLinExpr sum=0;
                    for (int w: weeks) sum += work_expr(idx,w,5);
                    model.addConstr(sum >= low, "STI_2m_low_i" + to_string(idx) + "_m" + to_string(m1));
                    model.addConstr(sum <= high, "STI_2m_high_i" + to_string(idx) + "_m" + to_string(m1));
                }
            }
            if (countSAU_eligible > 0) {
                double targetSAU = (double)num_sats / (double)countSAU_eligible;
                int low = (int)floor(targetSAU);
                int high = (int)ceil(targetSAU);
                cout << "SAU Target: " << targetSAU << " Low: " << low << " High: " << high << "\n";
                for (int idx : eligibleSAU_indices) {
                    GRBLinExpr sum=0;
                    for (int w: weeks) sum += work_expr(idx,w,5);
                    model.addConstr(sum >= low, "SAU_2m_low_i" + to_string(idx) + "_m" + to_string(m1));
                    model.addConstr(sum <= high, "SAU_2m_high_i" + to_string(idx) + "_m" + to_string(m1));
                }
            }
        }

        // across all saturdays
        {
            auto &weeks = all_saturday_weeks;
            int num_sats = (int)weeks.size();
            if (num_sats > 0) {
                if (countSTI_eligible > 0) {
                    double targetSTI = (double)num_sats / (double)countSTI_eligible;
                    int low = (int)floor(targetSTI);
                    int high = (int)ceil(targetSTI);
                    MSb_sti = low;
                    
                    for (int idx : eligibleSTI_indices) {
                        GRBLinExpr sum=0;
                        for (int w: weeks) sum += work_expr(idx,w,5);
                        model.addConstr(sum >= low, "STI_all_low_i" + to_string(idx));
                        model.addConstr(sum <= high, "STI_all_high_i" + to_string(idx));
                    }
                }
                if (countSAU_eligible > 0) {
                    double targetSAU = (double)num_sats / (double)countSAU_eligible;
                    int low = (int)floor(targetSAU);
                    int high = (int)ceil(targetSAU);
                    MSb_sau = low;
                    
                    for (int idx : eligibleSAU_indices) {
                        GRBLinExpr sum=0;
                        for (int w: weeks) sum += work_expr(idx,w,5);
                        model.addConstr(sum >= low, "SAU_all_low_i" + to_string(idx));
                        model.addConstr(sum <= high, "SAU_all_high_i" + to_string(idx));
                    }
                }
            }
        }

        // ==================================================
        // OBJETIVO — HAPPINESS
        // ==================================================

        vector<GRBVar> alegria(N);
        for (int i = 0; i < N; ++i) {
            alegria[i] = model.addVar(0.0, 1.0, 0.0, GRB_CONTINUOUS, "alegria_" + to_string(i));
        }

        for (int i = 0; i < N; ++i) {
            GRBLinExpr expressaoFelicidade = 0;
            double somaConstantesFolga = 0;

            auto it = prefs.find(employees[i].name);
            Preference emptyPr;
            Preference &pr = (it == prefs.end()) ? emptyPr : it->second;

            // --- SEXTAS ---
            if (employees[i].name != "Juliana") {
                for (int w = 0; w < (int)all_friday_weeks.size(); ++w) {
                    int weekIdx = all_friday_weeks[w];
                    if (w < (int)pr.friday.size()) {
                        GRBLinExpr X = work_expr(i, weekIdx, 4);
                        // Lógica: Se trabalha, ganha pr.friday[w]. Se folga, ganha 4.
                        // Matematicamente: 4 + (pr.friday[w] - 4) * X
                        expressaoFelicidade += (double(pr.friday[w]) - 4.0) * X;
                        somaConstantesFolga += 4.0;
                    }
                }
            }

            // --- SÁBADOS ---
            if (employees[i].name != "Bia") {
                for (int w = 0; w < (int)all_saturday_weeks.size(); ++w) {
                    int weekIdx = all_saturday_weeks[w];
                    if (w < (int)pr.saturday.size()) {
                        GRBLinExpr Y = work_expr(i, weekIdx, 5);
                        expressaoFelicidade += (double(pr.saturday[w]) - 4.0) * Y;
                        somaConstantesFolga += 4.0;
                    }
                }
            }

            // --- CÁLCULO DO DENOMINADOR (Cenário Ideal Realista) ---
            double denominador = 0.0;

            // Para Sextas: Considera que ela trabalhará exatamente MSx dias (os com melhor nota)
            if (employees[i].name != "Juliana") {
                vector<int> p_fri = pr.friday;
                sort(p_fri.begin(), p_fri.end(), greater<int>());
                
                int T_fri = (int)MSx; 
                for (int k = 0; k < (int)p_fri.size(); ++k) {
                    if (k < T_fri) denominador += p_fri[k]; // Dias de trabalho (melhores notas)
                    else denominador += 4.0;               // Dias de folga (nota máxima 4)
                }
            }

            // Para Sábados: Considera a carga horária do grupo STI ou SAU
            if (employees[i].name != "Bia") {
                vector<int> p_sat = pr.saturday;
                sort(p_sat.begin(), p_sat.end(), greater<int>());
                
                int T_sat = isSTI(employees[i].name) ? (int)MSb_sti : (int)MSb_sau;
                for (int k = 0; k < (int)p_sat.size(); ++k) {
                    if (k < T_sat) denominador += p_sat[k];
                    else denominador += 4.0;
                }
            }

            // --- ADICIONAR RESTRIÇÃO AO MODELO ---
            // alegria = (expressao + soma) / denominador  =>  alegria * denominador - expressao = soma
            if (denominador > 0) {
                model.addConstr(alegria[i] * denominador == expressaoFelicidade + somaConstantesFolga, 
                                "def_alegria_i" + to_string(i));
            } else {
                model.addConstr(alegria[i] == 1.0, "def_alegria_zero_den_i" + to_string(i));
            }
        }

        // ==================================================
        // CÁLCULO DO TOTAL DE DIAS TRABALHADOS (Para balanceamento)
        // ==================================================
        
        // 1. Variáveis para armazenar o total de dias de cada funcionária
        vector<GRBVar> totalDias(N);
        for (int i = 0; i < N; ++i) {
            totalDias[i] = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, "totalDias_" + to_string(i));
            
            GRBLinExpr sumDias = 0;
            const auto& pats = (employees[i].group == 'A') ? patsA : (employees[i].group == 'B') ? patsB : patsJ;
            
            // Soma dias trabalhados usando o pats[j].count()
            for (int w = 0; w < W; ++w) {
                for (int j = 0; j < (int)pats.size(); ++j) {
                    sumDias += pats[j].count() * x[{i, j, w}];
                }
            }
            // Finge que a Bia trabalhou uma média de sábados para não ser injusto
            if (employees[i].name == "Bia")
                sumDias += MSb_sti;

            // Conecta a variável à soma calculada
            model.addConstr(totalDias[i] == sumDias, "def_totalDias_i" + to_string(i));
        }

        // 2. Variáveis para o Máximo e Mínimo globais
        GRBVar maxDias = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, "maxDias");
        GRBVar minDias = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, "minDias");

        // 3. Forçar maxDias a ser maior que todos, e minDias a ser menor que todos
        for (int i = 0; i < N; ++i) {
            // NOTA: Talvez você queira pular a Juliana (i) aqui, explicarei abaixo!
            model.addConstr(maxDias >= totalDias[i], "link_maxDias_i" + to_string(i));
            model.addConstr(minDias <= totalDias[i], "link_minDias_i" + to_string(i));
        }

        // 4. Variável W (A diferença / gap)
        GRBVar var_w = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, "w_diferenca");
        model.addConstr(var_w == maxDias - minDias, "def_w_diferenca");

        // --------------------------------
        // OBJETIVO
        // (opção recomendada: maximizar menor alegria)
        // --------------------------------

        GRBVar z = model.addVar(0.0, 1.0, 0.0, GRB_CONTINUOUS, "z");

        for (int i = 0; i < N; ++i) {
            model.addConstr(alegria[i] >= z, "min_alegria_link_i" + to_string(i));
        }

        GRBLinExpr obj = 10 * z;
        
        // Adiciona a alegria de cada funcionária à soma
        for (int i = 0; i < N; ++i) {
            obj += alegria[i];
        }

        obj -= var_w;

        model.setObjective(obj, GRB_MAXIMIZE);
        model.optimize();
        model.write("model.lp");

        cout << "Maximum minimum happiness z = " << z.get(GRB_DoubleAttr_X) << "\n";

        // --- NOVO TRECHO: Imprimir a alegria de cada funcionária ---
        cout << "\n=== Felicidade (Alegria) por Funcionária ===\n";
        for (int i = 0; i < N; ++i) {
            cout << left << setw(12) << employees[i].name 
                 << ": " << alegria[i].get(GRB_DoubleAttr_X) << "\n";
        }
        cout << "============================================\n";

        // ==================================================
        // BUILD table for printing (empty default, * for holiday/dom, fill from selected patterns)
        // ==================================================
        map<pair<int,int>, map<string,char>> table;
        for (auto &di : calendar) for (auto &e : employees) table[{di.day,di.month}][e.name] = ' ';
        for (auto &di : calendar) if (di.weekday==6 || di.holiday) for (auto &e : employees) table[{di.day,di.month}][e.name] = '*';

        for (int i=0;i<N;i++) {
            const auto& pats = (employees[i].group=='A')?patsA : (employees[i].group=='B')?patsB : patsJ;
            for (int w=0; w<W; ++w) {
                for (int j=0;j<(int)pats.size(); ++j) {
                    if (x[{i,j,w}].get(GRB_DoubleAttr_X)) {
                        for (auto &di : calendar) {
                            if (di.weekIndex == w && di.weekday < DAYS && !di.holiday) {
                                if (pats[j][di.weekday]) {
                                    table[{di.day,di.month}][employees[i].name] = (di.weekday == 5 ? 'D' : 'N');
                                } else if (di.weekday == 5) {
                                    table[{di.day,di.month}][employees[i].name] = '*';
                                } else {
                                    table[{di.day,di.month}][employees[i].name] = 'D';
                                }
                            }
                        }
                    }
                }
            }
        }

        // ==================================================
        // PRINT (FORMATADO, COM DIA DA SEMANA)
        // ==================================================
        int idxCal = 0;
        while (idxCal < (int)calendar.size()) {
            int curM = calendar[idxCal].month;
            cout << "\n\n" << MONTH_NAMES[curM] << "\n";
            cout << string(12 + 4 * 31, '-') << "\n";

            cout << left << setw(12) << "dia";
            int j = idxCal;
            while (j < (int)calendar.size() && calendar[j].month == curM) {
                cout << setw(4) << calendar[j].day;
                j++;
            }
            cout << "\n";

            cout << left << setw(12) << "dia_semana";
            j = idxCal;
            while (j < (int)calendar.size() && calendar[j].month == curM) {
                cout << setw(4) << (calendar[j].weekday < 6 ? DAY_NAMES[calendar[j].weekday] : "dom");
                j++;
            }
            cout << "\n\n";

            for (auto &e : employees) {
                cout << left << setw(12) << e.name;
                j = idxCal;
                while (j < (int)calendar.size() && calendar[j].month == curM) {
                    cout << setw(4) << table[{calendar[j].day, calendar[j].month}][e.name];
                    j++;
                }
                cout << "\n";
            }

            idxCal = j;
        }

    } catch (GRBException &e) {
        cerr << "Gurobi exception: " << e.getMessage() << "\n";
    } catch (exception &e) {
        cerr << e.what() << "\n";
    }
    return 0;
}
