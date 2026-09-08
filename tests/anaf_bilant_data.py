# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Real ANAF /bilant payloads captured from the live web service.

Keyed by ``(cui, year)`` so they can be injected straight into the
``anaf_bilant_data`` context key that ``anaf.bilant.client.fetch`` honours.
An empty dict is what ANAF really returns for an unknown fiscal code or for a
year whose balance sheet is not filed yet - it answers HTTP 200, not an error.
"""

ANAF_BILANT_DATA = {
    ("14399840", 2025): {
        "an": 2025,
        "cui": 14399840,
        "deni": "DANTE INTERNATIONALSA",
        "caen": 4754,
        "den_caen": "Comerţ cu amănuntul al articolelor şi aparatelor electrocasnice",
        "i": [
            {
                "indicator": "I5",
                "val_indicator": 344191865,
                "val_den_indicator": "Casa şi conturi la bănci",
            },
            {
                "indicator": "I6",
                "val_indicator": 26590996,
                "val_den_indicator": "CHELTUIELI IN AVANS",
            },
            {
                "indicator": "I7",
                "val_indicator": 2512599434,
                "val_den_indicator": "DATORII",
            },
            {
                "indicator": "I8",
                "val_indicator": 115766286,
                "val_den_indicator": "VENITURI IN AVANS",
            },
            {
                "indicator": "I9",
                "val_indicator": 132860846,
                "val_den_indicator": "PROVIZIOANE",
            },
            {
                "indicator": "I10",
                "val_indicator": 2041323091,
                "val_den_indicator": "CAPITALURI - TOTAL, din care:",
            },
            {
                "indicator": "I11",
                "val_indicator": 1566421,
                "val_den_indicator": "Capital subscris varsat",
            },
            {
                "indicator": "I12",
                "val_indicator": 0,
                "val_den_indicator": "Patrimoniul regiei ",
            },
            {
                "indicator": "I13",
                "val_indicator": 8706154345,
                "val_den_indicator": "Cifra de afaceri neta",
            },
            {
                "indicator": "I14",
                "val_indicator": 8964052330,
                "val_den_indicator": "VENITURI TOTALE",
            },
            {
                "indicator": "I15",
                "val_indicator": 9254606394,
                "val_den_indicator": "CHELTUIELI TOTALE",
            },
            {
                "indicator": "I16",
                "val_indicator": 0,
                "val_den_indicator": "Profit brut",
            },
            {
                "indicator": "I17",
                "val_indicator": 290554064,
                "val_den_indicator": "Pierdere bruta",
            },
            {
                "indicator": "I18",
                "val_indicator": 0,
                "val_den_indicator": "Profit net",
            },
            {
                "indicator": "I19",
                "val_indicator": 370680444,
                "val_den_indicator": "Pierdere neta",
            },
            {
                "indicator": "I20",
                "val_indicator": 2889,
                "val_den_indicator": "Numar mediu de salariati",
            },
            {
                "indicator": "I1",
                "val_indicator": 2725246619,
                "val_den_indicator": "ACTIVE IMOBILIZATE - TOTAL ",
            },
            {
                "indicator": "I2",
                "val_indicator": 2050712042,
                "val_den_indicator": "ACTIVE CIRCULANTE - TOTAL, din care:",
            },
            {
                "indicator": "I3",
                "val_indicator": 1172475902,
                "val_den_indicator": "Stocuri",
            },
            {
                "indicator": "I4",
                "val_indicator": 534044275,
                "val_den_indicator": "Creante",
            },
        ],
    },
    ("14056826", 2025): {
        "an": 2025,
        "cui": 14056826,
        "deni": "Societatea Nationala de Gaze Naturale ROMGAZ SA",
        "caen": 620,
        "den_caen": "Extracţia gazelor naturale",
        "i": [
            {
                "indicator": "I1",
                "val_indicator": 16572592765,
                "val_den_indicator": "ACTIVE IMOBILIZATE - TOTAL ",
            },
            {
                "indicator": "I2",
                "val_indicator": 7944067439,
                "val_den_indicator": "ACTIVE CIRCULANTE - TOTAL, din care:",
            },
            {
                "indicator": "I3",
                "val_indicator": 429253391,
                "val_den_indicator": "Stocuri",
            },
            {
                "indicator": "I4",
                "val_indicator": 1451668850,
                "val_den_indicator": "Creante",
            },
            {
                "indicator": "I5",
                "val_indicator": 2024968841,
                "val_den_indicator": "Casa şi conturi la bănci",
            },
            {
                "indicator": "I6",
                "val_indicator": 37201986,
                "val_den_indicator": "CHELTUIELI IN AVANS",
            },
            {
                "indicator": "I7",
                "val_indicator": 7074888286,
                "val_den_indicator": "DATORII ",
            },
            {
                "indicator": "I8",
                "val_indicator": 305064845,
                "val_den_indicator": "VENITURI IN AVANS",
            },
            {
                "indicator": "I9",
                "val_indicator": 687659621,
                "val_den_indicator": "PROVIZIOANE",
            },
            {
                "indicator": "I10",
                "val_indicator": 16486249438,
                "val_den_indicator": "CAPITALURI - TOTAL, din care:",
            },
            {
                "indicator": "I11",
                "val_indicator": 3854224000,
                "val_den_indicator": "Capital subscris varsat",
            },
            {
                "indicator": "I12",
                "val_indicator": 0,
                "val_den_indicator": "Patrimoniul regiei",
            },
            {
                "indicator": "I13",
                "val_indicator": 7579634046,
                "val_den_indicator": "Cifra de afaceri neta",
            },
            {
                "indicator": "I14",
                "val_indicator": 8356154699,
                "val_den_indicator": "VENITURI TOTALE",
            },
            {
                "indicator": "I15",
                "val_indicator": 4754457701,
                "val_den_indicator": "CHELTUIELI TOTALE",
            },
            {
                "indicator": "I16",
                "val_indicator": 3601696998,
                "val_den_indicator": "Profit brut",
            },
            {
                "indicator": "I17",
                "val_indicator": 0,
                "val_den_indicator": "Pierdere bruta",
            },
            {
                "indicator": "I18",
                "val_indicator": 3138315979,
                "val_den_indicator": "Profit net",
            },
            {
                "indicator": "I19",
                "val_indicator": 0,
                "val_den_indicator": "Pierdere bruta",
            },
            {
                "indicator": "I20",
                "val_indicator": 5227,
                "val_den_indicator": "Numar mediu de salariati",
            },
        ],
    },
    ("1973096", 2025): {
        "an": 2025,
        "cui": 1973096,
        "deni": "SC ANTIBIOTICE SA",
        "caen": 2110,
        "den_caen": "Fabricarea produselor farmaceutice de bază",
        "i": [
            {
                "indicator": "I1",
                "val_indicator": 886869364,
                "val_den_indicator": "ACTIVE IMOBILIZATE - TOTAL ",
            },
            {
                "indicator": "I2",
                "val_indicator": 501705491,
                "val_den_indicator": "ACTIVE CIRCULANTE - TOTAL, din care:",
            },
            {
                "indicator": "I3",
                "val_indicator": 183971846,
                "val_den_indicator": "Stocuri",
            },
            {
                "indicator": "I4",
                "val_indicator": 307789299,
                "val_den_indicator": "Creante",
            },
            {
                "indicator": "I5",
                "val_indicator": 9944346,
                "val_den_indicator": "Casa şi conturi la bănci",
            },
            {
                "indicator": "I6",
                "val_indicator": 3984188,
                "val_den_indicator": "CHELTUIELI IN AVANS",
            },
            {
                "indicator": "I7",
                "val_indicator": 440958431,
                "val_den_indicator": "DATORII ",
            },
            {
                "indicator": "I8",
                "val_indicator": 10524966,
                "val_den_indicator": "VENITURI IN AVANS",
            },
            {
                "indicator": "I9",
                "val_indicator": 9001934,
                "val_den_indicator": "PROVIZIOANE",
            },
            {
                "indicator": "I10",
                "val_indicator": 932073712,
                "val_den_indicator": "CAPITALURI - TOTAL, din care:",
            },
            {
                "indicator": "I11",
                "val_indicator": 67133804,
                "val_den_indicator": "Capital subscris varsat",
            },
            {
                "indicator": "I12",
                "val_indicator": 0,
                "val_den_indicator": "Patrimoniul regiei",
            },
            {
                "indicator": "I13",
                "val_indicator": 645275929,
                "val_den_indicator": "Cifra de afaceri neta",
            },
            {
                "indicator": "I14",
                "val_indicator": 685826946,
                "val_den_indicator": "VENITURI TOTALE",
            },
            {
                "indicator": "I15",
                "val_indicator": 625680382,
                "val_den_indicator": "CHELTUIELI TOTALE",
            },
            {
                "indicator": "I16",
                "val_indicator": 60146564,
                "val_den_indicator": "Profit brut",
            },
            {
                "indicator": "I17",
                "val_indicator": 0,
                "val_den_indicator": "Pierdere bruta",
            },
            {
                "indicator": "I18",
                "val_indicator": 51769472,
                "val_den_indicator": "Profit net",
            },
            {
                "indicator": "I19",
                "val_indicator": 0,
                "val_den_indicator": "Pierdere bruta",
            },
            {
                "indicator": "I20",
                "val_indicator": 1370,
                "val_den_indicator": "Numar mediu de salariati",
            },
        ],
    },
    ("14399840", 2026): {
    },
    ("13548146", 2025): {
    },
    ("13548146", 2024): {
    },
}
