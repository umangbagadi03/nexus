def retrieval_recall(expected_urls, retrieved_urls):
    """Share of the expected sources that showed up in the retrieved results."""
    if len(expected_urls) == 0:
        return None

    found = 0
    for url in expected_urls:
        if url in retrieved_urls:
            found += 1
    return found / len(expected_urls)


def average(values):
    clean_values = []
    for value in values:
        if value is not None:
            clean_values.append(value)

    if len(clean_values) == 0:
        return None
    return sum(clean_values) / len(clean_values)
