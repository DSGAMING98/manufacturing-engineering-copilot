"""Create a small manually authored, post-training routing challenge set."""
from phase3.generate_router_data import DATA_DIR, SYSTEM
from phase3.shared import write_jsonl

CASES = {
    'design': [
        'Will the largest shaft still enter the smallest bore, and what is the worst clearance?',
        'Compare the upper and lower limits of these two mating diameters.',
        'I need an interference-versus-clearance assessment for a pin and hole.',
        'Check the dimensional fit envelope before the assembly review.',
        'Which calculation tells me whether two cylindrical features have a transition fit?',
    ],
    'process': [
        'For a 50 mm bar at 120 m/min, estimate lathe RPM and feed travel.',
        'How long is one ideal turning pass if I provide diameter, feed and cut length?',
        'Work out spindle revolutions from surface speed for a machining estimate.',
        'Prepare a preliminary single-pass cutting-time calculation for the planner.',
        'I have feed per revolution and workpiece diameter; which capability estimates the lathe setup?',
    ],
    'production': [
        'A shift ran 420 of 480 minutes and made 350 pieces; calculate effectiveness.',
        'Combine uptime, ideal cycle output and accepted quantity into one OEE figure.',
        'Show availability, performance and yield for yesterday’s production run.',
        'We know planned minutes, runtime, cycle time, total count and good count.',
        'Which workspace evaluates line effectiveness from operating and part-count data?',
    ],
    'quality': [
        'The gauge reads 20.03 against 20.00 plus or minus 0.05; is that feature conforming?',
        'Compare one measured diameter with its inclusive upper and lower specification limits.',
        'Perform a single-characteristic acceptance check, not a whole-lot release.',
        'Flag whether this measurement is inside an asymmetric tolerance band.',
        'A technician needs PASS, FAIL, or missing-evidence status for one dimension.',
    ],
    'maintenance': [
        'Four breakdowns occurred during 800 operating hours with 20 repair hours.',
        'Summarize historical time between failures and average restoration time.',
        'Use failure count, uptime and repair duration to calculate reliability indicators.',
        'I need retrospective equipment availability, not a remaining-life prediction.',
        'Which analysis handles breakdown frequency and maintenance repair duration?',
    ],
    'documentation': [
        'Generate a review-required inspection sheet with drawing revision and gauge ID.',
        'Prepare a traceable draft measurement record, clearly marked not approved.',
        'Put feature, drawing, operator, timestamp and result into an inspection record.',
        'Create the QA record for a measured characteristic but leave final sign-off to a person.',
        'Which function formats supplied measurement evidence into a controlled draft?',
    ],
    'knowledge': [
        'Find the exact registered source lines that describe traceability identifiers.',
        'Do our approved documents mention what to record for a nonconformance?',
        'Search the local procedure library and cite the relevant excerpt.',
        'Answer only from indexed evidence and abstain when the source is absent.',
        'Where in the registered work instructions is inspection-record retention discussed?',
    ],
}


def main():
    rows = []
    for label, prompts in CASES.items():
        for index, prompt in enumerate(prompts, 1):
            rows.append({
                'id': f'R-MC-{label[:3].upper()}-{index:02d}', 'source_kind': 'manually_authored_challenge',
                'reviewed_by_engineer': False, 'gold_tool': label,
                'messages': [
                    {'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt},
                    {'role': 'assistant', 'content': f'Tool: {label}'},
                ],
            })
    write_jsonl(DATA_DIR / 'manual_challenge.jsonl', rows)
    print(f'Wrote {len(rows)} manually authored challenge prompts.')


if __name__ == '__main__':
    main()
