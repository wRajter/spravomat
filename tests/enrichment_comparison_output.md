# LLM enrichment comparison

Prompt temperature 0.3, 3 runs/model. Models: gemini-3.1-flash-lite, gpt-4.1-mini, claude-haiku-4-5.


## Cluster 20 — 4 media, 6 articles [large (>=4 media)]

**Sources:**

- `aktuality` Von der Leyenová víta nového premiéra Ukrajiny Koreckého. Sľubuje plnú podporu pri reformách a v ceste do EÚ
- `aktuality` Novým predsedom ukrajinskej vlády sa stal šéf Naftohazu Serhij Koreckyj
- `teraz_sk` Ukrajinský parlament schválil novú vládu premiéra Serhija Koreckého
- `sita` Šéfka EK zablahoželala k vymenovaniu novému premiérovi Ukrajiny, verí v pokrok v jej integrácii do EÚ
- `sita` Ukrajinský parlament vymenoval nového premiéra, stal sa ním šéf Naftohazu Serhij Koreckyj
- `24_hodin` Ukrajinský parlament vymenoval nového premiéra, stal sa ním šéf Naftohazu Serhij Koreckyj

**Keyword title (current v1):** premiéra, ukrajinský, parlament, šéf, serhij


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Serhij Koreckyj novým premiérom Ukrajiny** — Ukrajinský parlament vymenoval Serhija Koreckého za nového predsedu vlády. / Koreckyj doteraz pôsobil ako šéf štátnej spoločnosti Naftohaz. / Európska komisia podporuje reformy a integráciu Ukrajiny pod novým vedením.
- Run 2 [JSON ✅]: **Serhij Koreckyj novým premiérom Ukrajiny** — Ukrajinský parlament vymenoval Serhija Koreckého za nového predsedu vlády. / Koreckyj doteraz pôsobil ako šéf štátnej spoločnosti Naftohaz. / Európska komisia podporuje Ukrajinu v reformách a integrácii do EÚ.
- Run 3 [JSON ✅]: **Serhij Koreckyj novým premiérom Ukrajiny** — Ukrajinský parlament vymenoval Serhija Koreckého za nového predsedu vlády. / Koreckyj doteraz pôsobil ako šéf štátnej spoločnosti Naftohaz. / Európska komisia sľúbila Ukrajine podporu pri reformách a integrácii do EÚ.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Nový premiér Ukrajiny Serhij Koreckyj** — Koreckyj šéfuje Naftohazu, stal sa premiérom / Parlament schválil novú vládu pod jeho vedením / EK sľubuje podporu a pokrok v integrácii do EÚ
- Run 2 [JSON ✅]: **Nový premiér Ukrajiny Serhij Koreckyj** — Koreckyj je nový predseda vlády Ukrajiny / Von der Leyenová sľubuje podporu reforiem / Cieľom je integrácia Ukrajiny do EÚ
- Run 3 [JSON ✅]: **Nový premiér Ukrajiny Serhij Koreckyj** — Koreckyj je šéf Naftohazu a nový premiér / EK sľubuje podporu reformám a integrácii do EÚ / Ukrajinský parlament schválil novú vládu

### Claude Haiku 4.5

- Run 1 [ERROR]: Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011Cd7DUELnNYRrzSJd1CaZg'}
- Run 2 [ERROR]: Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011Cd7DUa3wu649LWVSeGKEv'}
- Run 3 [ERROR]: Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011Cd7DVFQZKXq4eS5GGAVbs'}

## Cluster 68 — 4 media, 5 articles [large (>=4 media)]

**Sources:**

- `sme` Dôvera kupuje Union. Na trhu zdravotných poisťovní ostane len Penta a štát
- `aktuality` Veľký otras na trhu zdravotného poistenia: Dôvera kupuje Union zdravotnú poisťovňu
- `sita` Dôvera sa spája so zdravotnou poisťovňou Union, transakciu zafinancuje jej akcionár – VIDEO, FOTO
- `aktuality` Koniec éry troch poisťovní: Čo prinesie zlúčenie Dôvery a Unionu bežným pacientom? (Otázky a odpovede)
- `dennik_n` Panel expertov: Kúpa Unionu je pre Pentu obrovský úspech, no vyvoláva veľké obavy

**Keyword title (current v1):** dôvera, union, kupuje, trhu, poisťovní


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Dôvera kupuje Union: Koniec éry troch poisťovní** — Zdravotná poisťovňa Dôvera preberá Union, na trhu ostanú len dvaja hráči. / Transakciu financuje akcionár Dôvery, čo vyvoláva diskusie o vplyve Penty. / Odborníci analyzujú dopady zlúčenia na bežných pacientov a konkurenčné prostredie.
- Run 2 [JSON ✅]: **Dôvera kupuje Union: Koniec trhu troch poisťovní** — Zdravotná poisťovňa Dôvera preberá konkurenčný Union pod svoje krídla. / Na slovenskom trhu ostanú po transakcii iba dve poisťovne. / Odborníci hodnotia spojenie ako úspech Penty, no vyvoláva obavy.
- Run 3 [JSON ✅]: **Dôvera kupuje Union: Koniec éry troch poisťovní** — Zdravotná poisťovňa Dôvera preberá konkurenčnú poisťovňu Union. / Na slovenskom trhu ostanú už len dve poisťovne, štátna a súkromná. / Transakcia vyvoláva u expertov obavy z posilnenia vplyvu Penty.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Zlúčenie Dôvery a Union zdravotnej poisťovne** — Dôvera kupuje Union, zostanú len dve poisťovne / Transakciu financuje akcionár Dôvery / Zlúčenie vyvoláva obavy aj úspech
- Run 2 [JSON ✅]: **Zlúčenie Dôvery a Union zdravotnej poisťovne** — Dôvera kupuje Union, zostanú dve poisťovne / Transakciu financuje akcionár Dôvery / Zlúčenie vyvoláva obavy aj úspech
- Run 3 [JSON ✅]: **Zlúčenie Dôvery a Union zdravotnej poisťovne** — Dôvera kupuje Union, zostávajú len dve poisťovne / Transakciu financuje akcionár Dôvery / Zlúčenie vyvoláva obavy aj úspechy

### Claude Haiku 4.5

- Run 1 [ERROR]: Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'Overloaded'}, 'request_id': 'req_011Cd7DWETHkbPcsoaw6eQ6D'}
- Run 2 [JSON ✅]: **Dôvera kupuje Union: zmena na trhu zdravotného poistenia** — Poisťovňa Dôvera prevezme zdravotnú poisťovňu Union v rámci strategickej transakcie. / Na slovenskom trhu zdravotného poistenia ostanú len tri hráči: Dôvera, Penta a štátna poisťovňa. / Zlúčenie vyvoláva obavy o dopad na pacientov a konkurenciu na trhu zdravotného poistenia.
- Run 3 [JSON ✅]: **Dôvera kupuje Union: Zmena na trhu zdravotného poistenia** — Dôvera prevezme zdravotnú poisťovňu Union v rámci veľkej transakcie. / Na trhu ostanú len tri hráči: Dôvera, Penta a štátna poisťovňa. / Zlúčenie vyvoláva obavy z dopadov na pacientov a konkurenciu.

## Cluster 12 — 4 media, 5 articles [large (>=4 media)]

**Sources:**

- `sme` Urážky, vojna a pomsta. Rivalita medzi Anglickom a Argentínou prerástla rámec futbalu
- `sita` Messi sa konečne stretne s Anglickom – na sklonku kariéry a v semifinále MS
- `24_hodin` Messi sa konečne stretne s Anglickom – na sklonku kariéry a v semifinále MS
- `sita` Futbal: Argentína otočila v závere zápasu proti Anglicku a postúpila do finále šampionátu – FOTO
- `aktuality` Lionel Messi pred finále vyzdvihol Španielov a poslal odkaz do milovanej Barcelony

**Keyword title (current v1):** messi, anglickom, kariéry, konečne, stretne


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Futbalová rivalita Argentíny a Anglicka na MS** — Historická rivalita medzi Argentínou a Anglickom presahuje hranice športu. / Messi v semifinále MS doviedol Argentínu k víťazstvu nad Anglickom. / Argentína po dramatickom obrate v závere postúpila do finále šampionátu.
- Run 2 [JSON ✅]: **Futbalová rivalita Argentíny a Anglicka na MS** — Historická rivalita medzi Argentínou a Anglickom presahuje hranice športu. / Messi v semifinále MS doviedol Argentínu k víťazstvu nad Anglickom. / Argentína po dramatickom obrate v závere zápasu postupuje do finále.
- Run 3 [JSON ✅]: **Historická rivalita Argentíny a Anglicka na MS** — Futbalový zápas medzi Argentínou a Anglickom prekročil hranice športu. / Messi v semifinále MS pomohol Argentíne vyradiť anglický tím. / Po postupe do finále Messi adresoval slová Španielsku a Barcelone.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Rivalita Argentína vs Anglicko vo futbale** — Napätie a pomsta presahujú futbalové zápasy / Messi sa stretáva s Anglickom v semifinále MS / Argentína otočila zápas a postúpila do finále
- Run 2 [JSON ✅]: **Rivalita Argentíny a Anglicka vo futbale** — Napätie a pomsta presahujú futbalové zápasy / Messi sa stretáva s Anglickom v semifinále MS / Argentína otočila zápas a postúpila do finále
- Run 3 [JSON ✅]: **Rivalita Argentína vs Anglicko vo futbale** — Napätie a pomsta presahujú futbalové zápasy / Messi sa stretáva s Anglickom na MS semifinále / Argentína otočila zápas a postúpila do finále

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Argentína porazila Anglicko vo finále MS** — Historická rivalita medzi krajinami presahuje rámec futbalu / Messi sa stretol s Anglickom v semifinále na sklonku kariéry / Argentína dramaticky otočila zápas a postúpila do finále
- Run 2 [JSON ✅]: **Argentína porazila Anglicko vo finále MS** — Messi sa stretol s Anglickom v semifinále na sklonku svojej kariéry. / Argentína otočila zápas v závere a postúpila do finále šampionátu. / Medzi krajinami existuje hlboká rivalita presahujúca rámec futbalu.
- Run 3 [JSON ✅]: **Argentína porazila Anglicko vo finále MS** — Historická rivalita medzi krajinami presahuje rámec futbalu a zahŕňa politické spory. / Messi sa stretol s Anglickom v semifinále na sklonku svojej kariéry. / Argentína dramaticky otočila zápas a postúpila do finále šampionátu.

## Cluster 72 — 2 media, 2 articles [syndication (near-identical titles)]

**Sources:**

- `aktuality` Coworking v ikonickej Jurkovičovej Teplárni vstupuje pod správu Alto Real Estate
- `24_hodin` Coworking v ikonickej Jurkovičovej Teplárni vstupuje pod správu Alto Real Estate

**Keyword title (current v1):** vstupuje, teplárni, správu, real, pod


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Správa coworkingu v Jurkovičovej Teplárni prechádza pod Alto** — Spoločnosť Alto Real Estate preberá správu coworkingu v Jurkovičovej Teplárni. / Ikonický priemyselný priestor v Bratislave mení svojho prevádzkovateľa. / Zmena správy ovplyvní fungovanie známeho coworkingového centra v hlavnom meste.
- Run 2 [JSON ✅]: **Správa coworkingu v Jurkovičovej Teplárni prechádza pod Alto** — Spoločnosť Alto Real Estate preberá správu coworkingu v Jurkovičovej Teplárni. / Ikonické bratislavské priestory menia svojho doterajšieho správcu. / Zmena prináša novú éru pre tento známy industriálny pracovný priestor.
- Run 3 [JSON ✅]: **Správa coworkingu v Jurkovičovej Teplárni prechádza pod Alto** — Spoločnosť Alto Real Estate preberá správu coworkingu v Jurkovičovej Teplárni. / Ikonický industriálny priestor v Bratislave mení svojho doterajšieho správcu. / Zmena správy ovplyvní prevádzku zdieľaných kancelárií v tejto historickej budove.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Coworking v Jurkovičovej Teplárni pod Alto Real Estate** — Coworkingové priestory v historickej teplárni / Správa prevzatá spoločnosťou Alto Real Estate / Nová etapa rozvoja coworkingu v ikonickej budove
- Run 2 [JSON ✅]: **Coworking v Jurkovičovej Teplárni pod Alto Real Estate** — Správa coworkingu prechádza na Alto Real Estate / Priestor sa nachádza v ikonickej Jurkovičovej Teplárni / Zmena správy ovplyvní prevádzku coworkingu
- Run 3 [JSON ✅]: **Správa coworkingu v Jurkovičovej Teplárni** — Coworking prevzala spoločnosť Alto Real Estate / Priestor sa nachádza v ikonickej teplárni / Zmena správy ovplyvní prevádzku coworkingu

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Coworking v Jurkovičovej Teplárni pod Alto Real Estate** — Ikonická budova Jurkovičovej Teplárne sa transformuje na moderný coworking priestor / Alto Real Estate prevzala správu a riadenie nového coworking projektu / Projekt spája historickú architektúru s moderným pracovným prostredím
- Run 2 [JSON ✅]: **Coworking v Jurkovičovej Teplárni pod Alto Real Estate** — Ikonická Jurkovičova Teplárňa sa transformuje na moderný coworking priestor. / Alto Real Estate prevzala správu a riadenie tohto projektu. / Projekt spája históriu budovy s moderným pracovným prostredím.
- Run 3 [JSON ✅]: **Jurkovičova Teplárňa zmení správcu na Alto Real Estate** — Coworking priestory v historickej Jurkovičovej Teplárni prejdú pod správu Alto Real Estate / Ide o ikonickú budovu, ktorá sa transformuje na moderný pracovný priestor / Zmena správy znamená nový manažment a potenciálny rozvoj coworkingového projektu

## Cluster 87 — 3 media, 3 articles [syndication (near-identical titles)]

**Sources:**

- `aktuality` Pri Trenčíne zomrel vodič po čelnej zrážke s policajným autom
- `sita` Policajti sa čelne zrazili s osobným autom, 78-ročný vodič nehodu neprežil – VIDEO, FOTO
- `24_hodin` Policajti sa čelne zrazili s osobným autom, 78-ročný vodič nehodu neprežil – VIDEO, FOTO

**Keyword title (current v1):** autom, vodič, ročný, policajti, foto


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Smrteľná čelná zrážka s policajným autom pri Trenčíne** — Pri Trenčíne došlo k tragickej čelnej zrážke policajného a osobného auta. / Osemdesiatsedemročný vodič osobného vozidla utrpel zranenia nezlučiteľné so životom. / Polícia okolnosti a presné príčiny tejto vážnej dopravnej nehody vyšetruje.
- Run 2 [JSON ✅]: **Smrteľná čelná zrážka s policajným autom pri Trenčíne** — Pri Trenčíne došlo k tragickej čelnej zrážke policajného a osobného auta. / Sedemdesiatosemročný vodič osobného vozidla utrpel zranenia, ktorým na mieste podľahol. / Okolnosti a príčiny tejto vážnej dopravnej nehody sú predmetom policajného vyšetrovania.
- Run 3 [JSON ✅]: **Smrteľná čelná zrážka s policajným autom pri Trenčíne** — Pri Trenčíne došlo k tragickej čelnej zrážke policajného a osobného auta. / Nehodu neprežil 78-ročný vodič osobného motorového vozidla. / Polícia okolnosti a príčiny tejto fatálnej dopravnej nehody aktuálne vyšetruje.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Tragická čelná zrážka pri Trenčíne** — Zrážka policajného a osobného auta / 78-ročný vodič nehodu neprežil / Udalosť dokumentovaná videom a fotkami
- Run 2 [JSON ✅]: **Tragická čelná zrážka pri Trenčíne** — Vodič 78 rokov zomrel pri nehode / Zrážka s policajným autom / Policajti sa zúčastnili nehody
- Run 3 [JSON ✅]: **Tragická čelná zrážka pri Trenčíne** — Zrážka policajného auta s osobným vozidlom / 78-ročný vodič pri nehode zomrel / Policajti sa zúčastnili na nehode

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Tragická čelná zrážka policajného auta pri Trenčíne** — Pri Trenčíne došlo k čelnej zrážke medzi policajným autom a osobným vozidlom. / Vodič osobného auta, 78-ročný muž, v nehode zomrel. / Incident bol zdokumentovaný na videu a fotografiách.
- Run 2 [JSON ✅]: **Tragická čelná zrážka policajného auta pri Trenčíne** — Policajné auto sa čelne zrazilo s osobným vozidlom pri Trenčíne. / Vodič osobného auta, 78-ročný muž, v nehode zomrel. / Incident bol zdokumentovaný fotografiami a videom.
- Run 3 [JSON ✅]: **Tragická čelná zrážka policajného auta pri Trenčíne** — Pri Trenčíne sa čelne zrazilo policajné auto s osobným vozidlom. / Vodič osobného auta, 78-ročný muž, v nehode zomrel. / Incident bol zdokumentovaný na videu a fotografiách.

## Cluster 2 — 2 media, 5 articles [small (2 media)]

**Sources:**

- `sita` Splnený sen. Krajný obranca Pedro Porro gólom prispel k postupu Španielov do finále MS 2026
- `sita` Madrid zaplavila eufória. Španieli po vyradení Francúzska veria, že druhý titul je na dosah – VIDEO
- `sita` Francúzske útočné hviezdy zhasli, vypol ich úžasný kolektívny výkon Španielska – VIDEO
- `24_hodin` Splnený sen. Krajný obranca Pedro Porro gólom prispel k postupu Španielov do finále MS 2026
- `24_hodin` Francúzske útočné hviezdy zhasli, vypol ich úžasný kolektívny výkon Španielska – VIDEO

**Keyword title (current v1):** video, španielska, úžasný, útočné, zhasli


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Španielsko postupuje do finále futbalových MS 2026** — Španielsko po víťazstve nad Francúzskom postúpilo do finále svetového šampionátu. / Pedro Porro prispel k dôležitému triumfu svojho tímu rozhodujúcim gólom. / Španielsky kolektívny výkon úspešne eliminoval hviezdy francúzskeho národného tímu.
- Run 2 [JSON ✅]: **Španielsko postupuje do finále futbalových MS 2026** — Španielsko po víťazstve nad Francúzskom postúpilo do finále svetového šampionátu. / Pedro Porro prispel k dôležitému triumfu nad favoritom streleným gólom. / Španielsky tím predviedol skvelý kolektívny výkon a vyradil francúzske hviezdy.
- Run 3 [JSON ✅]: **Španielsko postupuje do finále futbalových MS 2026** — Španielsko po víťazstve nad Francúzskom postúpilo do finále svetového šampionátu. / Pedro Porro prispel k dôležitému triumfu nad hviezdnym francúzskym výberom. / Španielski fanúšikovia v Madride oslavujú nádej na zisk druhého titulu.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Španielsko vo finále MS 2026** — Pedro Porro rozhodol kľúčovým gólom / Španieli vyradili Francúzsko kolektívne / Madrid oslavuje druhý titul na dosah
- Run 2 [JSON ✅]: **Španielsko vo finále MS 2026** — Pedro Porro strelil rozhodujúci gól / Španieli vyradili Francúzsko kolektívnym výkonom / Madrid oslavuje druhý titul na dosah
- Run 3 [JSON ✅]: **Španielsko vo finále MS 2026** — Pedro Porro strelil rozhodujúci gól / Španieli vyradili Francúzsko kolektívnym výkonom / Madrid zažíva eufóriu a verí v titul

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Španielsko postupuje do finále MS 2026 po výhre nad Francúzskom** — Pedro Porro strelil gól a pomohol Španielom vyradiť Francúzsko zo súťaže. / Španielski hráči podali kolektívny výkon, ktorý neutralizoval francúzske útočné hviezdy. / Madrid oslavuje postup do finále, kde Španieli chcú získať druhý svetový titul.
- Run 2 [JSON ✅]: **Španielsko postupuje do finále MS 2026 po výhre nad Francúzskom** — Pedro Porro strelil gól a pomohol Španielom vyradiť Francúzsko z turnaja / Španielska obrana a kolektívny výkon zneškodnili francúzske útočné hviezdy / Madrid oslavuje postup do finále a verí v druhý svetový titul
- Run 3 [JSON ✅]: **Španielsko postupuje do finále MS 2026 po výhre nad Francúzskom** — Pedro Porro strelil gól a pomohol Španielom vyradiť Francúzsko z turnaja / Španielska obrana a kolektívny výkon zastavili francúzske útočné hviezdy / Madrid oslavuje postup do finále, Španieli veria v druhý svetový titul

## Cluster 309 — 2 media, 4 articles [small (2 media)]

**Sources:**

- `sita` USA dokončili najnovšiu vlnu útokov na Irán, Trump hrozí ďalšou eskaláciou
- `sita` USA zaútočili na iránske ciele, Teherán odpovedal údermi na spojencov Washingtonu
- `24_hodin` USA zaútočili na iránske ciele, Teherán odpovedal údermi na spojencov Washingtonu
- `24_hodin` USA dokončili najnovšiu vlnu útokov na Irán, Trump hrozí ďalšou eskaláciou

**Keyword title (current v1):** usa, spojencov, iránske, odpovedal, teherán


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Vojenská eskalácia napätia medzi USA a Iránom** — USA uskutočnili sériu vojenských útokov na iránske ciele. / Irán reagoval odvetnými údermi na spojencov Washingtonu v regióne. / Donald Trump varuje pred ďalším stupňovaním vojenského konfliktu.
- Run 2 [JSON ✅]: **Vojenská eskalácia napätia medzi USA a Iránom** — USA uskutočnili sériu vojenských útokov na iránske ciele. / Irán reagoval odvetnými údermi na spojencov Washingtonu v regióne. / Donald Trump varuje pred ďalším stupňovaním vojenského konfliktu.
- Run 3 [JSON ✅]: **Vojenská eskalácia napätia medzi USA a Iránom** — USA uskutočnili sériu vojenských útokov na iránske ciele. / Irán reagoval odvetnými údermi na spojencov Washingtonu v regióne. / Donald Trump varuje pred ďalšou eskaláciou konfliktu v oblasti.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Napätie medzi USA a Iránom eskaluje** — USA zaútočili na iránske ciele / Irán odpovedal údermi na spojencov USA / Trump hrozí ďalšou eskaláciou konfliktu
- Run 2 [JSON ✅]: **Napätie medzi USA a Iránom eskaluje** — USA zaútočili na iránske ciele / Irán odpovedal údermi na spojencov USA / Trump hrozí ďalšou eskaláciou konfliktu
- Run 3 [JSON ✅]: **Napätie medzi USA a Irán eskaluje** — USA vykonali útoky na iránske ciele / Irán reagoval údermi na amerických spojencov / Trump hrozí ďalšou eskaláciou konfliktu

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Eskalácia konfliktu medzi USA a Iránom** — USA vykonali útoky na iránske ciele, Trump hrozí ďalšou eskaláciou konfliktu / Irán odpovedal údermi na spojencov Spojených štátov ako reakciu / Napätie medzi krajinami sa zvyšuje s hrozbou ďalších vojenských akcií
- Run 2 [JSON ✅]: **Eskalácia konfliktu medzi USA a Iránom** — USA vykonali útoky na iránske ciele, Trump hrozí ďalšou eskaláciou konfliktu. / Irán odpovedal údermi na spojencov Spojených štátov ako reakciu. / Napätie medzi krajinami sa zvyšuje s hrozbou ďalších vojenských akcií.
- Run 3 [JSON ✅]: **Eskalácia konfliktu medzi USA a Iránom** — USA vykonali útoky na iránske ciele, Trump hrozí ďalšou eskaláciou konfliktu / Irán odpovedal údermi na spojencov Spojených štátov amerických / Pokračuje cyklus vzájomných vojenských akcií medzi oboma krajinami

## Cluster 86 — 2 media, 4 articles [small (2 media)]

**Sources:**

- `sita` Prečo sa Anglicko a Argentína neznášajú? Rivalitu vytvorila vojna, Maradonova Božia ruka aj Beckhamova červená karta
- `sita` Argentína po postupe do finále protestovala proti britskej vojnovej lodi pri Falklandských ostrovoch
- `sita` Britský minister žiada FIFA o prešetrenie argentínskeho transparentu o Falklandoch
- `24_hodin` Britský minister žiada FIFA o prešetrenie argentínskeho transparentu o Falklandoch

**Keyword title (current v1):** žiada, prešetrenie, argentínskeho, britský, falklandoch


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Historická rivalita Anglicka a Argentíny** — Dlhodobé napätie medzi krajinami vyvolala najmä vojna o Falklandské ostrovy. / Športovú rivalitu vyostrili kontroverzné momenty futbalových zápasov Anglicka a Argentíny. / Politické spory o suverenitu Falklandov pravidelne zasahujú aj do futbalového diania.
- Run 2 [JSON ✅]: **Historická rivalita Anglicka a Argentíny** — Dlhoročné napätie medzi krajinami pramení z vojnového konfliktu o Falklandské ostrovy. / Športovú rivalitu vyostrili kontroverzné futbalové momenty Maradonu a Beckhama. / Politické spory o suverenitu ostrovov pravidelne zasahujú aj do futbalového diania.
- Run 3 [JSON ✅]: **Dlhoročná rivalita Anglicka a Argentíny** — Historické napätie medzi krajinami vyvolala vojna o Falklandské ostrovy. / Športové zápasy sú poznačené kontroverznými momentmi, ako bola Maradonova Božia ruka. / Politické spory o územie Falklandov často zasahujú aj do futbalového diania.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Rivalita Anglicka a Argentíny vo futbale a politike** — Vzťahy ovplyvnila vojna a futbalové kontroverzie / Argentína protestuje proti britskej vojnovej lodi / Británia žiada FIFA prešetriť argentínske transparenty
- Run 2 [JSON ✅]: **Rivalita Anglicka a Argentíny vo futbale a politike** — Vzťahy ovplyvnila vojna o Falklandy a futbalové momenty / Argentína protestuje proti britskej vojnovej lodi pri ostrovoch / Británia žiada FIFA prešetriť argentínske transparenty o Falklandoch
- Run 3 [JSON ✅]: **Futbalová rivalita Anglicka a Argentíny** — Rivalita vznikla kvôli vojne a futbalovým incidentom / Argentína protestovala proti britskej vojnovej lodi / Británia žiada FIFA prešetriť argentínsky transparent

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Anglicko-argentínska rivalita v futbale a politike** — Konflikt vznikol z vojny o Falklandské ostrovy a futbalových kontroverzií. / Argentína protestovala proti britskej vojnovej lodi počas postupu do finále. / Britský minister žiadal FIFA vyšetriť argentínsky transparent o Falklandoch.
- Run 2 [JSON ✅]: **Anglicko-argentínska rivalita: futbal, politika a história** — Spor medzi krajinami vznikol z vojny o Falklandské ostrovy a futbalových incidentov / Argentína počas MS protestovala proti britskej vojnovej lodi pri Falklandoch / Britský minister požiadal FIFA o vyšetrenie argentínskeho transparentu o územnom spore
- Run 3 [JSON ✅]: **Anglicko-argentínska rivalita: futbal a politika** — Konflikt vznikol z vojny o Falklandské ostrovy a futbalových incidentov. / Argentína protestuje proti britskej vojnovej lodi pri Falklandoch. / Británia žiada FIFA vyšetriť argentínsky transparent o Falklandoch.

## Cluster 24 — 3 media, 5 articles [mid (3 media)]

**Sources:**

- `aktuality` Peter Pellegrini v Karabachu ocenil Azerbajdžan ako nový zdroj stability aj plynu pre Slovensko
- `sita` Prezident Pellegrini v Azerbajdžane rokoval s premiérom, témou bola energetika aj investície – VIDEO, FOTO
- `24_hodin` Pellegrini v Azerbajdžane: Strategické partnerstvo má stáť na spoločných projektoch, nielen na obchode – VIDEO, FOTO
- `24_hodin` Pellegrini odcestoval na oficiálnu návštevu Azerbajdžanu, čakajú ho viaceré rokovania
- `24_hodin` Prezident Pellegrini v Azerbajdžane rokoval s premiérom, témou bola energetika aj investície – VIDEO, FOTO

**Keyword title (current v1):** pellegrini, video, foto, azerbajdžane, rokoval


### Gemini 3.1 Flash-Lite

- Run 1 [JSON ✅]: **Prezident Pellegrini na oficiálnej návšteve Azerbajdžanu** — Prezident rokoval o posilnení strategického partnerstva a vzájomných investíciách. / Azerbajdžan sa stáva kľúčovým zdrojom stability a plynu pre Slovensko. / Cieľom návštevy je rozvoj spoločných energetických a hospodárskych projektov.
- Run 2 [JSON ✅]: **Prezident Pellegrini na oficiálnej návšteve Azerbajdžanu** — Prezident rokoval o posilnení energetickej bezpečnosti a dodávkach plynu na Slovensko. / Témou návštevy bolo prehĺbenie strategického partnerstva a podpora vzájomných investícií. / Pellegrini ocenil Azerbajdžan ako stabilného partnera pre rozvoj spoločných projektov.
- Run 3 [JSON ✅]: **Prezident Pellegrini na oficiálnej návšteve Azerbajdžanu** — Prezident rokoval o posilnení energetickej bezpečnosti a dodávkach plynu na Slovensko. / Cieľom návštevy je budovanie strategického partnerstva a podpora spoločných investičných projektov. / Pellegrini ocenil úlohu Azerbajdžanu ako stabilného partnera pre slovenskú ekonomiku.

### GPT-4.1 mini

- Run 1 [JSON ✅]: **Pellegrini v Azerbajdžane: Energetika a investície** — Rokovania o energetike a investíciách s premiérom / Azerbajdžan ako nový zdroj plynu pre Slovensko / Strategické partnerstvo založené na spoločných projektoch
- Run 2 [JSON ✅]: **Pellegriniho návšteva a spolupráca s Azerbajdžanom** — Diskusia o energetike a dodávkach plynu / Podpora strategického partnerstva a investícií / Viaceré rokovania s azerbajdžanským premiérom
- Run 3 [JSON ✅]: **Pellegrini a Azerbajdžan: Energetika a partnerstvo** — Diskusia o energetike a investíciách / Azerbajdžan ako nový zdroj plynu pre Slovensko / Strategické partnerstvo nadobúda spoločné projekty

### Claude Haiku 4.5

- Run 1 [JSON ✅]: **Pellegrini v Azerbajdžane: Energia a strategické partnerstvo** — Prezident rokoval s azerbajdžanskou vládou o energetike a investíciách / Azerbajdžan predstavuje nový zdroj stability a plynu pre Slovensko / Strategické partnerstvo má byť založené na spoločných projektoch
- Run 2 [JSON ✅]: **Pellegrini v Azerbajdžane: Energia a strategické partnerstvo** — Prezident rokoval s azerbajdžanským premiérom o energetike a investičných projektoch / Azerbajdžan predstavuje nový zdroj stability a plynu pre Slovenskú republiku / Strategické partnerstvo má byť založené na spoločných projektoch, nie len obchode
- Run 3 [JSON ✅]: **Pellegrini v Azerbajdžane: Energia a strategické partnerstvo** — Prezident rokoval s azerbajdžanským premiérom o energetike a investičných projektoch / Azerbajdžan predstavuje nový zdroj stability a plynu pre Slovenskú republiku / Strategické partnerstvo má byť založené na spoločných projektoch, nie len obchode
