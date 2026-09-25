# My agent: WanderWise (Travel Destination Curator)
One-liner: A conversational agent that helps travelers find and evaluate destinations based on season, travel party, activities, visa constraints, safety, and a holistic Total Cost of Trip (factoring flights, lodging, dining, and activities together rather than judging airfare alone) with a catalog of global travel destinations.

Tool coverage:
- Memory: Remembers passport/citizenship (visa requirements), travel party (kid-friendly needs, ages), activity preferences (hikes, skiing, beaches), target total budget, home airport, and visited destinations across sessions.
- Tools: Look up destination candidates by season and interests (`filter_destinations`), check travel safety/political advisory levels (`check_travel_advisories`), verify visa/entry requirements (`check_visa_requirements`), and estimate itemized costs (`get_destination_cost_index`).
- Catalog/UI: A curated catalog of global destinations rendered as A2UI rich cards and side-by-side comparison tables showing a full cost breakdown (Airfare vs Lodging vs Daily Spend vs Total Trip Cost), season ratings, and visa badges.
- Image gen: Generates custom seasonal visual postcards / mood imagery for the recommended destination matching the selected activities (e.g. "Zermatt alpine ski slopes in January").
- Sandbox: Computes holistic Total Cost of Trip (TCO) comparisons in Python (e.g., modeling where cheaper European/international daily lodging and food offsets higher flights compared to expensive domestic cities like Boston).

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for multi-destination total cost trade-off math, live Google Flights / Maps integration, and Cloud Trace for latency tracking.
