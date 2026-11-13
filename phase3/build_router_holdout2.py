"""Freeze a second post-v2 challenge before the v3 training run."""
from phase3.generate_router_data import DATA_DIR, SYSTEM
from phase3.shared import write_jsonl

CASES = {
    'design': [
        'Determine whether the limiting bore and journal sizes create clearance, interference, or a transition.',
        'The design reviewer wants the smallest and largest possible gap between mating round parts.',
        'Assess assembly fit from hole lower/upper sizes and shaft lower/upper sizes.',
        'Does the pin always fit, never fit, or depend on actual size?',
        'Calculate the worst dimensional overlap between a bore and its mating shaft.',
        'Route a request about the fit envelope of two coaxial features.',
        'I need maximum material fit behavior, not a measured-part acceptance decision.',
    ],
    'process': [
        'Estimate revolutions per minute for an ideal turning operation from diameter and surface velocity.',
        'Convert feed per revolution into feed per minute and approximate one cutting pass.',
        'The planner needs a theoretical lathe cycle estimate before machine-specific review.',
        'Use bar diameter, cutting speed, feed and travel length for a turning calculation.',
        'Which tool handles preliminary machining speed and duration?',
        'Work out ideal spindle rotation and axial feed for a single cut.',
        'Estimate metal-cutting time without generating CNC code.',
    ],
    'production': [
        'Calculate the three OEE factors and their product for a completed shift.',
        'Compare scheduled time, actual runtime, theoretical output and accepted quantity.',
        'Summarize how effectively the line ran from time and piece-count records.',
        'The supervisor supplied planned minutes, operating minutes, ideal cycle and yield.',
        'Evaluate historical production availability, speed loss and scrap loss.',
        'Which capability combines utilization, rate performance and good-piece ratio?',
        'Provide an equipment-effectiveness calculation for yesterday’s batch.',
    ],
    'quality': [
        'Is 9.98 acceptable for a 10.00 dimension with bilateral limits of 0.03?',
        'Judge one observed feature against its stated lower and upper deviations.',
        'The inspector needs a dimensional conformity result using inclusive boundaries.',
        'Check whether this gauge value lies within the tolerance interval.',
        'Return insufficient data if nominal, observation, tolerance, or unit is unusable.',
        'Which workspace performs scalar measurement acceptance?',
        'Evaluate one characteristic only; do not approve the complete component.',
    ],
    'maintenance': [
        'Calculate average operating time per breakdown and average repair time per breakdown.',
        'Summarize past equipment reliability using uptime, downtime, and event count.',
        'The maintenance lead wants observed MTBF, MTTR, and availability.',
        'Analyze failure history without forecasting the next failure.',
        'Which function handles repair-hours and breakdown-count statistics?',
        'Use recorded service data to describe restoration performance.',
        'Compute retrospective reliability indicators for this asset.',
    ],
    'documentation': [
        'Turn the supplied drawing, feature, gauge, operator, timestamp, and reading into a draft record.',
        'Prepare an unsigned inspection report that explicitly requires human review.',
        'Format traceability identifiers and a dimensional result into a controlled QA document.',
        'Create a measurement record marked DRAFT_NOT_APPROVED.',
        'Which workspace produces an inspection form rather than calculating OEE?',
        'Assemble the provided evidence into a record for later authorized sign-off.',
        'Generate a review-required document containing revision and equipment identity.',
    ],
    'knowledge': [
        'Look through registered procedures for the paragraph governing record retention.',
        'What do the indexed work instructions state about handling a discrepancy?',
        'Find and cite exact source lines; do not answer from general model knowledge.',
        'Search approved local documents for the required traceability fields.',
        'If no registered excerpt supports the question, return no verified source.',
        'Which capability answers questions from document evidence rather than calculations?',
        'Retrieve the relevant passage and include its source identifier and line range.',
    ],
}


def main():
    destination = DATA_DIR / 'holdout2.jsonl'
    if destination.exists():
        raise FileExistsError('The frozen second challenge already exists; refusing to overwrite it.')
    rows = []
    for label, prompts in CASES.items():
        for index, prompt in enumerate(prompts, 1):
            rows.append({
                'id': f'R-H2-{label.upper()}-{index:02d}',
                'source_kind': 'manually_authored_post_v2_holdout',
                'reviewed_by_engineer': False, 'gold_tool': label,
                'messages': [
                    {'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': f'Tool: {label}'},
                ],
            })
    write_jsonl(destination, rows)
    print(f'Wrote {len(rows)} frozen post-v2 holdout prompts.')


if __name__ == '__main__':
    main()
