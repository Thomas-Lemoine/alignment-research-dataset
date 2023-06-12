import json
import pytest
import jsonlines
from pathlib import Path
from align_data.common.alignment_dataset import AlignmentDataset, GdocDataset, DataEntry


def test_data_entry_default_fields():
    entry = DataEntry({})

    assert entry == {
        'date_published': None,
        'source': None,
        'title': None,
        'url': None,
        'id': None,
        'text': None,
    }


def test_data_entry_id_from_text():
    data = {'key1': 12, 'key2': 312, 'text': 'once upon a time'}
    entry = DataEntry(data)
    entry.add_id()

    assert entry == dict({
        'date_published': None,
        'id': 'ea36fcd25d96821e1455adec6e5d9a3a',
        'source': None,
        'title': None,
        'url': None,
        }, **data
    )


def test_data_entry_no_text():
    entry = DataEntry({'key1': 12, 'key2': 312})
    with pytest.raises(AssertionError, match='Entry is missing text'):
        entry.add_id()


def test_data_entry_none_text():
    entry = DataEntry({'key1': 12, 'key2': 312, 'text': None})
    with pytest.raises(AssertionError, match='Entry is missing text'):
        entry.add_id()


def test_data_entry_verify_id_passes():
    entry = DataEntry({'text': 'once upon a time', 'id': 'ea36fcd25d96821e1455adec6e5d9a3a'})
    entry._verify_id()


@pytest.mark.parametrize('data, error', (
    ({'text': 'bla bla bla'}, 'Entry is missing id'),
    ({'text': 'bla bla bla', 'id': None}, 'Entry is missing id'),

    ({'id': '123'}, 'Entry is missing text'),
    ({'id': '123', 'text': None}, 'Entry is missing text'),

    ({'id': '123', 'text': 'winter wonderland'}, 'Entry id does not match text'),
    ({'id': 'ea36fcd25d96821e1455adec6e5d9a3a', 'text': 'winter wonderland'}, 'Entry id does not match text'),
    ({'id': 'ea36fcd25d96821e1455adec6e5d9a3a', 'text': 'Once upon a time'}, 'Entry id does not match text'),
))
def test_data_entry_verify_id_fails(data, error):
    entry = DataEntry(data)
    with pytest.raises(AssertionError, match=error):
        entry._verify_id()


# The base data directory
DATA_PATH = Path(__file__).parent.parent.parent.parent / 'data'


def test_alignment_dataset_default_values():
    dataset = AlignmentDataset(name='blee')

    assert dataset.name == 'blee'

    # Make sure all data paths are correct
    assert dataset.data_path.resolve() == DATA_PATH.resolve()
    assert dataset.raw_data_path.resolve() == (DATA_PATH / 'raw').resolve()
    assert dataset.files_path.resolve() == (DATA_PATH / 'raw' / dataset.name).resolve()

    # Make sure the output files are correct
    assert dataset.jsonl_path.resolve() == (DATA_PATH / f'{dataset.name}.jsonl').resolve()
    assert dataset.txt_path.resolve() == (DATA_PATH / f'{dataset.name}.txt').resolve()


def test_alignment_dataset_file_list():
    # The distill posts data is in the repo, so should always be present
    dataset = AlignmentDataset(name='distill_posts')
    dataset.glob = '*.html'

    files = [f.resolve() for f in dataset.file_list]
    assert files, "No files found - do the distill posts exists?"
    assert files == list((DATA_PATH / 'raw' / 'distill_posts').glob('*html'))


@pytest.fixture
def data_entries():
    entries = [
        DataEntry({
            'text': f'line {i}',
            'date_published': f'day {i}',
            'source': f'source {i}',
            'title': str(i),
            'url': f'http://bla.bla.bla?page={i}',
        }) for i in range(5)
    ]
    for entry in entries:
        entry.add_id()
    return entries


def check_written_files(output_path, name, entries):
    with jsonlines.open(Path(output_path) / f'{name}.jsonl', mode='r') as reader:
        assert list(reader) == entries, f'Not all entries were output to the {name}.jsonl file'

    with open(Path(output_path) / f'{name}.txt') as f:
        assert len(f.readlines()) == len(entries) * 3, f'Not all entries were output to the {name}.txt file'

    return True


def test_alignment_dataset_writer_default_paths(tmp_path, data_entries):
    dataset = AlignmentDataset(name='blaa')
    dataset.__post_init__(Path(tmp_path))

    with dataset.writer() as writer:
        for entry in data_entries:
            writer(entry)

    assert check_written_files(tmp_path, dataset.name, data_entries)


def test_alignment_dataset_writer_provided_paths(tmp_path, data_entries):
    dataset = AlignmentDataset(name='blaa')

    with dataset.writer(out_path=tmp_path) as writer:
        for entry in data_entries:
            writer(entry)

    assert check_written_files(tmp_path, dataset.name, data_entries)


def test_alignment_dataset_writer_append(tmp_path, data_entries):
    dataset = AlignmentDataset(name='blaa')

    with dataset.writer(out_path=tmp_path) as writer:
        for entry in data_entries:
            writer(entry)

    with dataset.writer(out_path=tmp_path, overwrite=False) as writer:
        for entry in data_entries:
            writer(entry)

    assert check_written_files(tmp_path, dataset.name, data_entries * 2)


def test_alignment_dataset_writer_overwrite(tmp_path, data_entries):
    dataset = AlignmentDataset(name='blaa')

    with dataset.writer(out_path=tmp_path) as writer:
        for entry in data_entries:
            writer(entry)

    with dataset.writer(out_path=tmp_path, overwrite=True) as writer:
        for entry in data_entries:
            writer(entry)

    assert check_written_files(tmp_path, dataset.name, data_entries)
