from __future__ import annotations

import re
import json
from dataclasses import asdict
from dataclasses import dataclass

from .schemas import AdaptiveQuestion, TutorIntervention
from .practice_matching import AnswerMode, response_matches


@dataclass(frozen=True)
class DiagnosticItem:
    prompt: str
    options: tuple[str, ...]
    correct_option: str
    concept: str
    explanation: str
    worked_example: str
    hint: str
    practice_prompt: str
    practice_answers: tuple[str, ...]
    answer_mode: AnswerMode = "exact"


FRACTION_DIAGNOSTIC = (
    DiagnosticItem(
        "What is 3/4 + 1/4?", ("1/2", "1", "3/8", "2"), "1", "Adding like fractions",
        "When denominators are the same, add the numerators and keep the denominator: (3 + 1) / 4 = 4/4 = 1.",
        "2/5 + 3/5 = 5/5 = 1.", "Keep the denominator 4 and add 3 + 1.",
        "What is 2/8 + 4/8?", ("6/8", "3/4", "0.75"), "number",
    ),
    DiagnosticItem(
        "Which fraction is equal to 1/2?", ("2/6", "3/6", "4/6", "5/6"), "3/6", "Equivalent fractions",
        "Equivalent fractions name the same amount. Multiplying 1/2 by 3/3 gives 3/6.",
        "1/3 multiplied by 2/2 is 2/6.", "Multiply the numerator and denominator of 1/2 by the same number.",
        "Name a fraction equivalent to 2/3 with denominator 6.", ("4/6",),
    ),
    DiagnosticItem(
        "What is 5/8 - 1/8?", ("4/8", "4/16", "5/7", "6/8"), "4/8", "Subtracting like fractions",
        "With equal denominators, subtract the numerators and keep the denominator: (5 - 1) / 8 = 4/8.",
        "6/7 - 2/7 = 4/7.", "Keep the denominator 8 and subtract 1 from 5.",
        "What is 7/9 - 2/9?", ("5/9",), "number",
    ),
)


DECIMAL_DIAGNOSTIC = (
    DiagnosticItem(
        "What is 3.75 + 1.20?", ("4.95", "4.85", "3.87", "4.05"), "4.95", "Adding decimals",
        "Align equal place values, then add: 3.75 + 1.20 = 4.95.",
        "2.40 + 0.35 = 2.75.", "Line up the decimal points before adding.",
        "What is 6.4 + 2.35?", ("8.75",), "number",
    ),
    DiagnosticItem(
        "Which digit is in the hundredths place in 18.472?", ("1", "4", "7", "2"), "7", "Decimal place value",
        "The first digit to the right of the decimal is tenths and the second is hundredths, so 7 is in the hundredths place.",
        "In 5.638, the digit 3 is in the hundredths place.", "Count two places to the right of the decimal point.",
        "Which digit is in the tenths place in 9.64?", ("6",),
    ),
    DiagnosticItem(
        "Which number is greatest?", ("0.58", "0.508", "0.85", "0.805"), "0.85", "Comparing decimals",
        "Write equal decimal places: 0.580, 0.508, 0.850, and 0.805. The greatest is 0.850, or 0.85.",
        "Between 0.70 and 0.67, 0.70 is greater.", "Compare tenths first, then hundredths.",
        "Which is greater: 0.72 or 0.702?", ("0.72", "0.720"),
    ),
)


PERCENTAGE_DIAGNOSTIC = (
    DiagnosticItem(
        "What is 25% of 80?", ("20", "25", "40", "60"), "20", "Finding a percentage",
        "25% is 25/100, so 25/100 × 80 = 20.",
        "10% of 60 is 10/100 × 60 = 6.", "Convert 25% to 25/100, then multiply by 80.",
        "What is 30% of 50?", ("15",), "number",
    ),
    DiagnosticItem(
        "Which decimal equals 62%?", ("0.062", "0.62", "6.2", "62.0"), "0.62", "Converting percent to decimal",
        "Percent means per hundred. Dividing 62 by 100 gives 0.62.",
        "35% = 35/100 = 0.35.", "Move the decimal point two places left.",
        "Write 47% as a decimal.", ("0.47",), "number",
    ),
    DiagnosticItem(
        "A ₹200 item is discounted by 10%. What is the discount amount?", ("₹10", "₹20", "₹180", "₹220"), "₹20", "Percentage discount",
        "The discount is 10% of ₹200: 10/100 × 200 = ₹20.",
        "A 5% discount on ₹100 is 5/100 × 100 = ₹5.", "Find 10% of 200; do not subtract it yet.",
        "What is the discount amount when 20% is taken off ₹150?", ("₹30", "30"), "exact",
    ),
)


ALGEBRA_DIAGNOSTIC = (
    DiagnosticItem(
        "Solve x + 7 = 19.", ("10", "11", "12", "26"), "12", "Solving one-step equations",
        "Subtract 7 from both sides: x = 19 - 7 = 12.",
        "For y + 5 = 13, subtract 5 from both sides to get y = 8.", "Undo adding 7 by subtracting 7 from both sides.",
        "Solve n + 9 = 23.", ("14",), "number",
    ),
    DiagnosticItem(
        "Which expression equals 3(a + 4)?", ("3a + 4", "3a + 7", "3a + 12", "a + 12"), "3a + 12", "Distributive property",
        "Multiply 3 by each term inside the parentheses: 3 × a + 3 × 4 = 3a + 12.",
        "2(b + 5) = 2b + 10.", "Multiply both a and 4 by 3.",
        "Expand 4(y + 2).", ("4y + 8", "4y+8"),
    ),
    DiagnosticItem(
        "What is 2m - 3 when m = 5?", ("4", "7", "10", "13"), "7", "Substitution",
        "Replace m with 5: 2 × 5 - 3 = 10 - 3 = 7.",
        "When p = 4, 3p + 1 = 3 × 4 + 1 = 13.", "Replace m with 5 before calculating.",
        "Find 3k + 2 when k = 4.", ("14",), "number",
    ),
)


GEOMETRY_DIAGNOSTIC = (
    DiagnosticItem(
        "A triangle has angles 50° and 60°. What is its third angle?", ("60°", "70°", "80°", "110°"), "70°", "Triangle angle sum",
        "The angles of a triangle total 180°. The third angle is 180° - 50° - 60° = 70°.",
        "A triangle with angles 40° and 90° has third angle 180° - 40° - 90° = 50°.", "Subtract both known angles from 180°.",
        "A triangle has angles 35° and 85°. Find the third angle.", ("60°", "60"), "exact",
    ),
    DiagnosticItem(
        "What is the area of a triangle with base 10 cm and height 6 cm?", ("16 cm²", "30 cm²", "60 cm²", "120 cm²"), "30 cm²", "Triangle area",
        "Triangle area is one half × base × height: 1/2 × 10 × 6 = 30 cm².",
        "For base 8 cm and height 5 cm, area = 1/2 × 8 × 5 = 20 cm².", "Multiply base by height, then divide by 2.",
        "Find the area in cm² of a triangle with base 12 cm and height 4 cm.", ("24", "24 cm²", "24 cm2"), "exact",
    ),
    DiagnosticItem(
        "Which set of side lengths forms a right triangle?", ("3, 4, 5", "3, 4, 6", "4, 5, 6", "5, 6, 7"), "3, 4, 5", "Pythagorean relationship",
        "For a right triangle, a² + b² = c². For 3, 4, 5: 3² + 4² = 9 + 16 = 25 = 5².",
        "For 5, 12, 13: 5² + 12² = 25 + 144 = 169 = 13².", "Test whether the two smaller squares add to the largest square.",
        "Do side lengths 6, 8, and 10 form a right triangle? Answer yes or no.", ("yes",),
    ),
)


CELLS_DIAGNOSTIC = (
    DiagnosticItem(
        "Which cell structure controls what enters and leaves the cell?", ("Cell membrane", "Nucleus", "Cytoplasm", "Ribosome"), "Cell membrane", "Cell membrane function",
        "The cell membrane forms the cell boundary and controls which substances enter and leave.",
        "If a substance moves from outside a cell into it, that substance crosses the cell membrane.", "Think about the boundary around the cell.",
        "Name the structure that controls movement into and out of a cell.", ("Cell membrane", "membrane"),
    ),
    DiagnosticItem(
        "Which structure is present in plant cells but not animal cells?", ("Cell wall", "Cell membrane", "Cytoplasm", "Nucleus"), "Cell wall", "Plant and animal cells",
        "Both plant and animal cells have a membrane, cytoplasm, and a nucleus, while plant cells also have a cell wall.",
        "A diagram with a cell wall can represent a plant cell rather than an animal cell.", "Look for the structure outside the plant cell membrane.",
        "Name the rigid outer structure found in plant cells.", ("Cell wall",),
    ),
    DiagnosticItem(
        "Which order goes from smallest to largest?", ("Cell, tissue, organ, organ system", "Tissue, cell, organ, organ system", "Organ, tissue, cell, organ system", "Cell, organ, tissue, organ system"), "Cell, tissue, organ, organ system", "Levels of organization",
        "Similar cells form tissues, tissues form organs, and organs work together in organ systems.",
        "Muscle cells form muscle tissue, and several tissues can form an organ.", "Begin with one cell and group similar cells together.",
        "What level comes directly after tissue: cell, organ, or organ system?", ("organ",),
    ),
)


MATTER_DIAGNOSTIC = (
    DiagnosticItem(
        "Which change is a physical change?", ("Ice melting", "Iron rusting", "Paper burning", "Milk souring"), "Ice melting", "Physical and chemical changes",
        "Melting changes water from solid to liquid without forming a new substance, so it is a physical change.",
        "Liquid water freezing into ice is also a physical change because it remains water.", "Choose the change that keeps the same substance.",
        "Is water freezing a physical or chemical change?", ("physical", "physical change"),
    ),
    DiagnosticItem(
        "A sample has mass 60 g and volume 20 cm³. What is its density?", ("3 g/cm³", "40 g/cm³", "80 g/cm³", "1200 g/cm³"), "3 g/cm³", "Density",
        "Density equals mass divided by volume: 60 g ÷ 20 cm³ = 3 g/cm³.",
        "A 40 g sample with volume 10 cm³ has density 40 ÷ 10 = 4 g/cm³.", "Divide 60 by 20 and keep the density unit.",
        "Find the density in g/cm³ of a 45 g sample with volume 15 cm³.", ("3", "3 g/cm³", "3 g/cm3"), "exact",
    ),
    DiagnosticItem(
        "Which sample is a mixture?", ("Air", "Pure oxygen", "Pure gold", "Distilled water"), "Air", "Pure substances and mixtures",
        "Air contains several gases together, so it is a mixture. The other choices name single pure substances.",
        "Salt water contains salt and water together, so it is a mixture.", "Look for a sample containing more than one substance together.",
        "Is salt water a pure substance or a mixture?", ("mixture", "a mixture"),
    ),
)


FORCE_MOTION_DIAGNOSTIC = (
    DiagnosticItem(
        "A cyclist travels 120 m in 20 s. What is the cyclist's average speed?", ("6 m/s", "20 m/s", "100 m/s", "2400 m/s"), "6 m/s", "Average speed",
        "Average speed equals distance divided by time: 120 m ÷ 20 s = 6 m/s.",
        "Traveling 90 m in 15 s gives an average speed of 90 ÷ 15 = 6 m/s.", "Divide the distance by the time.",
        "Find the average speed in m/s for 150 m traveled in 30 s.", ("5", "5 m/s"), "exact",
    ),
    DiagnosticItem(
        "A 10 N force pushes right and a 6 N force pushes left. What is the net force?", ("4 N right", "4 N left", "16 N right", "16 N left"), "4 N right", "Net force",
        "Opposite forces subtract. The larger force is rightward, so 10 N - 6 N = 4 N right.",
        "For 9 N left and 3 N right, the net force is 6 N left.", "Subtract the smaller force and keep the larger force's direction.",
        "Find the net force for 12 N left and 5 N right.", ("7 N left", "7 newtons left"),
    ),
    DiagnosticItem(
        "When a bus stops suddenly, a standing passenger tends to keep moving forward. Which idea explains this?", ("Inertia", "Density", "Buoyancy", "Reflection"), "Inertia", "Inertia",
        "Inertia is the tendency of an object's motion to remain unchanged unless a net force acts on it, so the passenger's body tends to keep moving.",
        "When a moving cart is stopped, an unsecured object on it tends to continue moving because of inertia.", "Which idea describes resistance to a change in motion?",
        "Name the tendency of motion to remain unchanged unless a net force acts.", ("inertia",),
    ),
)


ECOSYSTEMS_DIAGNOSTIC = (
    DiagnosticItem(
        "In the food chain grass → rabbit → fox, which organism is the producer?", ("Grass", "Rabbit", "Fox", "All three"), "Grass", "Producers in food chains",
        "Grass makes its own food and begins the stated food chain, so grass is the producer.",
        "In algae → fish → heron, algae is the producer at the start of the chain.", "Choose the organism at the start that makes its own food.",
        "In leaves → caterpillar → bird, name the producer.", ("leaves", "the leaves"),
    ),
    DiagnosticItem(
        "In the food chain grass → rabbit → fox, which organism gets energy directly from grass?", ("Rabbit", "Fox", "Grass", "None"), "Rabbit", "Energy transfer in food chains",
        "The arrow from grass to rabbit shows that the rabbit gets energy directly from grass.",
        "In algae → fish → heron, the fish gets energy directly from algae.", "Follow the arrow leaving grass.",
        "In seeds → mouse → owl, which organism gets energy directly from seeds?", ("mouse", "the mouse"),
    ),
    DiagnosticItem(
        "A pond has enough food and space, but very little water remains. Which stated factor most directly limits the pond population?", ("Water", "Food", "Space", "None"), "Water", "Limiting factors",
        "The premises say food and space are sufficient but water is scarce, so water is the limiting factor.",
        "If water and space are sufficient but food is scarce, food is the limiting factor.", "Which resource does the question say is scarce?",
        "If food is scarce while water and space are sufficient, name the limiting factor.", ("food",),
    ),
)


GRAMMAR_DIAGNOSTIC = (
    DiagnosticItem(
        "Which sentence has correct subject-verb agreement?", ("The basket of apples is heavy.", "The basket of apples are heavy.", "The apples in the basket is fresh.", "The baskets is heavy."), "The basket of apples is heavy.", "Subject-verb agreement",
        "The subject is the singular noun basket, so the singular verb 'is' agrees with it.",
        "In 'The group of players is ready,' group is singular, so 'is' is correct.", "Identify the main subject, not the noun inside the phrase beginning with of.",
        "Choose the correct verb: The team of dancers (is/are) ready.", ("is",),
    ),
    DiagnosticItem(
        "Which sentence uses the pronoun correctly?", ("Maya and I completed the project.", "Maya and me completed the project.", "Her completed the project.", "Us completed the project."), "Maya and I completed the project.", "Pronoun case",
        "The pronoun is part of the sentence subject, so the subject pronoun I is correct.",
        "In 'Ravi and she arrived,' she is a subject pronoun.", "Remove Maya and test which pronoun can be the subject before completed.",
        "Complete with I or me: Arjun and ___ prepared the chart.", ("I",),
    ),
    DiagnosticItem(
        "Which sentence is punctuated correctly?", ("After the rain stopped, we continued the match.", "After the rain stopped we, continued the match.", "After, the rain stopped we continued the match.", "After the rain, stopped we continued the match."), "After the rain stopped, we continued the match.", "Introductory-clause punctuation",
        "The introductory dependent clause 'After the rain stopped' is followed by a comma before the main clause.",
        "In 'When the bell rang, the class left,' the comma separates the introductory clause.", "Place the comma after the complete introductory clause.",
        "Add the missing punctuation mark: Before class began___ we reviewed our notes.", (",", "comma"),
    ),
)


READING_DIAGNOSTIC = (
    DiagnosticItem(
        "Passage: Lina planted two seed trays. She placed one beside a sunny window and one in a dark cupboard. She gave both equal water. After a week, only the window tray had strong green shoots. Which variable did Lina change?", ("Amount of water", "Amount of light", "Type of seed tray", "Length of the week"), "Amount of light", "Identifying an experimental variable",
        "Both trays received equal water, but one received window light and the other did not, so the changed variable was the amount of light.",
        "If two plants receive equal light but different water amounts, water is the changed variable.", "Compare what was different between the two tray locations.",
        "In the passage, was light or water intentionally different between the trays?", ("light",),
    ),
    DiagnosticItem(
        "Passage: The library extended its hours during exams. Attendance rose each evening, and students asked the library to repeat the schedule next term. What is the main idea?", ("The library bought new books.", "Longer exam hours were useful to students.", "Students stopped studying at home.", "Evening attendance decreased."), "Longer exam hours were useful to students.", "Determining main idea",
        "The passage connects extended hours with higher attendance and a request to repeat them, supporting the main idea that the longer hours were useful.",
        "When several details describe benefits of a new bus route, the main idea summarizes those benefits rather than one minor detail.", "Choose the option supported by both increased attendance and the request to repeat the schedule.",
        "Did students want the extended schedule repeated? Answer yes or no.", ("yes",),
    ),
    DiagnosticItem(
        "Passage: Omar checked the sky, packed an umbrella, and moved the picnic food indoors before the first drops fell. What can the reader infer?", ("Omar expected rain.", "Omar lost the picnic food.", "The picnic had ended yesterday.", "The umbrella was broken."), "Omar expected rain.", "Making an inference",
        "Checking the sky, packing an umbrella, and moving food indoors before drops fell together support the inference that Omar expected rain.",
        "If someone wears gloves and a thick coat before leaving, those clues can support an inference that the person expects cold weather.", "Combine the clues about the sky, umbrella, and indoor food.",
        "What weather did Omar expect?", ("rain", "rainy weather"),
    ),
)


VOCABULARY_DIAGNOSTIC = (
    DiagnosticItem(
        "In the sentence 'The path was arduous, requiring hours of steep climbing,' what does arduous mean?", ("Difficult", "Short", "Crowded", "Hidden"), "Difficult", "Using context clues",
        "The phrase 'requiring hours of steep climbing' signals that arduous means difficult.",
        "In 'The fragile glass broke easily,' 'broke easily' helps show that fragile means easily damaged.", "Use the description after the comma as a clue.",
        "Give the one-word meaning of arduous in this sentence.", ("difficult", "hard"),
    ),
    DiagnosticItem(
        "Which word is the best antonym for scarce?", ("Abundant", "Limited", "Rare", "Insufficient"), "Abundant", "Antonyms",
        "Scarce means available in too small an amount, while abundant means available in a large amount, so the words are opposites.",
        "The antonym of narrow is wide.", "Choose the word meaning plentiful rather than limited.",
        "What is an antonym for ancient: modern or old?", ("modern",),
    ),
    DiagnosticItem(
        "The prefix re- means again. What does rewrite mean?", ("Write again", "Write before", "Write badly", "Stop writing"), "Write again", "Prefixes",
        "Combining re-, meaning again, with write gives the meaning write again.",
        "Rebuild means build again.", "Apply the stated meaning of re- to write.",
        "Using the meaning of re-, what does reread mean?", ("read again", "to read again"),
    ),
)


WRITING_DIAGNOSTIC = (
    DiagnosticItem(
        "Which sentence is the clearest topic sentence for a paragraph about saving water at home?", ("Homes can save water through several simple daily habits.", "Water is clear.", "Yesterday was Tuesday.", "Some cups are blue."), "Homes can save water through several simple daily habits.", "Topic sentences",
        "A topic sentence states the paragraph's controlling idea; this choice introduces saving water through daily habits.",
        "For a paragraph about safe cycling, 'Several habits help cyclists stay safe' clearly introduces the topic.", "Choose the sentence broad enough to introduce several water-saving details.",
        "Which topic does the correct sentence introduce: saving water or choosing cups?", ("saving water", "water saving"),
    ),
    DiagnosticItem(
        "Which transition best completes the sentence? 'The first trial failed. ___, the team revised the design and tried again.'", ("Therefore", "Meanwhile", "For example", "Similarly"), "Therefore", "Logical transitions",
        "Therefore shows that revising the design was a result of the failed trial.",
        "The road was flooded; therefore, the trip was postponed. The transition marks a result.", "The second action happened as a result of the first sentence.",
        "Choose the result transition: therefore or meanwhile.", ("therefore",),
    ),
    DiagnosticItem(
        "Which revision removes unnecessary repetition?", ("The final outcome was unexpected.", "The outcome was unexpected.", "The unexpected outcome was an outcome.", "The final outcome result was unexpected."), "The outcome was unexpected.", "Concise revision",
        "Outcome already means a final result, so removing final makes the sentence concise without changing its meaning.",
        "Revise 'return back' to 'return' because return already includes the idea of back.", "Remove the word whose meaning is already contained in outcome.",
        "Revise 'repeat again' by writing only the necessary verb.", ("repeat",),
    ),
)


GEOGRAPHY_DIAGNOSTIC = (
    DiagnosticItem(
        "Which coordinate gives latitude before longitude?", ("20°N, 75°E", "75°E, 20°N", "20°E, 75°N", "75°N, 20°E"), "20°N, 75°E", "Latitude and longitude order",
        "A geographic coordinate is conventionally written with latitude first and longitude second, so 20°N, 75°E has the required order.",
        "12°S, 40°W lists latitude 12°S before longitude 40°W.", "Latitude uses north or south; place it before the east-or-west longitude.",
        "Write the order using the words latitude and longitude.", ("latitude, longitude", "latitude then longitude"),
    ),
    DiagnosticItem(
        "A map scale says 1 cm represents 5 km. Two towns are 4 cm apart on the map. What is their real distance?", ("1.25 km", "9 km", "20 km", "25 km"), "20 km", "Map scale",
        "Each map centimetre represents 5 km, so 4 × 5 km = 20 km.",
        "At 1 cm = 3 km, a 2 cm map distance represents 2 × 3 = 6 km.", "Multiply the map distance by the kilometres represented by each centimetre.",
        "At 1 cm = 8 km, what distance does 3 cm represent?", ("24", "24 km"), "exact",
    ),
    DiagnosticItem(
        "Which statement describes climate rather than weather?", ("It rained this morning.", "The temperature is 18°C today.", "Summers are usually hot and dry in this region.", "A storm is expected tonight."), "Summers are usually hot and dry in this region.", "Weather and climate",
        "Climate describes usual conditions over a long period, while the other statements describe conditions or forecasts for a short time.",
        "'Winters are generally mild here' describes climate; 'today is cold' describes weather.", "Choose the statement about usual conditions, not one day.",
        "Does 'winters are usually wet here' describe weather or climate?", ("climate",),
    ),
)


HISTORY_DIAGNOSTIC = (
    DiagnosticItem(
        "Which item is a primary source for studying a historical event?", ("A diary written by a witness", "A modern textbook summary", "A recent documentary", "A student's book review"), "A diary written by a witness", "Primary and secondary sources",
        "A diary created by a witness during or near the event is direct evidence from that time, so it is a primary source.",
        "A letter written by a participant during an event is a primary source for studying that event.", "Choose the source created by someone who directly witnessed the event.",
        "Is a witness's diary a primary or secondary source?", ("primary", "primary source"),
    ),
    DiagnosticItem(
        "An agreement was signed in 1910, a protest occurred in 1912, and a law changed in 1915. Which event happened second?", ("The agreement", "The protest", "The law change", "All happened together"), "The protest", "Chronological order",
        "Ordering the stated years gives 1910, 1912, 1915, so the 1912 protest happened second.",
        "For events in 1801, 1804, and 1809, the 1804 event is second chronologically.", "Arrange the three stated years from earliest to latest.",
        "Which year comes second in this sequence: 1920, 1923, 1928?", ("1923",), "number",
    ),
    DiagnosticItem(
        "A city raised a bridge toll. The next month, fewer drivers used the bridge. Which statement identifies the effect described?", ("The toll was raised.", "Fewer drivers used the bridge.", "The bridge was built.", "The city removed the toll."), "Fewer drivers used the bridge.", "Cause and effect in sources",
        "The passage presents the toll increase first as the cause and fewer drivers afterward as the described effect.",
        "If a road closed and traffic moved elsewhere, the closure is the cause and moved traffic is the effect.", "Look for what happened after the toll increase.",
        "In the passage, did bridge use increase or decrease after the toll rose?", ("decrease", "decreased"),
    ),
)


CIVICS_DIAGNOSTIC = (
    DiagnosticItem(
        "A system states that the legislature makes laws, the executive enforces them, and the judiciary interprets them. Which branch interprets a disputed law?", ("Legislature", "Executive", "Judiciary", "Election commission"), "Judiciary", "Separation of powers",
        "The question states that the judiciary interprets laws, so the judiciary interprets the disputed law.",
        "If a town charter says its court interprets rules, the court decides what a disputed rule means.", "Match the action 'interprets' to the branch assigned that role.",
        "Name the branch that interprets laws in the stated system.", ("judiciary", "the judiciary"),
    ),
    DiagnosticItem(
        "Which action is a civic responsibility rather than an individual right?", ("Obeying lawful rules", "Expressing an opinion", "Practising a religion", "Receiving equal treatment"), "Obeying lawful rules", "Rights and responsibilities",
        "Obeying lawful rules is an obligation placed on community members, so it is a responsibility; the other choices are framed as individual rights.",
        "Serving on a jury when legally required is a civic responsibility rather than a personal freedom.", "Choose the obligation rather than a protected freedom.",
        "Classify obeying lawful rules as a right or responsibility.", ("responsibility", "a responsibility"),
    ),
    DiagnosticItem(
        "A rule requires more than half of 80 votes to win. What is the smallest winning number?", ("39", "40", "41", "80"), "41", "Majority rule",
        "Half of 80 is 40. More than half therefore begins at 41 votes.",
        "More than half of 50 requires at least 26 votes.", "Find half of 80, then add one.",
        "What is the smallest majority in a total of 100 votes?", ("51",), "number",
    ),
)


ECONOMICS_DIAGNOSTIC = (
    DiagnosticItem(
        "A family can buy either a bicycle or a tablet, but not both. If it buys the bicycle, what is the opportunity cost?", ("The tablet not bought", "The bicycle", "The family's income", "Both items"), "The tablet not bought", "Opportunity cost",
        "Opportunity cost is the next-best option given up. Buying the bicycle means giving up the tablet.",
        "If a student uses an hour to study instead of playing a game, the forgone game time is the opportunity cost.", "Identify the alternative the family gives up.",
        "If you choose tea instead of coffee, which drink is the opportunity cost?", ("coffee",),
    ),
    DiagnosticItem(
        "A shop has 10 notebooks but customers want 25 at the current price. Which condition is described?", ("Shortage", "Surplus", "Balance", "No demand"), "Shortage", "Shortage and surplus",
        "Quantity wanted, 25, is greater than quantity available, 10, so the shop has a shortage.",
        "If 30 tickets are wanted but only 20 are available, the difference describes a shortage.", "Compare how many are wanted with how many are available.",
        "If 50 items are wanted but only 40 are available, is there a shortage or surplus?", ("shortage", "a shortage"),
    ),
    DiagnosticItem(
        "A budget has ₹500. After spending ₹320, how much remains?", ("₹180", "₹220", "₹320", "₹820"), "₹180", "Budget balance",
        "Remaining budget equals starting amount minus spending: ₹500 - ₹320 = ₹180.",
        "From a ₹200 budget, spending ₹75 leaves ₹125.", "Subtract the amount spent from the starting budget.",
        "How much remains from ₹700 after spending ₹450?", ("₹250", "250"), "exact",
    ),
)


DETERMINISTIC_DIAGNOSTICS = {
    ("math", "fractions"): FRACTION_DIAGNOSTIC,
    ("math", "decimals"): DECIMAL_DIAGNOSTIC,
    ("math", "percentages"): PERCENTAGE_DIAGNOSTIC,
    ("math", "algebra"): ALGEBRA_DIAGNOSTIC,
    ("math", "geometry"): GEOMETRY_DIAGNOSTIC,
    ("science", "cells"): CELLS_DIAGNOSTIC,
    ("science", "matter"): MATTER_DIAGNOSTIC,
    ("science", "force-and-motion"): FORCE_MOTION_DIAGNOSTIC,
    ("science", "ecosystems"): ECOSYSTEMS_DIAGNOSTIC,
    ("english", "grammar"): GRAMMAR_DIAGNOSTIC,
    ("english", "reading-comprehension"): READING_DIAGNOSTIC,
    ("english", "vocabulary"): VOCABULARY_DIAGNOSTIC,
    ("english", "writing"): WRITING_DIAGNOSTIC,
    ("social", "geography"): GEOGRAPHY_DIAGNOSTIC,
    ("social", "history"): HISTORY_DIAGNOSTIC,
    ("social", "civics"): CIVICS_DIAGNOSTIC,
    ("social", "economics"): ECONOMICS_DIAGNOSTIC,
}


def diagnostic_bank(subject_id: str, chapter_id: str) -> tuple[DiagnosticItem, ...]:
    try:
        return DETERMINISTIC_DIAGNOSTICS[(subject_id.lower(), chapter_id.lower())]
    except KeyError as error:
        raise ValueError("A deterministic diagnostic is not available for this chapter") from error


def is_deterministic_diagnostic_item(item: DiagnosticItem) -> bool:
    return any(item in bank for bank in DETERMINISTIC_DIAGNOSTICS.values())


def validate_diagnostic_bank(items: tuple[DiagnosticItem, ...]) -> tuple[DiagnosticItem, ...]:
    if len(items) != 3:
        raise ValueError("A diagnostic must contain exactly three questions")
    seen_prompts: set[str] = set()
    seen_practice_prompts: set[str] = set()
    for item in items:
        if item.answer_mode not in {"exact", "number"}:
            raise ValueError("Unsupported practice answer mode")
        prompt_key = item.prompt.strip().lower()
        if not prompt_key or prompt_key in seen_prompts:
            raise ValueError("Diagnostic questions must be present and unique")
        seen_prompts.add(prompt_key)
        if len(item.options) != 4 or len({option.strip().lower() for option in item.options}) != 4:
            raise ValueError("Every diagnostic question must have four unique choices")
        if item.correct_option not in item.options:
            raise ValueError("Every correct answer must exactly match one choice")
        if not all((item.concept, item.explanation, item.worked_example, item.hint, item.practice_prompt)) or not item.practice_answers:
            raise ValueError("Every diagnostic question must include complete teaching support")
        practice_key = item.practice_prompt.strip().casefold()
        if practice_key in seen_practice_prompts:
            raise ValueError("Every diagnostic question must include a distinct practice prompt")
        seen_practice_prompts.add(practice_key)
    return items


def serialize_diagnostic_bank(items: tuple[DiagnosticItem, ...]) -> str:
    validate_diagnostic_bank(items)
    return json.dumps([asdict(item) for item in items], ensure_ascii=False)


def parse_diagnostic_bank(value: str) -> tuple[DiagnosticItem, ...]:
    decoded = json.loads(value)
    items = tuple(
        DiagnosticItem(
            **{
                **item,
                "options": tuple(item["options"]),
                "practice_answers": tuple(item["practice_answers"]),
            }
        )
        for item in decoded
    )
    return validate_diagnostic_bank(items)


def public_question(item: DiagnosticItem, ordinal: int, total: int) -> AdaptiveQuestion:
    return AdaptiveQuestion(ordinal=ordinal + 1, total=total, prompt=item.prompt, options=list(item.options), concept=item.concept)


def tutor_for(item: DiagnosticItem) -> TutorIntervention:
    return TutorIntervention(title=item.concept, explanation=item.explanation, worked_example=item.worked_example, hint=item.hint, practice_prompt=item.practice_prompt)


def normalize_fraction_response(value: str) -> str:
    compact = re.sub(r"\s+", "", value.lower())
    return "3/4" if compact in {"6/8", "3/4", "0.75"} else compact


def evaluate_rewrite(value: str, concept: str = "Adding like fractions") -> tuple[bool, str | None]:
    normalized = value.lower()
    words = re.findall(r"[a-z0-9]+", normalized)
    concept_terms = {"numerator", "denominator", "same", "equal", "fourths", "parts"}
    evidence_terms = {"add", "plus", "total", "sum", "4/4", "one"}
    if concept == "Adding like fractions":
        understood = len(words) >= 8 and bool(concept_terms.intersection(words)) and (bool(evidence_terms.intersection(words)) or "4/4" in normalized)
    else:
        concept_words = {word for word in re.findall(r"[a-z0-9]+", concept.lower()) if len(word) > 3}
        understood = len(words) >= 8 and bool(concept_words.intersection(words))
    if understood:
        return True, None
    return False, f"Explain the key idea behind {concept}, then connect it to the practice example."


def confidence_for(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "developing"
    return "needs_support"
