/**
 * Airports Database - Major International Airports
 * Source: OpenFlights (domaine public)
 *
 * Format: { iata, icao, name, city, country, lat, lng }
 */

window.AIRPORTS_DATABASE = [
    // ============================================
    // FRANCE
    // ============================================
    { iata: "CDG", icao: "LFPG", name: "Charles de Gaulle", city: "Paris", country: "France", lat: 49.0097, lng: 2.5479 },
    { iata: "ORY", icao: "LFPO", name: "Orly", city: "Paris", country: "France", lat: 48.7233, lng: 2.3794 },
    { iata: "NCE", icao: "LFMN", name: "Nice Cote d'Azur", city: "Nice", country: "France", lat: 43.6584, lng: 7.2159 },
    { iata: "LYS", icao: "LFLL", name: "Saint-Exupery", city: "Lyon", country: "France", lat: 45.7256, lng: 5.0811 },
    { iata: "MRS", icao: "LFML", name: "Marseille Provence", city: "Marseille", country: "France", lat: 43.4393, lng: 5.2214 },
    { iata: "TLS", icao: "LFBO", name: "Blagnac", city: "Toulouse", country: "France", lat: 43.6291, lng: 1.3638 },
    { iata: "BOD", icao: "LFBD", name: "Merignac", city: "Bordeaux", country: "France", lat: 44.8283, lng: -0.7156 },
    { iata: "NTE", icao: "LFRS", name: "Nantes Atlantique", city: "Nantes", country: "France", lat: 47.1532, lng: -1.6107 },
    { iata: "SXB", icao: "LFST", name: "Strasbourg", city: "Strasbourg", country: "France", lat: 48.5383, lng: 7.6282 },
    { iata: "MPL", icao: "LFMT", name: "Montpellier", city: "Montpellier", country: "France", lat: 43.5762, lng: 3.963 },
    { iata: "LIL", icao: "LFQQ", name: "Lesquin", city: "Lille", country: "France", lat: 50.5619, lng: 3.0894 },
    { iata: "RNS", icao: "LFRN", name: "Saint-Jacques", city: "Rennes", country: "France", lat: 48.0695, lng: -1.7348 },
    { iata: "BIQ", icao: "LFBZ", name: "Biarritz Pays Basque", city: "Biarritz", country: "France", lat: 43.4684, lng: -1.5233 },
    { iata: "BES", icao: "LFRB", name: "Guipavas", city: "Brest", country: "France", lat: 48.4479, lng: -4.4186 },
    { iata: "CFE", icao: "LFLC", name: "Auvergne", city: "Clermont-Ferrand", country: "France", lat: 45.7867, lng: 3.1693 },
    { iata: "AJA", icao: "LFKJ", name: "Campo Dell'Oro", city: "Ajaccio", country: "France", lat: 41.9236, lng: 8.8029 },
    { iata: "BIA", icao: "LFKB", name: "Poretta", city: "Bastia", country: "France", lat: 42.5527, lng: 9.4837 },

    // ============================================
    // UNITED KINGDOM
    // ============================================
    { iata: "LHR", icao: "EGLL", name: "Heathrow", city: "Londres", country: "Royaume-Uni", lat: 51.4700, lng: -0.4543 },
    { iata: "LGW", icao: "EGKK", name: "Gatwick", city: "Londres", country: "Royaume-Uni", lat: 51.1537, lng: -0.1821 },
    { iata: "STN", icao: "EGSS", name: "Stansted", city: "Londres", country: "Royaume-Uni", lat: 51.8850, lng: 0.2350 },
    { iata: "LTN", icao: "EGGW", name: "Luton", city: "Londres", country: "Royaume-Uni", lat: 51.8747, lng: -0.3683 },
    { iata: "LCY", icao: "EGLC", name: "London City", city: "Londres", country: "Royaume-Uni", lat: 51.5053, lng: 0.0553 },
    { iata: "MAN", icao: "EGCC", name: "Manchester", city: "Manchester", country: "Royaume-Uni", lat: 53.3537, lng: -2.2750 },
    { iata: "EDI", icao: "EGPH", name: "Edinburgh", city: "Edinburgh", country: "Royaume-Uni", lat: 55.9500, lng: -3.3725 },
    { iata: "BHX", icao: "EGBB", name: "Birmingham", city: "Birmingham", country: "Royaume-Uni", lat: 52.4539, lng: -1.7480 },
    { iata: "GLA", icao: "EGPF", name: "Glasgow", city: "Glasgow", country: "Royaume-Uni", lat: 55.8719, lng: -4.4331 },
    { iata: "BRS", icao: "EGGD", name: "Bristol", city: "Bristol", country: "Royaume-Uni", lat: 51.3827, lng: -2.7191 },
    { iata: "NCL", icao: "EGNT", name: "Newcastle", city: "Newcastle", country: "Royaume-Uni", lat: 55.0375, lng: -1.6917 },
    { iata: "LPL", icao: "EGGP", name: "John Lennon", city: "Liverpool", country: "Royaume-Uni", lat: 53.3336, lng: -2.8497 },
    { iata: "BFS", icao: "EGAA", name: "Belfast International", city: "Belfast", country: "Royaume-Uni", lat: 54.6575, lng: -6.2158 },
    { iata: "ABZ", icao: "EGPD", name: "Aberdeen", city: "Aberdeen", country: "Royaume-Uni", lat: 57.2019, lng: -2.1978 },

    // ============================================
    // GERMANY
    // ============================================
    { iata: "FRA", icao: "EDDF", name: "Frankfurt am Main", city: "Francfort", country: "Allemagne", lat: 50.0264, lng: 8.5431 },
    { iata: "MUC", icao: "EDDM", name: "Franz Josef Strauss", city: "Munich", country: "Allemagne", lat: 48.3538, lng: 11.7861 },
    { iata: "BER", icao: "EDDB", name: "Berlin Brandenburg", city: "Berlin", country: "Allemagne", lat: 52.3667, lng: 13.5033 },
    { iata: "DUS", icao: "EDDL", name: "Dusseldorf", city: "Dusseldorf", country: "Allemagne", lat: 51.2895, lng: 6.7668 },
    { iata: "HAM", icao: "EDDH", name: "Hamburg", city: "Hambourg", country: "Allemagne", lat: 53.6304, lng: 9.9882 },
    { iata: "CGN", icao: "EDDK", name: "Cologne Bonn", city: "Cologne", country: "Allemagne", lat: 50.8659, lng: 7.1427 },
    { iata: "STR", icao: "EDDS", name: "Stuttgart", city: "Stuttgart", country: "Allemagne", lat: 48.6899, lng: 9.2220 },
    { iata: "HAJ", icao: "EDDV", name: "Hanover", city: "Hanovre", country: "Allemagne", lat: 52.4611, lng: 9.6850 },
    { iata: "NUE", icao: "EDDN", name: "Nuremberg", city: "Nuremberg", country: "Allemagne", lat: 49.4987, lng: 11.0669 },
    { iata: "LEJ", icao: "EDDP", name: "Leipzig/Halle", city: "Leipzig", country: "Allemagne", lat: 51.4324, lng: 12.2416 },

    // ============================================
    // SPAIN
    // ============================================
    { iata: "MAD", icao: "LEMD", name: "Adolfo Suarez Madrid-Barajas", city: "Madrid", country: "Espagne", lat: 40.4719, lng: -3.5626 },
    { iata: "BCN", icao: "LEBL", name: "El Prat", city: "Barcelone", country: "Espagne", lat: 41.2971, lng: 2.0785 },
    { iata: "AGP", icao: "LEMG", name: "Malaga Costa del Sol", city: "Malaga", country: "Espagne", lat: 36.6749, lng: -4.4991 },
    { iata: "PMI", icao: "LEPA", name: "Palma de Mallorca", city: "Palma de Majorque", country: "Espagne", lat: 39.5517, lng: 2.7388 },
    { iata: "ALC", icao: "LEAL", name: "Alicante-Elche", city: "Alicante", country: "Espagne", lat: 38.2822, lng: -0.5582 },
    { iata: "VLC", icao: "LEVC", name: "Valencia", city: "Valence", country: "Espagne", lat: 39.4893, lng: -0.4816 },
    { iata: "SVQ", icao: "LEZL", name: "Sevilla", city: "Seville", country: "Espagne", lat: 37.4180, lng: -5.8931 },
    { iata: "BIO", icao: "LEBB", name: "Bilbao", city: "Bilbao", country: "Espagne", lat: 43.3011, lng: -2.9106 },
    { iata: "IBZ", icao: "LEIB", name: "Ibiza", city: "Ibiza", country: "Espagne", lat: 38.8729, lng: 1.3731 },
    { iata: "TFS", icao: "GCTS", name: "Tenerife Sur", city: "Tenerife", country: "Espagne", lat: 28.0445, lng: -16.5725 },
    { iata: "LPA", icao: "GCLP", name: "Gran Canaria", city: "Las Palmas", country: "Espagne", lat: 27.9319, lng: -15.3866 },

    // ============================================
    // ITALY
    // ============================================
    { iata: "FCO", icao: "LIRF", name: "Leonardo da Vinci-Fiumicino", city: "Rome", country: "Italie", lat: 41.8003, lng: 12.2389 },
    { iata: "MXP", icao: "LIMC", name: "Malpensa", city: "Milan", country: "Italie", lat: 45.6306, lng: 8.7281 },
    { iata: "LIN", icao: "LIML", name: "Linate", city: "Milan", country: "Italie", lat: 45.4456, lng: 9.2778 },
    { iata: "VCE", icao: "LIPZ", name: "Marco Polo", city: "Venise", country: "Italie", lat: 45.5053, lng: 12.3519 },
    { iata: "NAP", icao: "LIRN", name: "Capodichino", city: "Naples", country: "Italie", lat: 40.8860, lng: 14.2908 },
    { iata: "BGY", icao: "LIME", name: "Orio al Serio", city: "Bergame", country: "Italie", lat: 45.6739, lng: 9.7042 },
    { iata: "BLQ", icao: "LIPE", name: "Guglielmo Marconi", city: "Bologne", country: "Italie", lat: 44.5354, lng: 11.2887 },
    { iata: "FLR", icao: "LIRQ", name: "Peretola", city: "Florence", country: "Italie", lat: 43.8100, lng: 11.2051 },
    { iata: "PSA", icao: "LIRP", name: "Galileo Galilei", city: "Pise", country: "Italie", lat: 43.6839, lng: 10.3927 },
    { iata: "TRN", icao: "LIMF", name: "Caselle", city: "Turin", country: "Italie", lat: 45.2008, lng: 7.6497 },
    { iata: "CTA", icao: "LICC", name: "Fontanarossa", city: "Catane", country: "Italie", lat: 37.4668, lng: 15.0664 },
    { iata: "PMO", icao: "LICJ", name: "Falcone Borsellino", city: "Palerme", country: "Italie", lat: 38.1760, lng: 13.0910 },

    // ============================================
    // NETHERLANDS / BELGIUM / LUXEMBOURG
    // ============================================
    { iata: "AMS", icao: "EHAM", name: "Schiphol", city: "Amsterdam", country: "Pays-Bas", lat: 52.3086, lng: 4.7639 },
    { iata: "RTM", icao: "EHRD", name: "Rotterdam The Hague", city: "Rotterdam", country: "Pays-Bas", lat: 51.9569, lng: 4.4372 },
    { iata: "EIN", icao: "EHEH", name: "Eindhoven", city: "Eindhoven", country: "Pays-Bas", lat: 51.4500, lng: 5.3747 },
    { iata: "BRU", icao: "EBBR", name: "Brussels", city: "Bruxelles", country: "Belgique", lat: 50.9014, lng: 4.4844 },
    { iata: "CRL", icao: "EBCI", name: "Charleroi", city: "Charleroi", country: "Belgique", lat: 50.4592, lng: 4.4538 },
    { iata: "LGG", icao: "EBLG", name: "Liege", city: "Liege", country: "Belgique", lat: 50.6374, lng: 5.4432 },
    { iata: "LUX", icao: "ELLX", name: "Findel", city: "Luxembourg", country: "Luxembourg", lat: 49.6266, lng: 6.2115 },

    // ============================================
    // SWITZERLAND / AUSTRIA
    // ============================================
    { iata: "ZRH", icao: "LSZH", name: "Zurich", city: "Zurich", country: "Suisse", lat: 47.4647, lng: 8.5492 },
    { iata: "GVA", icao: "LSGG", name: "Geneva", city: "Geneve", country: "Suisse", lat: 46.2381, lng: 6.1089 },
    { iata: "BSL", icao: "LFSB", name: "EuroAirport Basel-Mulhouse", city: "Bale", country: "Suisse", lat: 47.5896, lng: 7.5299 },
    { iata: "VIE", icao: "LOWW", name: "Vienna", city: "Vienne", country: "Autriche", lat: 48.1103, lng: 16.5697 },
    { iata: "SZG", icao: "LOWS", name: "Salzburg", city: "Salzbourg", country: "Autriche", lat: 47.7933, lng: 13.0043 },
    { iata: "INN", icao: "LOWI", name: "Innsbruck", city: "Innsbruck", country: "Autriche", lat: 47.2602, lng: 11.3439 },

    // ============================================
    // IRELAND
    // ============================================
    { iata: "DUB", icao: "EIDW", name: "Dublin", city: "Dublin", country: "Irlande", lat: 53.4213, lng: -6.2701 },
    { iata: "SNN", icao: "EINN", name: "Shannon", city: "Shannon", country: "Irlande", lat: 52.7020, lng: -8.9248 },
    { iata: "ORK", icao: "EICK", name: "Cork", city: "Cork", country: "Irlande", lat: 51.8413, lng: -8.4911 },

    // ============================================
    // PORTUGAL
    // ============================================
    { iata: "LIS", icao: "LPPT", name: "Humberto Delgado", city: "Lisbonne", country: "Portugal", lat: 38.7813, lng: -9.1359 },
    { iata: "OPO", icao: "LPPR", name: "Francisco Sa Carneiro", city: "Porto", country: "Portugal", lat: 41.2481, lng: -8.6814 },
    { iata: "FAO", icao: "LPFR", name: "Faro", city: "Faro", country: "Portugal", lat: 37.0144, lng: -7.9659 },
    { iata: "FNC", icao: "LPMA", name: "Madeira", city: "Funchal", country: "Portugal", lat: 32.6979, lng: -16.7745 },

    // ============================================
    // SCANDINAVIA
    // ============================================
    { iata: "CPH", icao: "EKCH", name: "Copenhagen Kastrup", city: "Copenhague", country: "Danemark", lat: 55.6180, lng: 12.6508 },
    { iata: "ARN", icao: "ESSA", name: "Stockholm Arlanda", city: "Stockholm", country: "Suede", lat: 59.6519, lng: 17.9186 },
    { iata: "OSL", icao: "ENGM", name: "Gardermoen", city: "Oslo", country: "Norvege", lat: 60.1939, lng: 11.1004 },
    { iata: "HEL", icao: "EFHK", name: "Helsinki-Vantaa", city: "Helsinki", country: "Finlande", lat: 60.3172, lng: 24.9633 },
    { iata: "GOT", icao: "ESGG", name: "Landvetter", city: "Goteborg", country: "Suede", lat: 57.6628, lng: 12.2798 },
    { iata: "BGO", icao: "ENBR", name: "Bergen Flesland", city: "Bergen", country: "Norvege", lat: 60.2934, lng: 5.2181 },

    // ============================================
    // EASTERN EUROPE
    // ============================================
    { iata: "PRG", icao: "LKPR", name: "Vaclav Havel", city: "Prague", country: "Republique Tcheque", lat: 50.1008, lng: 14.2600 },
    { iata: "WAW", icao: "EPWA", name: "Chopin", city: "Varsovie", country: "Pologne", lat: 52.1657, lng: 20.9671 },
    { iata: "KRK", icao: "EPKK", name: "John Paul II", city: "Cracovie", country: "Pologne", lat: 50.0777, lng: 19.7848 },
    { iata: "BUD", icao: "LHBP", name: "Ferenc Liszt", city: "Budapest", country: "Hongrie", lat: 47.4298, lng: 19.2611 },
    { iata: "OTP", icao: "LROP", name: "Henri Coanda", city: "Bucarest", country: "Roumanie", lat: 44.5711, lng: 26.0850 },
    { iata: "SOF", icao: "LBSF", name: "Sofia", city: "Sofia", country: "Bulgarie", lat: 42.6967, lng: 23.4114 },
    { iata: "ZAG", icao: "LDZA", name: "Franjo Tudman", city: "Zagreb", country: "Croatie", lat: 45.7429, lng: 16.0688 },
    { iata: "LJU", icao: "LJLJ", name: "Joze Pucnik", city: "Ljubljana", country: "Slovenie", lat: 46.2237, lng: 14.4576 },
    { iata: "BTS", icao: "LZIB", name: "M.R. Stefanik", city: "Bratislava", country: "Slovaquie", lat: 48.1702, lng: 17.2127 },

    // ============================================
    // GREECE / TURKEY / CYPRUS
    // ============================================
    { iata: "ATH", icao: "LGAV", name: "Eleftherios Venizelos", city: "Athenes", country: "Grece", lat: 37.9364, lng: 23.9445 },
    { iata: "SKG", icao: "LGTS", name: "Thessaloniki", city: "Thessalonique", country: "Grece", lat: 40.5197, lng: 22.9709 },
    { iata: "HER", icao: "LGIR", name: "Heraklion", city: "Heraklion", country: "Grece", lat: 35.3397, lng: 25.1803 },
    { iata: "RHO", icao: "LGRP", name: "Diagoras", city: "Rhodes", country: "Grece", lat: 36.4054, lng: 28.0862 },
    { iata: "IST", icao: "LTFM", name: "Istanbul", city: "Istanbul", country: "Turquie", lat: 41.2753, lng: 28.7519 },
    { iata: "SAW", icao: "LTFJ", name: "Sabiha Gokcen", city: "Istanbul", country: "Turquie", lat: 40.8986, lng: 29.3092 },
    { iata: "AYT", icao: "LTAI", name: "Antalya", city: "Antalya", country: "Turquie", lat: 36.8987, lng: 30.8005 },
    { iata: "ADB", icao: "LTBJ", name: "Adnan Menderes", city: "Izmir", country: "Turquie", lat: 38.2924, lng: 27.1570 },
    { iata: "LCA", icao: "LCLK", name: "Larnaca", city: "Larnaca", country: "Chypre", lat: 34.8751, lng: 33.6249 },
    { iata: "PFO", icao: "LCPH", name: "Paphos", city: "Paphos", country: "Chypre", lat: 34.7180, lng: 32.4857 },

    // ============================================
    // RUSSIA
    // ============================================
    { iata: "SVO", icao: "UUEE", name: "Sheremetyevo", city: "Moscou", country: "Russie", lat: 55.9726, lng: 37.4146 },
    { iata: "DME", icao: "UUDD", name: "Domodedovo", city: "Moscou", country: "Russie", lat: 55.4088, lng: 37.9063 },
    { iata: "VKO", icao: "UUWW", name: "Vnukovo", city: "Moscou", country: "Russie", lat: 55.5915, lng: 37.2615 },
    { iata: "LED", icao: "ULLI", name: "Pulkovo", city: "Saint-Petersbourg", country: "Russie", lat: 59.8003, lng: 30.2625 },

    // ============================================
    // USA - EAST COAST
    // ============================================
    { iata: "JFK", icao: "KJFK", name: "John F. Kennedy", city: "New York", country: "Etats-Unis", lat: 40.6413, lng: -73.7781 },
    { iata: "EWR", icao: "KEWR", name: "Newark Liberty", city: "New York/Newark", country: "Etats-Unis", lat: 40.6925, lng: -74.1687 },
    { iata: "LGA", icao: "KLGA", name: "LaGuardia", city: "New York", country: "Etats-Unis", lat: 40.7769, lng: -73.8740 },
    { iata: "BOS", icao: "KBOS", name: "Logan", city: "Boston", country: "Etats-Unis", lat: 42.3656, lng: -71.0096 },
    { iata: "PHL", icao: "KPHL", name: "Philadelphia", city: "Philadelphie", country: "Etats-Unis", lat: 39.8721, lng: -75.2411 },
    { iata: "IAD", icao: "KIAD", name: "Washington Dulles", city: "Washington", country: "Etats-Unis", lat: 38.9445, lng: -77.4558 },
    { iata: "DCA", icao: "KDCA", name: "Reagan National", city: "Washington", country: "Etats-Unis", lat: 38.8521, lng: -77.0377 },
    { iata: "MIA", icao: "KMIA", name: "Miami", city: "Miami", country: "Etats-Unis", lat: 25.7959, lng: -80.2870 },
    { iata: "FLL", icao: "KFLL", name: "Fort Lauderdale", city: "Fort Lauderdale", country: "Etats-Unis", lat: 26.0726, lng: -80.1527 },
    { iata: "MCO", icao: "KMCO", name: "Orlando", city: "Orlando", country: "Etats-Unis", lat: 28.4312, lng: -81.3081 },
    { iata: "ATL", icao: "KATL", name: "Hartsfield-Jackson", city: "Atlanta", country: "Etats-Unis", lat: 33.6407, lng: -84.4277 },
    { iata: "CLT", icao: "KCLT", name: "Charlotte Douglas", city: "Charlotte", country: "Etats-Unis", lat: 35.2140, lng: -80.9431 },

    // ============================================
    // USA - MIDWEST / SOUTH
    // ============================================
    { iata: "ORD", icao: "KORD", name: "O'Hare", city: "Chicago", country: "Etats-Unis", lat: 41.9742, lng: -87.9073 },
    { iata: "MDW", icao: "KMDW", name: "Midway", city: "Chicago", country: "Etats-Unis", lat: 41.7868, lng: -87.7522 },
    { iata: "DTW", icao: "KDTW", name: "Detroit Metro", city: "Detroit", country: "Etats-Unis", lat: 42.2124, lng: -83.3534 },
    { iata: "MSP", icao: "KMSP", name: "Minneapolis-Saint Paul", city: "Minneapolis", country: "Etats-Unis", lat: 44.8848, lng: -93.2223 },
    { iata: "DFW", icao: "KDFW", name: "Dallas/Fort Worth", city: "Dallas", country: "Etats-Unis", lat: 32.8998, lng: -97.0403 },
    { iata: "IAH", icao: "KIAH", name: "George Bush", city: "Houston", country: "Etats-Unis", lat: 29.9902, lng: -95.3368 },
    { iata: "DEN", icao: "KDEN", name: "Denver", city: "Denver", country: "Etats-Unis", lat: 39.8561, lng: -104.6737 },
    { iata: "PHX", icao: "KPHX", name: "Phoenix Sky Harbor", city: "Phoenix", country: "Etats-Unis", lat: 33.4373, lng: -112.0078 },
    { iata: "MSY", icao: "KMSY", name: "Louis Armstrong", city: "Nouvelle-Orleans", country: "Etats-Unis", lat: 29.9934, lng: -90.2580 },

    // ============================================
    // USA - WEST COAST
    // ============================================
    { iata: "LAX", icao: "KLAX", name: "Los Angeles", city: "Los Angeles", country: "Etats-Unis", lat: 33.9425, lng: -118.4081 },
    { iata: "SFO", icao: "KSFO", name: "San Francisco", city: "San Francisco", country: "Etats-Unis", lat: 37.6213, lng: -122.3790 },
    { iata: "SJC", icao: "KSJC", name: "San Jose", city: "San Jose", country: "Etats-Unis", lat: 37.3626, lng: -121.9291 },
    { iata: "OAK", icao: "KOAK", name: "Oakland", city: "Oakland", country: "Etats-Unis", lat: 37.7213, lng: -122.2208 },
    { iata: "SAN", icao: "KSAN", name: "San Diego", city: "San Diego", country: "Etats-Unis", lat: 32.7336, lng: -117.1897 },
    { iata: "SEA", icao: "KSEA", name: "Seattle-Tacoma", city: "Seattle", country: "Etats-Unis", lat: 47.4502, lng: -122.3088 },
    { iata: "PDX", icao: "KPDX", name: "Portland", city: "Portland", country: "Etats-Unis", lat: 45.5898, lng: -122.5951 },
    { iata: "LAS", icao: "KLAS", name: "Harry Reid", city: "Las Vegas", country: "Etats-Unis", lat: 36.0840, lng: -115.1537 },
    { iata: "HNL", icao: "PHNL", name: "Daniel K. Inouye", city: "Honolulu", country: "Etats-Unis", lat: 21.3245, lng: -157.9251 },

    // ============================================
    // CANADA
    // ============================================
    { iata: "YYZ", icao: "CYYZ", name: "Toronto Pearson", city: "Toronto", country: "Canada", lat: 43.6772, lng: -79.6306 },
    { iata: "YVR", icao: "CYVR", name: "Vancouver", city: "Vancouver", country: "Canada", lat: 49.1967, lng: -123.1815 },
    { iata: "YUL", icao: "CYUL", name: "Montreal-Trudeau", city: "Montreal", country: "Canada", lat: 45.4706, lng: -73.7408 },
    { iata: "YYC", icao: "CYYC", name: "Calgary", city: "Calgary", country: "Canada", lat: 51.1225, lng: -114.0134 },
    { iata: "YEG", icao: "CYEG", name: "Edmonton", city: "Edmonton", country: "Canada", lat: 53.3097, lng: -113.5797 },
    { iata: "YOW", icao: "CYOW", name: "Ottawa Macdonald-Cartier", city: "Ottawa", country: "Canada", lat: 45.3225, lng: -75.6692 },

    // ============================================
    // MEXICO / CENTRAL AMERICA / CARIBBEAN
    // ============================================
    { iata: "MEX", icao: "MMMX", name: "Benito Juarez", city: "Mexico", country: "Mexique", lat: 19.4363, lng: -99.0721 },
    { iata: "CUN", icao: "MMUN", name: "Cancun", city: "Cancun", country: "Mexique", lat: 21.0365, lng: -86.8771 },
    { iata: "GDL", icao: "MMGL", name: "Miguel Hidalgo", city: "Guadalajara", country: "Mexique", lat: 20.5218, lng: -103.3111 },
    { iata: "SJU", icao: "TJSJ", name: "Luis Munoz Marin", city: "San Juan", country: "Porto Rico", lat: 18.4394, lng: -66.0018 },
    { iata: "PTY", icao: "MPTO", name: "Tocumen", city: "Panama City", country: "Panama", lat: 9.0714, lng: -79.3835 },
    { iata: "SJO", icao: "MROC", name: "Juan Santamaria", city: "San Jose", country: "Costa Rica", lat: 9.9939, lng: -84.2088 },

    // ============================================
    // SOUTH AMERICA
    // ============================================
    { iata: "GRU", icao: "SBGR", name: "Guarulhos", city: "Sao Paulo", country: "Bresil", lat: -23.4356, lng: -46.4731 },
    { iata: "GIG", icao: "SBGL", name: "Galeao", city: "Rio de Janeiro", country: "Bresil", lat: -22.8100, lng: -43.2506 },
    { iata: "EZE", icao: "SAEZ", name: "Ministro Pistarini", city: "Buenos Aires", country: "Argentine", lat: -34.8222, lng: -58.5358 },
    { iata: "SCL", icao: "SCEL", name: "Arturo Merino Benitez", city: "Santiago", country: "Chili", lat: -33.3930, lng: -70.7858 },
    { iata: "BOG", icao: "SKBO", name: "El Dorado", city: "Bogota", country: "Colombie", lat: 4.7016, lng: -74.1469 },
    { iata: "LIM", icao: "SPJC", name: "Jorge Chavez", city: "Lima", country: "Perou", lat: -12.0219, lng: -77.1143 },
    { iata: "CCS", icao: "SVMI", name: "Simon Bolivar", city: "Caracas", country: "Venezuela", lat: 10.6012, lng: -66.9912 },

    // ============================================
    // MIDDLE EAST
    // ============================================
    { iata: "DXB", icao: "OMDB", name: "Dubai", city: "Dubai", country: "Emirats Arabes Unis", lat: 25.2528, lng: 55.3644 },
    { iata: "AUH", icao: "OMAA", name: "Abu Dhabi", city: "Abu Dhabi", country: "Emirats Arabes Unis", lat: 24.4330, lng: 54.6511 },
    { iata: "DOH", icao: "OTHH", name: "Hamad", city: "Doha", country: "Qatar", lat: 25.2731, lng: 51.6081 },
    { iata: "JED", icao: "OEJN", name: "King Abdulaziz", city: "Djeddah", country: "Arabie Saoudite", lat: 21.6796, lng: 39.1565 },
    { iata: "RUH", icao: "OERK", name: "King Khalid", city: "Riyad", country: "Arabie Saoudite", lat: 24.9576, lng: 46.6988 },
    { iata: "TLV", icao: "LLBG", name: "Ben Gurion", city: "Tel Aviv", country: "Israel", lat: 32.0114, lng: 34.8867 },
    { iata: "AMM", icao: "OJAI", name: "Queen Alia", city: "Amman", country: "Jordanie", lat: 31.7226, lng: 35.9932 },
    { iata: "BEY", icao: "OLBA", name: "Rafic Hariri", city: "Beyrouth", country: "Liban", lat: 33.8209, lng: 35.4884 },
    { iata: "CAI", icao: "HECA", name: "Le Caire", city: "Le Caire", country: "Egypte", lat: 30.1219, lng: 31.4056 },

    // ============================================
    // ASIA - EAST
    // ============================================
    { iata: "NRT", icao: "RJAA", name: "Narita", city: "Tokyo", country: "Japon", lat: 35.7720, lng: 140.3929 },
    { iata: "HND", icao: "RJTT", name: "Haneda", city: "Tokyo", country: "Japon", lat: 35.5494, lng: 139.7798 },
    { iata: "KIX", icao: "RJBB", name: "Kansai", city: "Osaka", country: "Japon", lat: 34.4347, lng: 135.2441 },
    { iata: "ICN", icao: "RKSI", name: "Incheon", city: "Seoul", country: "Coree du Sud", lat: 37.4602, lng: 126.4407 },
    { iata: "PEK", icao: "ZBAA", name: "Beijing Capital", city: "Pekin", country: "Chine", lat: 40.0799, lng: 116.6031 },
    { iata: "PKX", icao: "ZBAD", name: "Beijing Daxing", city: "Pekin", country: "Chine", lat: 39.5098, lng: 116.4105 },
    { iata: "PVG", icao: "ZSPD", name: "Pudong", city: "Shanghai", country: "Chine", lat: 31.1434, lng: 121.8052 },
    { iata: "SHA", icao: "ZSSS", name: "Hongqiao", city: "Shanghai", country: "Chine", lat: 31.1979, lng: 121.3363 },
    { iata: "CAN", icao: "ZGGG", name: "Baiyun", city: "Guangzhou", country: "Chine", lat: 23.3924, lng: 113.2988 },
    { iata: "HKG", icao: "VHHH", name: "Hong Kong", city: "Hong Kong", country: "Hong Kong", lat: 22.3080, lng: 113.9185 },
    { iata: "TPE", icao: "RCTP", name: "Taiwan Taoyuan", city: "Taipei", country: "Taiwan", lat: 25.0797, lng: 121.2342 },

    // ============================================
    // ASIA - SOUTHEAST
    // ============================================
    { iata: "SIN", icao: "WSSS", name: "Changi", city: "Singapour", country: "Singapour", lat: 1.3644, lng: 103.9915 },
    { iata: "BKK", icao: "VTBS", name: "Suvarnabhumi", city: "Bangkok", country: "Thailande", lat: 13.6900, lng: 100.7501 },
    { iata: "DMK", icao: "VTBD", name: "Don Mueang", city: "Bangkok", country: "Thailande", lat: 13.9126, lng: 100.6068 },
    { iata: "KUL", icao: "WMKK", name: "Kuala Lumpur", city: "Kuala Lumpur", country: "Malaisie", lat: 2.7456, lng: 101.7099 },
    { iata: "CGK", icao: "WIII", name: "Soekarno-Hatta", city: "Jakarta", country: "Indonesie", lat: -6.1256, lng: 106.6558 },
    { iata: "DPS", icao: "WADD", name: "Ngurah Rai", city: "Bali", country: "Indonesie", lat: -8.7482, lng: 115.1672 },
    { iata: "MNL", icao: "RPLL", name: "Ninoy Aquino", city: "Manille", country: "Philippines", lat: 14.5086, lng: 121.0198 },
    { iata: "SGN", icao: "VVTS", name: "Tan Son Nhat", city: "Ho Chi Minh", country: "Vietnam", lat: 10.8188, lng: 106.6520 },
    { iata: "HAN", icao: "VVNB", name: "Noi Bai", city: "Hanoi", country: "Vietnam", lat: 21.2212, lng: 105.8072 },

    // ============================================
    // ASIA - SOUTH
    // ============================================
    { iata: "DEL", icao: "VIDP", name: "Indira Gandhi", city: "New Delhi", country: "Inde", lat: 28.5562, lng: 77.1000 },
    { iata: "BOM", icao: "VABB", name: "Chhatrapati Shivaji", city: "Mumbai", country: "Inde", lat: 19.0896, lng: 72.8656 },
    { iata: "BLR", icao: "VOBL", name: "Kempegowda", city: "Bangalore", country: "Inde", lat: 13.1986, lng: 77.7066 },
    { iata: "MAA", icao: "VOMM", name: "Chennai", city: "Chennai", country: "Inde", lat: 12.9941, lng: 80.1709 },
    { iata: "CCU", icao: "VECC", name: "Netaji Subhas Chandra Bose", city: "Kolkata", country: "Inde", lat: 22.6547, lng: 88.4467 },
    { iata: "CMB", icao: "VCBI", name: "Bandaranaike", city: "Colombo", country: "Sri Lanka", lat: 7.1808, lng: 79.8841 },

    // ============================================
    // OCEANIA
    // ============================================
    { iata: "SYD", icao: "YSSY", name: "Kingsford Smith", city: "Sydney", country: "Australie", lat: -33.9399, lng: 151.1753 },
    { iata: "MEL", icao: "YMML", name: "Melbourne Tullamarine", city: "Melbourne", country: "Australie", lat: -37.6690, lng: 144.8410 },
    { iata: "BNE", icao: "YBBN", name: "Brisbane", city: "Brisbane", country: "Australie", lat: -27.3842, lng: 153.1175 },
    { iata: "PER", icao: "YPPH", name: "Perth", city: "Perth", country: "Australie", lat: -31.9403, lng: 115.9672 },
    { iata: "AKL", icao: "NZAA", name: "Auckland", city: "Auckland", country: "Nouvelle-Zelande", lat: -37.0082, lng: 174.7850 },
    { iata: "WLG", icao: "NZWN", name: "Wellington", city: "Wellington", country: "Nouvelle-Zelande", lat: -41.3272, lng: 174.8053 },
    { iata: "CHC", icao: "NZCH", name: "Christchurch", city: "Christchurch", country: "Nouvelle-Zelande", lat: -43.4894, lng: 172.5322 },

    // ============================================
    // AFRICA
    // ============================================
    { iata: "JNB", icao: "FAOR", name: "O.R. Tambo", city: "Johannesburg", country: "Afrique du Sud", lat: -26.1392, lng: 28.2460 },
    { iata: "CPT", icao: "FACT", name: "Cape Town", city: "Le Cap", country: "Afrique du Sud", lat: -33.9715, lng: 18.6021 },
    { iata: "CMN", icao: "GMMN", name: "Mohammed V", city: "Casablanca", country: "Maroc", lat: 33.3675, lng: -7.5898 },
    { iata: "RAK", icao: "GMMX", name: "Marrakech Menara", city: "Marrakech", country: "Maroc", lat: 31.6069, lng: -8.0363 },
    { iata: "ALG", icao: "DAAG", name: "Houari Boumediene", city: "Alger", country: "Algerie", lat: 36.6910, lng: 3.2154 },
    { iata: "TUN", icao: "DTTA", name: "Tunis-Carthage", city: "Tunis", country: "Tunisie", lat: 36.8510, lng: 10.2272 },
    { iata: "NBO", icao: "HKJK", name: "Jomo Kenyatta", city: "Nairobi", country: "Kenya", lat: -1.3192, lng: 36.9278 },
    { iata: "ADD", icao: "HAAB", name: "Bole", city: "Addis Abeba", country: "Ethiopie", lat: 8.9779, lng: 38.7993 },
    { iata: "LOS", icao: "DNMM", name: "Murtala Muhammed", city: "Lagos", country: "Nigeria", lat: 6.5774, lng: 3.3212 },
    { iata: "ACC", icao: "DGAA", name: "Kotoka", city: "Accra", country: "Ghana", lat: 5.6052, lng: -0.1668 }
];

// Total: ~250 aeroports majeurs mondiaux
