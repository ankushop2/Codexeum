import secrets


def interactive_questions(questions):
    geography = [
        ("Kenya", "Africa"),
        ("Brazil", "South America"),
        ("France", "Europe"),
        ("Japan", "Asia"),
        ("Canada", "North America"),
        ("Australia", "Oceania"),
    ]
    timelines = [
        [
            "Egyptian pyramids are built",
            "First modern Olympics (1896)",
            "First Moon landing (1969)",
            "First iPhone released (2007)",
        ],
        [
            "Printing press in Europe (around 1450)",
            "First powered airplane flight (1903)",
            "First human in space (1961)",
            "World Wide Web invented (1989)",
        ],
    ]
    countries = secrets.SystemRandom().sample(geography, 2)
    orders = secrets.SystemRandom().sample(timelines, 2)
    for question in questions:
        if question["category"] == "geography":
            country, continent = countries.pop()
            options = secrets.SystemRandom().sample(
                [c for _, c in geography if c != continent], 3
            ) + [continent]
            secrets.SystemRandom().shuffle(options)
            question.update(
                kind="map",
                prompt=f"Tap the continent where {country} is located.",
                options=options,
                answer=options.index(continent),
            )
        elif question["category"] == "history":
            timeline = orders.pop()
            items = secrets.SystemRandom().sample(timeline, len(timeline))
            question.update(
                kind="order",
                prompt="Put these events in order, from earliest to latest.",
                options=items,
                answer=0,
                order_answer=[items.index(item) for item in timeline],
            )
    return questions
