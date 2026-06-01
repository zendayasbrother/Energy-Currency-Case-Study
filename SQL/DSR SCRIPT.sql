CREATE SCHEMA IF NOT EXISTS "Trade Intelligence";

-- 1. Chinese Macroeconomic Indicators
CREATE TABLE "Trade Intelligence".chinese_macros (
    period INT PRIMARY KEY,
    chn_lpr NUMERIC(5, 2) NOT NULL,
    chn_rrr NUMERIC(5, 2) NOT NULL,
    chn_fai_yoy NUMERIC(5, 2),
    chn_fx_reserves NUMERIC(5, 2)
);

-- 2. West African Economic Data (Linked to Macros)
CREATE TABLE "Trade Intelligence".econs_wa (
    period INT REFERENCES "Trade Intelligence".chinese_macros(period),
    country_code VARCHAR(3) NOT NULL,
    exports_to_chn NUMERIC(10, 3),
    eds_total NUMERIC(10, 2),
    eds_var NUMERIC(10, 6),
    PRIMARY KEY (period, country_code)
);

-- 3. Data Insertion
INSERT INTO "Trade Intelligence".chinese_macros (period, chn_lpr, chn_rrr, chn_fai_yoy, chn_fx_reserves) VALUES 
(2014, 5.60, 4.3, 15.7, 3.81), (2015, 4.35, 2.7, 10.0, 3.33),
(2016, 4.30, 2.4, 8.1, 3.01), (2017, 4.30, 2.6, 7.2, 3.14),
(2018, 4.31, 2.7, 5.9, 3.07), (2019, 4.15, 2.5, 5.4, 3.11),
(2020, 3.85, 2.3, 2.9, 3.22), (2021, 3.80, 2.3, 4.9, 3.25),
(2022, 3.65, 2.2, 5.1, 3.13), (2023, 3.45, 2.0, 3.0, 3.23),
(2024, 3.35, 1.9, 2.8, 3.30);

INSERT INTO "Trade Intelligence".econs_wa (period, country_code, exports_to_chn, eds_total, eds_var) VALUES 
(2014, 'GHA', 0.83, 28.52, 0.92884), (2015, 'GHA', 1.11, 31.31, 1.065832),
(2016, 'GHA', 0.942, 38.46, 1.010881), (2017, 'GHA', 2.38, 33.76, 0.854578),
(2018, 'GHA', 2.03, 35.1, 0.745978), (2019, 'GHA', 2.81, 32.69, 0.853135),
(2020, 'GHA', 1.78, 40.3, 0.733945), (2021, 'GHA', 1.39, 46.58, 0.674300412),
(2022, 'GHA', 2.2, 43.61, 0.6572938808), (2023, 'GHA', 1.38, 41.7, 0.63653774),
(2024, 'GHA', 2.0, 35.41, 0.6448534743),
(2014, 'NGA', 1.67, 46.67, 0.0), (2015, 'NGA', 0.795, 45.02, 0.0),
(2016, 'NGA', 0.471, 43.74, 0.0), (2017, 'NGA', 0.721, 65.14, 0.0),
(2018, 'NGA', 1.04, 69.44, 0.0), (2019, 'NGA', 1.67, 81.34, 0.0),
(2020, 'NGA', 1.77, 87.59, 0.0), (2021, 'NGA', 1.85, 96.25, 0.0),
(2022, 'NGA', 0.834, 103.06, 0.0), (2023, 'NGA', 1.61, 102.47, 0.0),
(2024, 'NGA', 2.03, 108.76, 0.2547372411); 

SELECT * FROM "Trade Intelligence".vw_trade_data;