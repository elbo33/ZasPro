# exercise_topics — per-requirement exercise coverage (M4 input)

Built by `zaspro.knowledge.aggregate.rebuild_exercise_topics` from the reviewed `chunk_mappings`. **primary** = the exercise's primary requirement; **touch** = primary or approved secondary. Knowledge extraction aggregates over *touch*; the histogram is here so the set is visible before extraction (SPEC §11).

Materialised: 263 exercises with topics (263 primary + 416 secondary rows). Skipped: 3 with an unsettled primary mapping (rejected / still in review), 0 with no mapping.

## Histogram over the 73 podstawowy requirements

| exercises per requirement | primary | touch |
|---|---|---|
| 0 | 13 | 3 |
| 1-2 | 20 | 8 |
| 3-4 | 15 | 9 |
| 5+ | 25 | 53 |

Covered (primary >= 1): **60 / 73**.  Covered (touch >= 1): **70 / 73**.

## Per requirement

| code | primary | touch | requirement |
|---|---|---|---|
| `I.1` | 0 | 30 | wykonuje działania (dodawanie, odejmowanie, mnożenie, dzielenie, potęgowanie, pierwiastkowanie, logarytmowanie) w zbiorze liczb rzeczywistych |
| `I.2` | 7 | 9 | przeprowadza proste dowody dotyczące podzielności liczb całkowitych i reszt z dzielenia, np.: |
| `I.3` | 1 | 4 | stosuje własności pierwiastków dowolnego stopnia, w tym pierwiastków stopnia nieparzystego z liczb ujemnych |
| `I.4` | 9 | 17 | stosuje związek pierwiastkowania z potęgowaniem oraz prawa działań na potęgach i pierwiastkach |
| `I.5` | 0 | 0 | stosuje monotoniczność potęgowania, w szczególności własności dla podstawy większej niż 1 oraz z przedziału (0, 1) |
| `I.6` | 0 | 19 | posługuje się pojęciem przedziału liczbowego, zaznacza przedziały na osi liczbowej |
| `I.7` | 5 | 5 | stosuje interpretację geometryczną i algebraiczną wartości bezwzględnej, rozwiązuje proste równania z wartością bezwzględną |
| `I.8` | 3 | 4 | wykorzystuje własności potęgowania i pierwiastkowania w sytuacjach praktycznych, w tym do obliczania procentów składanych, zysków z lokat i kosztów kredytów |
| `I.9` | 7 | 7 | stosuje związek logarytmowania z potęgowaniem, posługuje się wzorami na logarytm iloczynu, logarytm ilorazu i logarytm potęgi |
| `II.1` | 6 | 20 | stosuje wzory skróconego mnożenia na kwadrat sumy, kwadrat różnicy i różnicę kwadratów |
| `II.2` | 1 | 11 | dodaje, odejmuje i mnoży wielomiany jednej i wielu zmiennych |
| `II.3` | 0 | 15 | wyłącza poza nawias jednomian z sumy algebraicznej |
| `II.4` | 3 | 4 | mnoży i dzieli wyrażenia wymierne |
| `III.1` | 4 | 23 | przekształca równania i nierówności w sposób równoważny, w tym równania wymierne prowadzące do równania liniowego |
| `III.2` | 0 | 1 | interpretuje równania i nierówności liniowe sprzeczne oraz tożsamościowe |
| `III.3` | 3 | 5 | rozwiązuje nierówności liniowe z jedną niewiadomą |
| `III.4` | 2 | 12 | rozwiązuje równania i nierówności kwadratowe |
| `III.5` | 10 | 13 | rozwiązuje równania wielomianowe dla wielomianów doprowadzonych do postaci iloczynowej |
| `IV.1` | 3 | 9 | rozwiązuje układy równań liniowych z dwiema niewiadomymi, podaje interpretację geometryczną układów oznaczonych, nieoznaczonych i sprzecznych |
| `IV.2` | 6 | 6 | stosuje układy równań do rozwiązywania zadań tekstowych |
| `V.1` | 1 | 8 | określa funkcje jako jednoznaczne przyporządkowanie za pomocą opisu słownego, tabeli, wykresu, wzoru (także różnymi wzorami na różnych przedziałach) |
| `V.2` | 2 | 17 | oblicza wartość funkcji zadanej wzorem algebraicznym |
| `V.3` | 1 | 23 | odczytuje i interpretuje wartości funkcji określonych za pomocą tabel, wykresów, wzorów itp., również w sytuacjach wielokrotnego użycia tego samego źródła informacji lub kilku źródeł jednocześnie |
| `V.4` | 14 | 23 | odczytuje z wykresu funkcji: dziedzinę, zbiór wartości, miejsca zerowe, przedziały monotoniczności, przedziały, w których funkcja przyjmuje wartości większe (nie mniejsze) lub mniejsze (nie większe) od danej liczby, największe i najmniejsze wartości funkcji (o ile istnieją) w danym przedziale domkniętym oraz argumenty, dla których wartości największe i najmniejsze są przez funkcję przyjmowane |
| `V.5` | 8 | 16 | interpretuje współczynniki występujące we wzorze funkcji liniowej |
| `V.6` | 3 | 12 | wyznacza wzór funkcji liniowej na podstawie informacji o jej wykresie lub o jej własnościach |
| `V.7` | 0 | 6 | szkicuje wykres funkcji kwadratowej zadanej wzorem |
| `V.8` | 7 | 21 | interpretuje współczynniki występujące we wzorze funkcji kwadratowej w postaci ogólnej, kanonicznej i iloczynowej (jeśli istnieje) |
| `V.9` | 9 | 11 | wyznacza wzór funkcji kwadratowej na podstawie informacji o tej funkcji lub o jej wykresie |
| `V.10` | 1 | 10 | wyznacza największą i najmniejszą wartość funkcji kwadratowej w przedziale domkniętym |
| `V.11` | 5 | 13 | wykorzystuje własności funkcji liniowej i kwadratowej do interpretacji zagadnień geometrycznych, fizycznych itp., także osadzonych w kontekście praktycznym |
| `V.12` | 3 | 4 | na podstawie wykresu funkcji y = f(x) szkicuje wykresy funkcji powstałych przez przesunięcie wzdłuż osi |
| `V.13` | 0 | 0 | posługuje się funkcją odwrotnie proporcjonalną, w tym jej wykresem, do opisu i interpretacji zagadnień związanych z wielkościami odwrotnie proporcjonalnymi |
| `V.14` | 3 | 4 | posługuje się funkcjami wykładniczą i logarytmiczną, w tym ich wykresami, do opisu i interpretacji zagadnień związanych z zastosowaniami praktycznymi |
| `VI.1` | 7 | 14 | oblicza wyrazy ciągu określonego wzorem ogólnym |
| `VI.2` | 2 | 2 | oblicza początkowe wyrazy ciągów określonych rekurencyjnie |
| `VI.3` | 1 | 4 | w prostych przypadkach bada, czy ciąg jest rosnący, czy malejący |
| `VI.4` | 5 | 11 | sprawdza, czy dany ciąg jest arytmetyczny lub geometryczny |
| `VI.5` | 5 | 7 | stosuje wzór na n-ty wyraz i na sumę n początkowych wyrazów ciągu arytmetycznego |
| `VI.6` | 2 | 9 | stosuje wzór na n-ty wyraz i na sumę n początkowych wyrazów ciągu geometrycznego |
| `VI.7` | 4 | 16 | wykorzystuje własności ciągów, w tym arytmetycznych i geometrycznych, do rozwiązywania zadań, również osadzonych w kontekście praktycznym |
| `VII.1` | 2 | 16 | wykorzystuje definicje funkcji: sinus, cosinus i tangens dla kątów od 0° do 180°, w szczególności wyznacza wartości funkcji trygonometrycznych dla kątów 30°, 45°, 60° |
| `VII.2` | 8 | 10 | korzysta z jedynki trygonometrycznej oraz z definicji tangensa jako ilorazu sinusa i cosinusa |
| `VII.3` | 3 | 7 | stosuje twierdzenie cosinusów oraz wzór na pole trójkąta wyrażone przez dwa boki i sinus kąta między nimi |
| `VII.4` | 6 | 15 | oblicza kąty trójkąta prostokątnego i długości jego boków przy odpowiednich danych (rozwiązuje trójkąty prostokątne, w tym z wykorzystaniem funkcji trygonometrycznych) |
| `VIII.1` | 1 | 13 | wyznacza promienie i średnice okręgów, długości cięciw okręgów oraz odcinków stycznych, w tym z wykorzystaniem twierdzenia Pitagorasa |
| `VIII.2` | 0 | 2 | rozpoznaje trójkąty ostrokątne, prostokątne i rozwartokątne przy danych długościach boków (m.in. stosuje twierdzenie odwrotne do twierdzenia Pitagorasa i twierdzenie cosinusów); stosuje twierdzenie: w trójkącie naprzeciw większego kąta wewnętrznego leży dłuższy bok |
| `VIII.3` | 1 | 3 | rozpoznaje wielokąty foremne i korzysta z ich podstawowych własności |
| `VIII.4` | 0 | 6 | korzysta z własności kątów i przekątnych w prostokątach, równoległobokach, rombach i trapezach |
| `VIII.5` | 7 | 9 | stosuje własności kątów wpisanych i środkowych |
| `VIII.6` | 0 | 0 | stosuje wzory na pole wycinka koła i długość łuku okręgu |
| `VIII.7` | 1 | 3 | stosuje twierdzenie Talesa |
| `VIII.8` | 4 | 8 | korzysta z cech podobieństwa trójkątów |
| `VIII.9` | 2 | 3 | wykorzystuje zależności między obwodami oraz między polami figur podobnych |
| `VIII.10` | 1 | 5 | wskazuje podstawowe punkty szczególne w trójkącie: środek okręgu wpisanego w trójkąt, środek okręgu opisanego na trójkącie, ortocentrum, środek ciężkości oraz korzysta z ich własności |
| `VIII.11` | 1 | 1 | przeprowadza dowody geometryczne |
| `VIII.12` | 3 | 10 | stosuje funkcje trygonometryczne do wyznaczania długości odcinków w figurach płaskich oraz obliczania pól figur |
| `IX.1` | 6 | 12 | rozpoznaje wzajemne położenie prostych na płaszczyźnie na podstawie ich równań, w tym znajduje wspólny punkt dwóch prostych, jeśli taki istnieje |
| `IX.2` | 4 | 10 | posługuje się równaniami prostych na płaszczyźnie, w postaci kierunkowej i ogólnej, w tym wyznacza równanie prostej o zadanych własnościach (takich, jak np. przechodzenie przez dwa dane punkty, znany współczynnik kierunkowy, równoległość do innej prostej) |
| `IX.3` | 6 | 10 | oblicza odległość dwóch punktów w układzie współrzędnych |
| `IX.4` | 4 | 5 | posługuje się równaniem okręgu w postaci kanonicznej |
| `IX.5` | 0 | 1 | wyznacza obrazy okręgów i wielokątów w symetriach osiowych względem osi układu współrzędnych, symetrii środkowej (o środku w początku układu współrzędnych) |
| `X.1` | 0 | 1 | rozpoznaje wzajemne położenie prostych w przestrzeni, w szczególności proste prostopadłe nieprzecinające się |
| `X.2` | 3 | 7 | posługuje się pojęciem kąta między prostą a płaszczyzną oraz pojęciem kąta dwuściennego między półpłaszczyznami |
| `X.3` | 2 | 6 | rozpoznaje w graniastosłupach i ostrosłupach kąty między odcinkami (np. krawędziami, krawędziami i przekątnymi) oraz kąty między ścianami, oblicza miary tych kątów |
| `X.4` | 0 | 1 | rozpoznaje w walcach i w stożkach kąt między odcinkami oraz kąt między odcinkami i płaszczyznami (np. kąt rozwarcia stożka, kąt między tworzącą a podstawą), oblicza miary tych kątów |
| `X.5` | 8 | 12 | oblicza objętości i pola powierzchni graniastosłupów, ostrosłupów, walca, stożka i kuli, również z wykorzystaniem trygonometrii |
| `X.6` | 2 | 2 | wykorzystuje zależność między objętościami brył podobnych |
| `XI.1` | 1 | 12 | zlicza obiekty w prostych sytuacjach kombinatorycznych |
| `XI.2` | 6 | 12 | zlicza obiekty, stosując reguły mnożenia i dodawania (także łącznie) dla dowolnej liczby czynności, np.: |
| `XII.1` | 8 | 9 | oblicza prawdopodobieństwo w modelu klasycznym |
| `XII.2` | 15 | 15 | oblicza średnią arytmetyczną i średnią ważoną, znajduje medianę i dominantę |
| `XIII.1` | 5 | 8 | rozwiązuje zadania optymalizacyjne w sytuacjach dających się opisać funkcją kwadratową |
