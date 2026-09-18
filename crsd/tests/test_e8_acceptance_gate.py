"""Guard against outcome-based selection, duplicate cells and false completeness."""
from pathlib import Path
import csv
import json
import sys
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'plan/scripts'))
from audit_e8_panel import check_raw, minimum_cover


def candidate(run, reps, score=0):
    return {'run': '/archive/' + run, 'cells': [(0.0, r) for r in reps], 'score': score}


def test_fewest_complete_sources_before_run_id():
    a = candidate('001', range(5)); b = candidate('002', range(5, 10))
    full = candidate('900', range(10))
    assert minimum_cover([a, b, full], {(0.0, r) for r in range(10)}) == (full,)


def test_tie_uses_ids_not_outcomes_or_input_order():
    a = candidate('001', range(10), -100); b = candidate('002', range(10), 100)
    expected = {(0.0, r) for r in range(10)}
    assert minimum_cover([b, a], expected) == minimum_cover([a, b], expected) == (a,)


def test_overlapping_and_incomplete_runs_do_not_form_cover():
    expected = {(0.0, r) for r in range(10)}
    assert minimum_cover([candidate('001', range(6)), candidate('002', range(5, 10))], expected) == ()


@pytest.fixture
def raw_fixture(tmp_path):
    def make(arm='showpool'):
        model = 'qwen3-235b-a22b-instruct-2507'
        tag = 'qwen-' + model
        defaults = {'CRG_TEMPLATE': 'baseline' if arm == 'evprobe_p0' else 'showpool',
                    'CRG_PROBE': 'value' if arm == 'evprobe_p0' else '',
                    'CRG_MAX_OUT': '3000', 'CRG_SEAT_MODELS': '',
                    'CRG_REPS': '1', 'CRG_REP_START': '0', 'CRG_RISKS': '0'}
        source = '\n'.join(f'os.environ.get({k!r}, {v!r})' for k, v in defaults.items())
        (tmp_path/'__notebook__.ipynb').write_text(json.dumps({'cells': [
            {'cell_type': 'code', 'source': source}]}))
        game = {'game_id': 'g', 'group_total': '0', 'target': '120',
                'target_reached': 'False', 'risk_probability': '0', 'rep': '0'}
        with (tmp_path/'games.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(game)); writer.writeheader(); writer.writerow(game)
        turns = [dict(game_id='g', round=r, player='Player_'+str(i), contribution=0,
                      risk_probability=0, rep=0, language='en', show_cumulative=True,
                      prompt='The climate account so far holds 0 of the 120 target')
                 for r in range(1, 11) for i in range(1, 7)]
        (tmp_path/'turns.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in turns))
        return dict(run=str(tmp_path), raw_directory=str(tmp_path), arm=arm,
                    model=model, errors=[], cells=[(0.0, 0)]), turns, tag
    return make


def test_clean_raw_sweep_passes(raw_fixture):
    record, _, _ = raw_fixture()
    assert check_raw(record) == []


def test_wrong_pool_and_duplicate_turn_are_rejected(raw_fixture, tmp_path):
    record, turns, _ = raw_fixture()
    turns[0]['prompt'] = 'The climate account so far holds 2 of the 120 target'
    (tmp_path/'turns.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in turns))
    assert 'pool_prompt_replay' in check_raw(record)
    turns[-1] = turns[0]
    (tmp_path/'turns.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in turns))
    assert 'turn_grid' in check_raw(record)


def test_incomplete_configured_sweep_is_rejected(raw_fixture, tmp_path):
    record, _, _ = raw_fixture()
    record['cells'] = []
    assert 'incomplete_configured_sweep' in check_raw(record)


def test_incorrect_but_parsed_answers_are_not_excluded(raw_fixture, tmp_path):
    record, _, tag = raw_fixture('evprobe_p0')
    probes = []
    for round_number in (1, 5, 10):
        for question, truth, answer in [('value_defect_ev', 40, 999), ('value_compare', 2, 1)]:
            probes.append(dict(game_id='g', round=round_number, question_id=question,
                               ground_truth=truth, parsed_answer=answer, correct=False,
                               player='Player_1', model=tag, category='value', risk_probability=0))
    (tmp_path/'probes.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in probes))
    assert check_raw(record) == []
    probes[0]['correct'] = True
    (tmp_path/'probes.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in probes))
    assert 'probe_correctness_flag' in check_raw(record)
