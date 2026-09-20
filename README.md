# Delivery Route Planner

A small Python program that reads a list of delivery requests from a CSV file
and organises them into delivery trips, respecting a 10 kg vehicle capacity,
prioritising urgent deliveries, and grouping deliveries by area where possible.

Written for the eT3 2026 Software Development Internship technical challenge.


## 1. How to run

Requirements:
- Python 3.8 or newer
- No external libraries - only the Python standard library is used

Run the program:

    python planner.py deliveries.csv

If you run it with no argument, it defaults to deliveries.csv in the current
directory:

    python planner.py


## 2. Input format

The program reads a CSV file with a header row and these four columns:

    Column       Type      Meaning
    -----------  --------  ------------------------------------------
    id           integer   Unique delivery identifier
    area         text      Destination area (e.g. Nasr City, Maadi)
    priority     integer   Lower number = more urgent (1 is most urgent)
    weight_kg    decimal   Package weight in kilograms

Example:

    id,area,priority,weight_kg
    1,Nasr City,2,4.5
    2,Maadi,1,2.0
    3,Nasr City,3,1.2

The column names must match exactly. If any required column is missing, the
program stops with a clear error message listing the expected and actual
columns.


## 3. Output

The program prints two reports.

Trip details: every trip, its total weight, the areas it covers, and the
individual deliveries inside it. Undeliverable items are listed separately at
the end.

Utilisation summary: the extension feature (see section 7). It shows how full
each trip is, plus average, minimum, and maximum utilisation across all trips.

Sample output (first lines only - run the program to see the full output):

    ============================================================
    TRIPS (6)
    ============================================================

    Trip 1  |  9.00 kg  |  areas: Maadi, Zamalek
       - #2 Maadi p1 2.0kg
       - #4 Zamalek p1 7.0kg
       - #7 Maadi p1 2.5kg
    ...


## 4. My solution approach

The idea in one sentence:
Sort deliveries by urgency first, then by area, then pack them greedily into
trips - preferring to keep the same area together, but willing to mix areas
rather than waste capacity.

The steps:

1. Read and validate. Load the CSV, skip malformed rows with a warning on
   stderr, and set aside any package heavier than 10 kg in a separate
   undeliverable list.

2. Sort. Sort valid deliveries by priority (ascending), then by area.
   Priority comes first because urgent deliveries must be handled first.
   Area is the tie-breaker so that same-priority deliveries naturally
   cluster by area.

3. Pack. Walk through the sorted list. For each delivery, try three things
   in order:

     Pass 1: fit it into an open trip that already serves the same area and
             has room.

     Pass 2: if no same-area trip fits, fit it into any open trip with room.
             This prevents leaving gaps in partially-filled trips.

     Pass 3: if nothing fits, open a new trip.

4. Report. Print the trips, the undeliverable bucket, and the utilisation
   summary.

Why greedy, and why area-aware:
True optimal bin-packing is NP-hard - solving it exactly for a large input is
not practical. A greedy approach is fast, predictable, and easy to explain.

The area-first preference means same-area deliveries usually end up together,
which is realistic for a delivery company (less driving between areas). The
capacity-first fallback means we do not waste space when a same-area trip
cannot take another package.


## 5. Edge case handling

    Situation                          What the program does
    ---------------------------------  -----------------------------------------
    No deliveries at all               Prints "No deliveries to plan." and
                                       exits with code 0

    A package over 10 kg               Placed in the undeliverable bucket
                                       and reported at the end

    A package exactly 10 kg            Treated as valid (uses a small float
                                       tolerance so exact fits are not
                                       rejected)

    A package 0 kg or less             Warning to stderr; row skipped

    A delivery with a blank area       Warning to stderr; row skipped

    A row with non-numeric weight      Warning to stderr; row skipped
    or priority

    The CSV is missing a required      Stops immediately with a clear error
    column                             listing expected vs actual columns

    Multiple deliveries share the      Tie-broken by area, so same-priority
    same priority                      same-area deliveries cluster

    The next package would exceed      Falls through to Pass 2 (another trip
    the trip capacity                  with room) or Pass 3 (new trip)

    Every delivery is undeliverable    Trip list is empty; the utilisation
                                       report prints "No trips planned."

Two decisions worth explaining:

Skipping blank-area deliveries. A delivery with no area is not routable.
Grouping blank-area items together would produce a trip no dispatcher can act
on, and mixing them into other areas would weaken the area-clustering. The
honest behaviour is to reject the row and let a human fix the data.

Skipping zero/negative weights. These are data errors, not real packages.
Letting them into a trip would corrupt the weight totals and break the
utilisation report's min/max calculations.


## 6. Reasoning questions

### 6.1 Explaining my solution approach

The program has three stages: read, sort, pack.

Read. The CSV is loaded row by row. Malformed rows and packages heavier than
10 kg are handled during reading - the first is skipped with a warning, the
second goes into a separate undeliverable list so it can still be reported.

Sort. Valid deliveries are sorted by priority ascending, then by area. This
means urgent deliveries are always considered first, and within the same
priority, deliveries to the same area sit next to each other in the list.

Pack. Each delivery is placed into a trip using three passes. First, look for
an open trip with the same area that has room. Second, if no same-area trip
fits, look for any open trip with room. Third, if nothing fits, start a new
trip.

The result is a set of trips where urgent deliveries are handled first, most
trips are single-area, and total capacity is used reasonably well.


### 6.2 What was the most difficult part of the assignment?

The hardest part was deciding how to balance two competing goals: keeping
same-area deliveries together, and using trip capacity efficiently.

If I only grouped by area, for example, a leftover 2 kg Nasr City package would open a new
trip instead of filling 2 kg of empty space in a Maadi trip - wasting capacity.

If I ignored areas and just filled trips to 10 kg, deliveries to different
areas would be mixed, and the driver would have to cover more ground.

The two-pass approach (area-first, then any-trip) is my attempt at a middle
ground. It is not perfect, but it is reasonable and I can explain the
trade-off clearly.


### 6.3 Are there situations where my algorithm may not produce the best possible grouping?

Yes. Greedy packing is not optimal.

Example 1 - leaving capacity idle. Suppose the sort order produces a 4 kg
Nasr City package that arrives when all same-area trips are full and the only
trip with room is a Zamalek trip at 9 kg. Pass 2 cannot fit it (9 + 4 > 10),
so it opens a new trip. That new trip ends up only 40% full, even though a
smarter algorithm might have rearranged earlier trips to avoid it.

Example 2 - committing too early. Because we sort and then greedily pack, we
commit to a placement before seeing the whole picture. A solver that
considered all deliveries together could often find fewer, fuller trips.

The utilisation summary in this program (my extension) shows this directly -
the Min line highlights the most under-filled trip, which is usually evidence
of exactly this limitation.


### 6.4 If the input contained 1,000,000 delivery requests, what part of my solution might become slow or memory-intensive?

Two parts would struggle.

The open_trips scan. For each delivery, Pass 1 and Pass 2 both loop over
every open trip to find a match. With N deliveries, that is roughly O(N^2)
work. At 1 million deliveries, this becomes very slow.

Memory. Every Delivery and Trip is a Python object, and the whole list is held
in memory at once. One million Delivery objects plus their containing trips
would take a significant amount of RAM - likely hundreds of megabytes.

How I would fix it:

- Replace the linear scan with an index: a dictionary from area to list of
  open trips with room. Pass 1 becomes a dictionary lookup instead of a loop.

- For Pass 2, keep open trips in a heap keyed by remaining capacity, so
  finding "any trip with room" is O(log n) instead of O(n).

- For memory, process deliveries in a streaming fashion rather than loading
  everything up front.


### 6.5 What would I improve if I had another day to work on the solution?

In priority order:

1. Fix the O(N^2) scans. Index open trips by area and by remaining capacity,
   as described above. This is the biggest improvement and would matter for
   any real dataset.

2. Add unit tests. A test file covering each edge case in section 5, plus
   some property tests (e.g. "no trip ever exceeds 10 kg", "every valid
   delivery appears in exactly one trip").

3. Make the output machine-readable. A JSON output option would let a real
   dispatch system consume the result directly, instead of parsing printed
   text.

4. Improve the packing quality. Add a light rebalancing pass after the greedy
   step - if a trip is very under-filled, try moving its contents into other
   trips to free up the whole trip. This would reduce the number of trips and
   improve the utilisation numbers.

5. Support multiple vehicles. The current model assumes one vehicle that can
   carry 10 kg per trip. A real delivery company would have a fleet with
   different capacities and possibly multiple trips in parallel.


## 7. Extension: trip utilisation report

What it does:
After the trips are planned, the program prints a second report showing how
well the trips use the vehicle's capacity.

For each trip, it shows the weight, the percentage of the 10 kg capacity used, and
the areas covered. It also prints aggregate stats - total trips, total kg
moved, average utilisation, and the min and max trips.

Example:

    ============================================================
    UTILISATION SUMMARY
    ============================================================
      Trips:    6
      Total:    46.20 kg moved
      Average:   77.0%
      Min:       4.00/10 kg ( 40.0%)  <- Trip 3 (most idle capacity)
      Max:      10.00/10 kg (100.0%)  <- Trip 5

      Per-trip breakdown:
        Trip 1:  9.00/10 kg ( 90.0%)  [Maadi, Zamalek]
        Trip 2:  8.00/10 kg ( 80.0%)  [Maadi, Nasr City, Zamalek]
        Trip 3:  4.00/10 kg ( 40.0%)  [Nasr City]
        ...

Why I chose this extension:
I chose the utilisation report because it directly addresses the biggest
weakness of the greedy algorithm - it sometimes leaves capacity idle.

The Min line makes that weakness visible. A reviewer can look at the output
and immediately see which trip is under-filled - and that is exactly the
evidence needed to answer reasoning question 6.3 ("are there situations where
your algorithm may not produce the best possible grouping?").

I also considered two other options:

- A per-area summary (trips and total kg per area). I decided against this
  because attributing a mixed-area trip's weight to individual areas is
  ambiguous - there is no single correct answer.

- A CSV output of trips. Useful for a real system, but it does not add any
  insight into the algorithm's quality.

The utilisation report is simple to explain, directly useful, and ties back to
the reasoning questions. That is why I picked it.


## 8. Project structure

    planner.py       All code lives here
    deliveries.csv   Sample input file
    README.md        This file

The whole program is intentionally in one file. The challenge brief asks for
clean, understandable code rather than layered architecture, and a single file
is easier to walk through end-to-end.


## 9. Author

Takwa Madkour
eT3 2026 Software Development Internship - Technical Assignment
